# src/source_pool/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib

class SourceStatus:
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    PROMOTED = "promoted"

@dataclass
class RawSource:
    url: str
    channel_name: str
    source_url: str
    discovered_at: datetime
    status: str = SourceStatus.PENDING
    fail_count: int = 0
    success_count: int = 0
    last_check: Optional[datetime] = None
    latency: int = 0
    video_codec: str = ""

    def get_key(self) -> str:
        return hashlib.md5(f"{self.channel_name}|{self.url}".encode()).hexdigest()

    def to_dict(self):
        return {
            "url": self.url,
            "channel_name": self.channel_name,
            "source_url": self.source_url,
            "discovered_at": self.discovered_at.isoformat(),
            "status": self.status,
            "fail_count": self.fail_count,
            "success_count": self.success_count,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "latency": self.latency,
            "video_codec": self.video_codec,
        }

    @classmethod
    def from_dict(cls, data: dict):
        data["discovered_at"] = datetime.fromisoformat(data["discovered_at"])
        if data.get("last_check"):
            data["last_check"] = datetime.fromisoformat(data["last_check"])
        return cls(**data)
