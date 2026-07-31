# src/stable/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

class StableStatus:
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    REPLACED = "replaced"

@dataclass
class StableSource:
    channel_name: str
    url: str
    latency: int
    video_codec: str
    promoted_at: datetime
    is_fixed: bool = False
    auto_optimize: bool = True
    last_verified: Optional[datetime] = None
    fail_count: int = 0
    status: str = StableStatus.ACTIVE

    def to_dict(self):
        return {
            "channel_name": self.channel_name,
            "url": self.url,
            "latency": self.latency,
            "video_codec": self.video_codec,
            "promoted_at": self.promoted_at.isoformat(),
            "is_fixed": self.is_fixed,
            "auto_optimize": self.auto_optimize,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
            "fail_count": self.fail_count,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: dict):
        data["promoted_at"] = datetime.fromisoformat(data["promoted_at"])
        if data.get("last_verified"):
            data["last_verified"] = datetime.fromisoformat(data["last_verified"])
        return cls(**data)
