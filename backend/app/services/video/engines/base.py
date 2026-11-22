"""Engine abstraction for video generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


ProgressCallback = Callable[[int, str], None]


@dataclass
class EngineCapabilities:
    engine_id: str
    label: str
    available: bool
    reason: Optional[str] = None
    requires_gpu: bool = False


@dataclass
class EngineResult:
    output_path: Path
    thumbnail_path: Path
    duration_seconds: float
    file_size_bytes: int
    metadata: dict[str, Any] = field(default_factory=dict)


class VideoEngine(ABC):
    engine_id: str
    label: str
    requires_gpu: bool = False

    @abstractmethod
    def capabilities(self) -> EngineCapabilities:
        ...

    @abstractmethod
    async def generate(
        self,
        project: Any,
        work_dir: Path,
        progress: Optional[ProgressCallback] = None,
    ) -> EngineResult:
        ...


def list_engines() -> list[EngineCapabilities]:
    from app.services.video.engines.local_engine import LocalEngine
    from app.services.video.engines.ltx2_engine import LTX2Engine

    return [LocalEngine().capabilities(), LTX2Engine().capabilities()]


def get_engine(engine_id: str) -> VideoEngine:
    from app.services.video.engines.local_engine import LocalEngine
    from app.services.video.engines.ltx2_engine import LTX2Engine

    engines = {
        "local": LocalEngine,
        "ltx2": LTX2Engine,
        "ltx-2.5": LTX2Engine,
    }
    cls = engines.get(engine_id)
    if not cls:
        raise ValueError(f"Unknown engine: {engine_id}")
    return cls()
