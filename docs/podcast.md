# A spoken edition

An audio edition is a second output from the same reported paper. The agent
writes and checks the words; local tools render audio and build a feed. Keep
reader sources, account choices, keys, feed URLs, and episode drafts in the
reader's private newsroom. These scripts write local files only. Hosting and
Apple Podcasts submission are separate owner actions.

## 1. Prepare a Mac and the private paths

Use a source checkout for the scripts: the `morning-paper` engine installed by
`uv tool install` does not install scripts from this repository. On macOS,
[Homebrew supplies `uv`](https://formulae.brew.sh/formula/uv),
[`ffmpeg`/`ffprobe`](https://formulae.brew.sh/formula/ffmpeg), and
[`whisper-cli`](https://formulae.brew.sh/formula/whisper.cpp).

```bash
brew install uv ffmpeg whisper.cpp
mkdir -p "$HOME/Work"
git clone https://github.com/dmthepm/morning-paper.git "$HOME/Work/morning-paper"
MP_SOURCE="$HOME/Work/morning-paper"             # existing checkout is fine
MP_NEWSROOM="$HOME/Work/my-morning-paper"        # replace with your private newsroom
MP_FEED="$HOME/.local/state/morning-paper/podcast-feed"
mkdir -p "$MP_NEWSROOM/audio" "$MP_FEED"
test -f "$MP_NEWSROOM/DELIVERY.md"
test -f "$MP_SOURCE/scripts/build_podcast_feed.py"
command -v ffmpeg && command -v ffprobe && command -v whisper-cli && command -v say
uv run --no-project --python 3.13 --with Pillow python -c 'import PIL; print(PIL.__version__)'
```

If the public checkout already exists, skip `git clone` and set `MP_SOURCE`
to its absolute path. The `uv run --with Pillow` environment is deliberate:
system `python3` and the isolated engine install may not have Pillow. Keep
the newsroom and durable `MP_FEED` outside the public checkout. Back up
`MP_FEED`, especially `episodes.json` and `episodes/`; subsequent editions
append there, preserving prior episode URLs and GUIDs.

For local transcript checking, download a model once from
[whisper.cpp's model list](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md):

```bash
mkdir -p "$HOME/.local/share/whisper-models"
curl -fL 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin' \
  -o "$HOME/.local/share/whisper-models/ggml-base.en.bin"
test -s "$HOME/.local/share/whisper-models/ggml-base.en.bin"
```

## 2. Write for the ear

Start with the edition's final `draft.md` and source notes after editorial and
factual review. Write a separate `$MP_NEWSROOM/audio/script.txt`. Lead with
the point and action, then the few facts needed to understand it. Use short
sentences, spoken numbers, and natural transitions. Remove tables, Markdown,
URLs, file paths, citation codes, and visual references; preserve the
strength and attribution of claims. Never invent an item or present an
unverified one as settled. At roughly 150 spoken words per minute, a
30-second test is about 75 words. Read it aloud once. Put source links and
optional reply prompts in episode notes, where the listener can look later.

## 3. Choose and render a voice

Audition the same short paragraph in two or three voices at normal speed on
the phone or headphones the reader uses. Judge names, numbers, pauses, and
long-form comfort. Record the chosen provider, route, model ID, voice ID,
language, and pronunciation notes in private `DELIVERY.md`. The paper's
editorial `preferences/voice.md` is a different choice. Re-audition after a
model or voice change. Use a cloned voice only with permission.

A free workflow rehearsal uses macOS `say`, then the normalization step
below. It proves the local file path without approving a provider voice:

```bash
say -v Samantha -f "$MP_NEWSROOM/audio/script.txt" -o "$MP_NEWSROOM/audio/rehearsal.aiff"
MP_SOURCE_AUDIO="$MP_NEWSROOM/audio/rehearsal.aiff"
```

[ElevenLabs TTS](https://elevenlabs.io/docs/overview/capabilities/text-to-speech)
is the documented provider default. The supported direct route uses
`scripts/render_podcast_elevenlabs.py`. The reader creates their own account
and [API key with a usage limit](https://elevenlabs.io/docs/overview/administration/workspaces/api-keys),
then makes `ELEVENLABS_API_KEY` available to the process from a private secret
store or `~/.config/morning-paper/env.sh`. Do not paste its value into a
command, repo, `DELIVERY.md`, or episode notes. In ElevenLabs **My Voices →
More actions → Copy voice ID**, copy the approved voice ID; use the
[model list](https://elevenlabs.io/docs/api-reference/models/list) to choose
a model whose `can_do_text_to_speech` is true. Record both IDs privately.
Voice-library API availability may depend on the account; audition in the
dashboard if needed.

The command without `--render` is a dry run: it reads the script and prints
the character count, IDs, and output path, with **no key lookup and no API
request**. Check that plan and the account's usage limit, then explicitly
approve the first paid audition or episode render. `--render` makes exactly
one direct [Create Speech API](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
request using the reviewed text, chosen IDs, and `mp3_44100_128`; it refuses
to overwrite an output file. Failed or uncertain paid requests need account
history inspection before retrying.

```bash
uv run --no-project --python 3.13 python "$MP_SOURCE/scripts/render_podcast_elevenlabs.py" \
  --script "$MP_NEWSROOM/audio/script.txt" --output "$MP_NEWSROOM/audio/source.mp3" \
  --voice-id VOICE_ID_FROM_MY_VOICES --model-id MODEL_ID_FROM_MODEL_LIST
# Only after approval: repeat that command with --render, then set
# MP_SOURCE_AUDIO="$MP_NEWSROOM/audio/source.mp3"
```

ElevenLabs through fal is an **advanced external route**. It needs the reader's
own fal account, `FAL_KEY` in that route's private secret store, an endpoint
and spending guard chosen by its owner. The direct-render script does not
call fal. A fal user brings the rendered MP3 into the same local
normalization, transcript, and feed steps.

## 4. Normalize and check the audio

`normalize_podcast_audio.py` measures the source with FFmpeg's
[two-pass `loudnorm`](https://ffmpeg.org/ffmpeg-filters.html#loudnorm), maps
`input_i`, `input_tp`, `input_lra`, `input_thresh`, and `target_offset` to
the second pass's `measured_I`, `measured_TP`, `measured_LRA`,
`measured_thresh`, and `offset`, then encodes mono AAC in M4A. It remeasures
the encoded file and reports integrated loudness and true peak. It targets
about -16 LUFS and at most -1 dBTP; check `within_apple_guidance: true`
before continuing. [Apple accepts MP3 and AAC in RSS and recommends AAC in
MP4](https://podcasters.apple.com/support/893-audio-requirements).

```bash
uv run --no-project --python 3.13 python "$MP_SOURCE/scripts/normalize_podcast_audio.py" \
  --input "$MP_SOURCE_AUDIO" --output "$MP_NEWSROOM/audio/edition.m4a"
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 \
  "$MP_NEWSROOM/audio/edition.m4a"
ffmpeg -y -i "$MP_NEWSROOM/audio/edition.m4a" -ar 16000 -ac 1 -c:a pcm_s16le \
  "$MP_NEWSROOM/audio/check.wav"
whisper-cli -m "$HOME/.local/share/whisper-models/ggml-base.en.bin" \
  -f "$MP_NEWSROOM/audio/check.wav" -nt -otxt -of "$MP_NEWSROOM/audio/check"
diff -u "$MP_NEWSROOM/audio/script.txt" "$MP_NEWSROOM/audio/check.txt" || true
```

Compare the transcript sentence by sentence. Punctuation, spoken numbers,
and names can differ; investigate any missing claim in a shorter listening
window. Listen to the beginning, a middle transition, and the ending. The
transcript checks completeness; a person still decides whether the voice
sounds right. Keep the original MP3/AIFF, final M4A, script and transcript
privately.

## 5. Build and rebuild the feed locally

Make a square, opaque **RGB** PNG or JPEG show cover, 1400–3000 pixels per
side (3000 preferred), without alpha or transparency metadata. Export it to
`$MP_NEWSROOM/audio/cover.png`. Apple's
[cover specification](https://podcasters.apple.com/support/5514-show-cover-template)
and [artwork troubleshooting](https://podcasters.apple.com/support/902-troubleshooting-artwork-issues)
have current details. The builder checks dimensions, RGB, opacity and file
extension. It copies cover and audio into `MP_FEED`, writes `feed.xml` and
`episodes.json`, and never uploads. `--base-url` must match the future HTTPS
location of that directory. A rehearsal can use `https://example.invalid/podcast`.

```bash
MP_BASE="https://example.invalid/podcast"  # replace with the chosen host and path later
uv run --no-project --python 3.13 --with Pillow python "$MP_SOURCE/scripts/build_podcast_feed.py" \
  --output-dir "$MP_FEED" --base-url "$MP_BASE" \
  --audio "$MP_NEWSROOM/audio/edition.m4a" --artwork "$MP_NEWSROOM/audio/cover.png" \
  --show-title 'My Paper' --show-description 'A spoken daily paper' \
  --author 'My Name' --episode-title 'My first edition' \
  --episode-description 'The main story and what to do' --dry-run
# Repeat without --dry-run to write local files after reviewing the plan.
```

RSS includes a stable GUID, RFC 2822 date, show title, description, language,
author, category, explicit label, artwork, episode title, notes, duration,
and an enclosure whose length is the audio file's actual byte count. A
private-by-URL feed includes `itunes:block`; use `--visibility public` only
when public directory submission is intended. An identical audio file is
treated as the **existing episode**: rerunning the builder regenerates feed
metadata and URLs without duplicating it or changing its GUID/date. Thus,
after choosing a host, rerun with the real `MP_BASE` and any visibility
change before upload. Existing episode title/notes are retained; this tool
does not edit an old episode's content. A new audio file appends a new episode
to the same durable `MP_FEED`. When changing artwork, rerun the builder with
a new ASCII filename, for example `--cover-name cover-2026-10.png`, so Apple's
image URL changes; review and upload the new file.

## 6. Host and verify, if the reader chooses to publish

An unlisted feed is **private by URL only**: anyone with that URL can fetch
its XML and audio. `itunes:block` asks directories not to list it; it is not
access control. The listener's phone must reach the HTTPS host. For one
owner-operated option, use a reader-controlled server with
[Caddy's static file server](https://caddyserver.com/docs/caddyfile/directives/file_server).
The owner points DNS at the server, provisions HTTPS and an upload-writable
`/srv/podcast` directory, opens inbound TCP 80/443, and chooses an unlisted
ASCII path. This example
uses `audio.example.org/reader-7f4c2e`; replace both values. Caddy's
[installation instructions](https://caddyserver.com/docs/install) cover the
host. Configure its Caddyfile on that host:

```caddyfile
audio.example.org {
  root * /srv/podcast
  @feed path /reader-7f4c2e/feed.xml
  header @feed Content-Type application/rss+xml
  @m4a path /reader-7f4c2e/episodes/*.m4a
  header @m4a Content-Type audio/x-m4a
  @mp3 path /reader-7f4c2e/episodes/*.mp3
  header @mp3 Content-Type audio/mpeg
  file_server
}
```

On a packaged Caddy host, save that block in `/etc/caddy/Caddyfile`, ensure
the `caddy` user can read `/srv/podcast`, then validate and reload the
[service](https://caddyserver.com/docs/running):

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
systemctl status caddy
```

After the owner has reviewed the generated local feed and granted upload
access, set `MP_BASE=https://audio.example.org/reader-7f4c2e`, rerun the
builder with the same audio to rewrite its URLs, and upload **only** the
feed, cover and `episodes/`. Keep `episodes.json` local and backed up. This
is an owner publishing step, not part of the builder:

```bash
rsync -a --exclude='episodes.json' --exclude='*.tmp' "$MP_FEED/" \
  'upload@audio.example.org:/srv/podcast/reader-7f4c2e/'
MP_EPISODE=$(uv run --no-project --python 3.13 python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))[-1]["file"])' "$MP_FEED/episodes.json")
curl -fsSI "$MP_BASE/feed.xml"                 # 200, application/rss+xml
curl -fsSI "$MP_BASE/cover.png"                # 200, image/png, Last-Modified
curl -fsSI "$MP_BASE/episodes/$MP_EPISODE"     # 200, audio/x-m4a
curl -fsS -D - -o /dev/null -H 'Range: bytes=0-15' \
  "$MP_BASE/episodes/$MP_EPISODE"             # 206, Content-Range: bytes 0-15/...
curl -fsS "$MP_BASE/feed.xml" -o "$MP_NEWSROOM/audio/host-feed.xml"
cmp "$MP_FEED/feed.xml" "$MP_NEWSROOM/audio/host-feed.xml"
```

Check each status and content type; the range response must be `206`, not
`200`. The cover's HEAD response needs `Last-Modified` for Apple's
[artwork refresh checks](https://podcasters.apple.com/support/902-troubleshooting-artwork-issues).
If the cover was rebuilt with `--cover-name`, use that filename in the HEAD
check instead of `cover.png`.
The [RSS requirements](https://podcasters.apple.com/support/823-podcast-requirements)
also require GET/HEAD, byte ranges, enclosure URL/length/type, artwork, and
at least one episode for directory submission. A `127.0.0.1` test proves
local files and server behavior, not host reachability or Apple acceptance.
For each later edition, keep the same `MP_FEED`, append with a new audio file,
check the feed and host responses, then upload the new files. Do not replace
or discard `episodes.json` or old media.

For a public directory listing, use `--visibility public` on the builder,
host the files at stable publicly reachable URLs, then the show owner signs
in to Apple Podcasts Connect, adds an RSS show, validates it, reviews content
rights, contact and availability, and explicitly publishes it. See Apple's
[submission steps](https://podcasters.apple.com/support/897-submit-a-show).

For an unlisted feed, the listener opens Apple Podcasts on iPhone, then
**Library → Edit → Add a Show by URL**, enters the reachable feed URL, and
taps Follow. On Mac, use **File → Add a Show by URL**. Apple says this
[tests a feed without submitting it to the directory](https://podcasters.apple.com/support/828-test-your-podcast).
The final phone test is to see the cover, stream, download and seek within
the episode. Record the actual host and feed URL in private `DELIVERY.md`.
