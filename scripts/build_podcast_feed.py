#!/usr/bin/env python3
"""Build a local podcast feed directory. This command never uploads anything."""

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image


ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES)
MEDIA_TYPES = {".m4a": "audio/x-m4a", ".mp3": "audio/mpeg"}


def base_url(value):
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc or parts.query or parts.fragment:
        raise ValueError("--base-url must be an HTTPS URL without a query or fragment")
    return value.rstrip("/")


def artwork(path):
    with Image.open(path) as image:
        width, height = image.size
        if image.format not in ("PNG", "JPEG") or width != height or not 1400 <= width <= 3000:
            raise ValueError("artwork must be a square PNG or JPEG, 1400–3000 pixels per side")
        if image.mode not in ("RGB", "L"):
            raise ValueError("artwork must have no transparency or alpha channel")


def duration(path):
    output = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    seconds = float(output)
    if seconds <= 0:
        raise ValueError("audio duration must be positive")
    return max(1, round(seconds))


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "episode"


def add(parent, name, value, **attrs):
    node = ET.SubElement(parent, name, attrs)
    node.text = str(value)
    return node


def feed_xml(args, episodes, cover_name, base):
    rss = ET.Element("rss", {"version": "2.0", "xmlns:content": "http://purl.org/rss/1.0/modules/content/"})
    channel = ET.SubElement(rss, "channel")
    add(channel, "title", args.show_title)
    add(channel, "link", base + "/")
    add(channel, "description", args.show_description)
    add(channel, "language", args.language)
    add(channel, f"{{{ITUNES}}}author", args.author)
    ET.SubElement(channel, f"{{{ITUNES}}}image", {"href": base + "/" + cover_name})
    add(channel, f"{{{ITUNES}}}explicit", "true" if args.explicit else "false")
    ET.SubElement(channel, f"{{{ITUNES}}}category", {"text": args.category})
    if args.visibility == "private":
        add(channel, f"{{{ITUNES}}}block", "Yes")
    for episode in sorted(episodes, key=lambda e: e["published_at"], reverse=True):
        item = ET.SubElement(channel, "item")
        add(item, "title", episode["title"])
        add(item, "description", episode["description"])
        add(item, "guid", episode["guid"], isPermaLink="false")
        when = dt.datetime.fromisoformat(episode["published_at"])
        add(item, "pubDate", format_datetime(when))
        ET.SubElement(item, "enclosure", {
            "url": base + "/episodes/" + episode["file"],
            "length": str(episode["bytes"]),
            "type": episode["type"],
        })
        add(item, f"{{{ITUNES}}}duration", episode["duration_seconds"])
        add(item, f"{{{ITUNES}}}explicit", "true" if episode["explicit"] else "false")
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-url", required=True, help="future HTTPS location of this directory")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--artwork", type=Path, required=True)
    parser.add_argument("--show-title", required=True)
    parser.add_argument("--show-description", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--episode-title", required=True)
    parser.add_argument("--episode-description", required=True)
    parser.add_argument("--language", default="en-us")
    parser.add_argument("--category", default="Technology")
    parser.add_argument("--visibility", choices=("private", "public"), default="private")
    parser.add_argument("--published-at", help="ISO 8601 time with timezone; default is now in UTC")
    parser.add_argument("--explicit", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="validate inputs and print plan without writing")
    args = parser.parse_args(argv)
    try:
        base = base_url(args.base_url)
        ext = args.audio.suffix.lower()
        if ext not in MEDIA_TYPES or not args.audio.is_file():
            raise ValueError("audio must be an existing .m4a or .mp3 file")
        if not args.artwork.is_file():
            raise ValueError("artwork file does not exist")
        artwork(args.artwork)
        published = dt.datetime.fromisoformat(args.published_at) if args.published_at else dt.datetime.now(dt.timezone.utc)
        if published.tzinfo is None:
            raise ValueError("--published-at needs a timezone")
        published = published.astimezone(dt.timezone.utc).isoformat()
        audio_hash = hashlib.sha256(args.audio.read_bytes()).hexdigest()
        name = f"{slug(args.episode_title)}-{audio_hash[:12]}{ext}"
        cover_name = "cover" + args.artwork.suffix.lower()
        entry = {
            "title": args.episode_title, "description": args.episode_description,
            "published_at": published, "file": name, "bytes": args.audio.stat().st_size,
            "type": MEDIA_TYPES[ext], "duration_seconds": duration(args.audio),
            "guid": "urn:sha256:" + audio_hash, "sha256": audio_hash, "explicit": args.explicit,
        }
        index = args.output_dir / "episodes.json"
        episodes = json.loads(index.read_text()) if index.exists() else []
        if any(e["sha256"] == audio_hash for e in episodes):
            raise ValueError("this audio is already in the feed")
        episodes.append(entry)
        xml = feed_xml(args, episodes, cover_name, base)
        ET.fromstring(xml)
        plan = {"feed": base + "/feed.xml", "episodes": len(episodes), "audio_bytes": entry["bytes"],
                "duration_seconds": entry["duration_seconds"], "visibility": args.visibility,
                "writes": not args.dry_run}
        if not args.dry_run:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            (args.output_dir / "episodes").mkdir(exist_ok=True)
            shutil.copyfile(args.audio, args.output_dir / "episodes" / name)
            shutil.copyfile(args.artwork, args.output_dir / cover_name)
            (args.output_dir / "feed.xml.tmp").write_bytes(xml)
            (args.output_dir / "feed.xml.tmp").replace(args.output_dir / "feed.xml")
            (args.output_dir / "episodes.json.tmp").write_text(json.dumps(episodes, indent=2) + "\n")
            (args.output_dir / "episodes.json.tmp").replace(index)
        print(json.dumps(plan, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"build_podcast_feed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
