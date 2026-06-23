from __future__ import annotations

import json
import sys

from .renderers import _count_pages_direct


def main() -> int:
    payload = json.loads(sys.stdin.read())
    pages = _count_pages_direct(
        str(payload["markdown"]),
        style=str(payload["style"]),
        palette=str(payload["palette"]),
        font_scale=float(payload["font_scale"]),
    )
    print(json.dumps({"pages": pages}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
