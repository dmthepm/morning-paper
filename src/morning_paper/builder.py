from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .config import MorningPaperConfig
from .renderers import write_outputs
from .sources import collect_sources


def build_paper(config: MorningPaperConfig, *, date_str: str | None = None) -> dict[str, object]:
    target_date = date_str or datetime.now(ZoneInfo(config.timezone)).date().isoformat()
    collected, errors = collect_sources(config)
    outputs = write_outputs(config, collected, date_str=target_date)
    return {
        "date": target_date,
        "name": config.name,
        "counts": {key: len(value) for key, value in collected.items()},
        "source_errors": errors,
        "outputs": {key: str(value) for key, value in outputs.items() if key != "dir"},
        "output_dir": str(outputs["dir"]),
    }
