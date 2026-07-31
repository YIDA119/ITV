# src/quality/monitor.py
import asyncio
import aiohttp
from collections import deque
from datetime import datetime
from typing import Dict, List

from src.logger import logger
from src.speed_tester import probe_channel_advanced
from src.quality.models import QualityReport, QualityStatus
from src.http_client import HttpClient

class QualityMonitor:
    CHECK_WINDOW = 10
    CHECK_INTERVAL_HOURS = 24
    LATENCY_WARN_THRESHOLD = 3000
    LATENCY_CRITICAL_THRESHOLD = 5000

    def __init__(self, stable_manager=None):
        from src.stable.manager import StableManager
        self.stable_manager = stable_manager or StableManager()
        self._history: Dict[str, deque] = {}

    def _get_history(self, channel_name: str) -> deque:
        if channel_name not in self._history:
            self._history[channel_name] = deque(maxlen=self.CHECK_WINDOW)
        return self._history[channel_name]

    async def check_channel(self, channel_name: str, url: str, session: aiohttp.ClientSession) -> tuple:
        channel = {"name": channel_name, "url": url}
        _, latency, ok, _ = await probe_channel_advanced(session, channel, await self.stable_manager._ensure_db())
        self._get_history(channel_name).append((datetime.now(), ok, latency))
        return ok, latency

    def get_quality_report(self, channel_name: str) -> QualityReport:
        history = self._get_history(channel_name)
        if not history:
            return QualityReport(channel_name, QualityStatus.UNKNOWN, 0, 0, 0, datetime.now(), 0)
        total = len(history)
        success_count = sum(1 for _, ok, _ in history if ok)
        success_rate = success_count / total if total > 0 else 0
        latencies = [lat for _, ok, lat in history if ok]
        avg_latency = sum(latencies) // len(latencies) if latencies else 9999
        consecutive_fails = 0
        for _, ok, _ in reversed(history):
            if not ok: consecutive_fails += 1
            else: break
        if consecutive_fails >= 3:
            status = QualityStatus.CRITICAL
        elif success_rate < 0.5 or avg_latency > self.LATENCY_CRITICAL_THRESHOLD:
            status = QualityStatus.CRITICAL
        elif success_rate < 0.8 or avg_latency > self.LATENCY_WARN_THRESHOLD:
            status = QualityStatus.WARNING
        else:
            status = QualityStatus.HEALTHY
        return QualityReport(channel_name, status, success_rate, avg_latency, total, datetime.now(), consecutive_fails)

    def should_replace(self, channel_name: str) -> bool:
        report = self.get_quality_report(channel_name)
        src = self.stable_manager.stable_sources.get(channel_name)
        if src and src.is_fixed and not src.auto_optimize:
            return False
        return report.needs_replacement()

    async def check_all_active_sources(self, concurrency: int = 10) -> List[QualityReport]:
        active_sources = await self.stable_manager.get_stable_sources()
        if not active_sources:
            return []
        logger.info(f"🔍 检查 {len(active_sources)} 个活跃源的质量...")
        reports = []
        semaphore = asyncio.Semaphore(concurrency)
        async with HttpClient.session_context() as session:
            async def check_one(name, src):
                async with semaphore:
                    ok, latency = await self.check_channel(name, src.url, session)
                    if ok:
                        await self.stable_manager.record_success(name)
                    else:
                        await self.stable_manager.record_failure(name)
                    return self.get_quality_report(name)
            tasks = [check_one(name, src) for name, src in active_sources.items()]
            reports = await asyncio.gather(*tasks)
        healthy = sum(1 for r in reports if r.status == QualityStatus.HEALTHY)
        warning = sum(1 for r in reports if r.status == QualityStatus.WARNING)
        critical = sum(1 for r in reports if r.status == QualityStatus.CRITICAL)
        logger.info(f"📊 质量检查结果: 健康={healthy}, 警告={warning}, 严重={critical}")
        return reports

    def get_critical_sources(self) -> List[str]:
        critical = []
        for name, src in self.stable_manager.stable_sources.items():
            if src.is_fixed and not src.auto_optimize:
                continue
            if self.get_quality_report(name).status == QualityStatus.CRITICAL:
                critical.append(name)
        return critical
