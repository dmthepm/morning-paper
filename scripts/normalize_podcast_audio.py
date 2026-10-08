#!/usr/bin/env python3
"""Two-pass loudnorm to a local mono AAC/M4A, then measure the encoded file."""

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path


TARGET = "I=-16:TP=-1:LRA=11"
MEASUREMENTS = {
    "input_i": "measured_I", "input_tp": "measured_TP",
    "input_lra": "measured_LRA", "input_thresh": "measured_thresh",
    "target_offset": "offset",
}


def measure(path):
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", f"loudnorm={TARGET}:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    matches = re.findall(r"\{\s*\"input_i\".*?\}", result.stderr, flags=re.DOTALL)
    if not matches:
        raise ValueError("ffmpeg did not return loudnorm measurements")
    values = json.loads(matches[-1])
    for key in MEASUREMENTS:
        if not math.isfinite(float(values[key])):
            raise ValueError(f"invalid loudnorm value: {key}")
    return values


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if not args.input.is_file() or args.output.suffix.lower() != ".m4a":
            raise ValueError("need an existing input and a .m4a output path")
        if args.output.exists():
            raise ValueError("output already exists; choose a new path")
        first = measure(args.input)
        settings = ":".join(f"{option}={first[source]}" for source, option in MEASUREMENTS.items())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(args.input),
             "-af", f"loudnorm={TARGET}:{settings}:linear=true",
             "-ar", "44100", "-ac", "1", "-c:a", "aac", "-b:a", "96k",
             "-movflags", "+faststart", str(args.output)],
            check=True,
        )
        final = measure(args.output)
        integrated = float(final["input_i"])
        true_peak = float(final["input_tp"])
        passed = -17 <= integrated <= -15 and true_peak <= -1
        print(json.dumps({"output": str(args.output), "lufs_i": integrated,
                          "dbtp": true_peak, "within_apple_guidance": passed}, sort_keys=True))
        return 0 if passed else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"normalize_podcast_audio: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
