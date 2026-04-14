from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class SourceItem:
    source_type: str
    source_name: str
    title: str
    url: str
    summary: str = ""
    author: str = ""
    published_at: str = ""
    score: float = 0.0
    metadata: dict[str, str | int | float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

