# src/quality/models.py
from dataclasses import dataclass
from datetime import datetime

class QualityStatus:
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class QualityReport:
    channel_name: str
    status: str
    success_rate: float
    avg_latency: int
    sample_count: int
    last_check: datetime
    consecutive_fails: int = 0

    def needs_replacement(self, max_fails: int = 3) -> bool:
        return self.status == QualityStatus.CRITICAL or self.consecutive_fails >= max_fails
