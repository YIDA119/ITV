import asyncio
import subprocess
import json
from datetime import datetime, timedelta
from src.config_loader import config
from src.logger import logger
from src.database import get_db_cache
from src.http_client import HttpClient

_ffprobe_available = None

async def check_ffprobe():
    global _ffprobe_available
    if _ffprobe_available is not None:
        return _ffprobe_available
    try:
        proc = await asyncio.create_subprocess_exec("ffprobe", "-version", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        await proc.wait()
        _ffprobe_available = (proc.returncode == 0)
        return _ffprobe_available
    except:
        _ffprobe_available = False
        return False

async def validate_with_ffprobe(url: str, timeout: int) -> dict:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams",
           "-analyzeduration", "5000000", "-probesize", "5000000", url]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            return {"valid": False, "has_video": False, "video_codec": ""}
        data = json.loads(stdout.decode())
        streams = data.get("streams", [])
        has_video = False
        video_codec = ""
        for s in streams:
            if s.get("codec_type") == "video":
                has_video = True
                video_codec = s.get("codec_name", "").lower()
                break
        return {"valid": has_video, "has_video": has_video, "video_codec": video_codec}
    except Exception:
        return {"valid": False, "has_video": False, "video_codec": ""}

async def quick_http_check(url: str, timeout: int = 3) -> bool:
    try:
        async with HttpClient.session_context() as session:
            async with session.head(url, timeout=timeout, allow_redirects=True) as resp:
                if resp.status != 200: return False
                ct = resp.headers.get("content-type", "").lower()
                return any(x in ct for x in ["video", "mpegurl", "x-mpegurl", "application/vnd.apple.mpegurl"])
    except:
        return False

async def validate_batch(channels: list) -> list:
    if config.ffmpeg_mode == "off" or not config.ffmpeg_enable:
        logger.info("⚙️ ffmpeg 深度验证已禁用")
        return channels
    if not await check_ffprobe():
        logger.warning("⚠️ ffprobe 不可用，跳过深度验证")
        return channels

    db = await get_db_cache()
    cached_valid = []
    need_validate = []
    for ch in channels:
        cached = await db.get_cached_probe_result(ch["url"])
        if cached:
            if cached.get("valid"):
                ch["video_codec"] = cached.get("video_codec", "")
                cached_valid.append(ch)
            continue
        # 快速HTTP检查
        if await quick_http_check(ch["url"], timeout=2):
            ch["video_codec"] = "http_ok"
            cached_valid.append(ch)
            await db.save_probe_result(ch["url"], {"valid": True, "video_codec": "http_ok", "has_video": True})
        else:
            need_validate.append(ch)

    logger.info(f"🔍 ffmpeg 深度验证: {len(need_validate)} 个需验证，{len(cached_valid)} 个来自缓存/HTTP")

    if config.ffmpeg_mode == "quick":
        return cached_valid + need_validate  # 不深度验证，直接返回

    # 深度模式
    semaphore = asyncio.Semaphore(config.max_workers)
    async def validate_one(ch):
        async with semaphore:
            result = await validate_with_ffprobe(ch["url"], config.timeout)
            if result.get("valid"):
                ch["video_codec"] = result.get("video_codec", "")
                await db.save_probe_result(ch["url"], result)
                return ch
            await db.save_probe_result(ch["url"], result)
            return None

    tasks = [validate_one(ch) for ch in need_validate]
    results = await asyncio.gather(*tasks)
    valid_need = [r for r in results if r is not None]
    valid = cached_valid + valid_need
    logger.info(f"✅ ffmpeg 验证完成: 通过 {len(valid)}/{len(channels)} 个频道")
    return valid
