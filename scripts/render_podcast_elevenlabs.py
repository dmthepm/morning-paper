#!/usr/bin/env python3
"""Render a reviewed ear script through ElevenLabs only with --render."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


API = "https://api.elevenlabs.io/v1/text-to-speech"
IDENTIFIER = re.compile(r"[A-Za-z0-9_-]+\Z")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new .mp3 file")
    parser.add_argument("--voice-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--render", action="store_true", help="make one paid API request")
    args = parser.parse_args(argv)
    try:
        if not args.script.is_file():
            raise ValueError("--script must be a readable file")
        if args.output.suffix.lower() != ".mp3":
            raise ValueError("--output must end in .mp3")
        if not IDENTIFIER.fullmatch(args.voice_id) or not IDENTIFIER.fullmatch(args.model_id):
            raise ValueError("voice and model IDs may contain only letters, digits, underscore and hyphen")
        script = args.script.read_text(encoding="utf-8").strip()
        if not script:
            raise ValueError("script is empty")
        if args.output.exists():
            raise ValueError("output already exists; choose a new path to avoid a duplicate paid render")
        plan = {"route": "ElevenLabs direct API", "model_id": args.model_id,
                "voice_id": args.voice_id, "characters": len(script), "output": str(args.output),
                "paid_request": args.render}
        if not args.render:
            print(json.dumps(plan, sort_keys=True))
            return 0
        key = os.environ.get("ELEVENLABS_API_KEY")
        if not key:
            raise ValueError("ELEVENLABS_API_KEY is not set")
        request = urllib.request.Request(
            f"{API}/{args.voice_id}?output_format=mp3_44100_128",
            data=json.dumps({"text": script, "model_id": args.model_id}).encode("utf-8"),
            headers={"Content-Type": "application/json", "xi-api-key": key},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if media_type not in ("audio/mpeg", "audio/mp3"):
                raise ValueError("provider did not return MP3 audio")
            audio = response.read()
        if not audio:
            raise ValueError("provider returned empty audio")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(".mp3.tmp")
        temporary.write_bytes(audio)
        temporary.replace(args.output)
        print(json.dumps({**plan, "bytes": len(audio)}, sort_keys=True))
        return 0
    except urllib.error.HTTPError as error:
        print(f"render_podcast_elevenlabs: provider HTTP {error.code}; no output written", file=sys.stderr)
    except urllib.error.URLError:
        print("render_podcast_elevenlabs: provider connection failed; check account before retrying", file=sys.stderr)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"render_podcast_elevenlabs: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
