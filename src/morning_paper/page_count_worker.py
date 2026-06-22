from __future__ import annotations

import json
import sys

from .renderers import count_pages


def main() -> int:
    payload = json.loads(sys.stdin.read())
    pages = count_pages(
        str(payload["markdown"]),
        style=str(payload["style"]),
        palette=str(payload["palette"]),
        font_scale=float(payload["font_scale"]),
    )
    print(json.dumps({"pages": pages}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
