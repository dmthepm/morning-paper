# A spoken edition

An audio edition is a second output from the same reported paper. The agent
writes and checks the words; local tools render audio and build a feed. Keep
reader sources, account choices, keys, feed URLs, and episode drafts in the
reader's private newsroom. This page is a reusable creation recipe. Nothing
here uploads a file or submits a show.

## 1. Write for the ear

Start with the edition's final `draft.md` and its source notes, after the
editorial and factual review. Write a separate `audio/script.txt` in the
private newsroom. Lead with the point and the action, then give the few facts
needed to understand it. Use short sentences, spoken numbers, and natural
transitions. Remove tables, Markdown, URLs, file paths, citation codes, and
visual references; preserve the strength and attribution of claims. Never
invent a headline or imply an unverified item is settled. At roughly 150
spoken words per minute, a 30-second test is about 75 words. Read it aloud
once before rendering. Put source links and optional reply prompts in episode
notes, where the listener can look later.

## 2. Choose a voice and route

Audition the same short paragraph in two or three voices at normal speed and
on the phone or headphones the reader uses. Judge intelligibility of names,
numbers, pauses, and long-form comfort. Record the chosen provider, model,
voice ID, language, and pronunciation notes in the private newsroom; the
paper's editorial `preferences/voice.md` is a different choice. Re-audition
after changing a model or voice. Only use a cloned voice with permission.

[ElevenLabs TTS](https://elevenlabs.io/docs/overview/capabilities/text-to-speech)
is the documented default. Its [direct API](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
accepts a voice ID and model ID; the reader can also choose an ElevenLabs
endpoint through fal. These are alternate routes to the same provider, with
their own account and billing. A local voice such as macOS `say` is suitable
for a free workflow rehearsal, but is not a substitute for the reader's voice
approval. Check current model availability and terms before a paid render.

Put only variable names in instructions and versioned files. For the direct
route, load `ELEVENLABS_API_KEY` from the reader's secret store or private
`~/.config/morning-paper/env.sh`. For a fal route, configure `FAL_KEY` in that
route's private secret store. Never put a value in `DELIVERY.md`, a command
line, or the feed directory. A zero-cost preflight checks the selected route,
model, voice ID, script character count, and a current price/usage limit **on
the provider's own account page**; it does not call TTS. The first real
audition or render requires the reader's approval of its cost and voice.

## 3. Render and check

Render the reviewed script to a local file in the private newsroom. If a
provider returns MP3, keep that original and make an AAC/M4A listening copy;
if it returns PCM, encode directly. Use `ffmpeg` to normalize the *final*
audio to about -16 LUFS integrated with true peak no higher than -1 dBTP,
then encode mono AAC at 44.1 or 48 kHz and 64–128 kb/s. MP3 at the same rate
is an alternative. Apple [accepts both for RSS and recommends AAC in an MP4
container](https://podcasters.apple.com/support/893-audio-requirements).

```bash
# Example for a local source file; inspect loudnorm's first-pass measurements
# before setting measured_* values for the second pass.
ffmpeg -i audio/source.wav -af loudnorm=I=-16:TP=-1:LRA=11:print_format=json -f null -
ffmpeg -i audio/source.wav -af 'loudnorm=I=-16:TP=-1:LRA=11:measured_I=...:measured_TP=...:measured_LRA=...:measured_thresh=...:offset=...:linear=true' -ar 44100 -ac 1 -c:a aac -b:a 96k -movflags +faststart audio/edition.m4a
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 audio/edition.m4a
```

Listen to the beginning, a middle transition, and the ending. Transcribe with
local Whisper or another speech recognizer, compare it with `script.txt`, and
recheck apparent gaps in shorter windows; recognizers can skip words at chunk
boundaries. Confirm names, ending, pace, and that no private content was
accidentally spoken. The transcript checks completeness; a person still
decides whether the voice sounds right.

## 4. Build a feed locally

Make a square, opaque PNG or JPEG cover between 1400 and 3000 pixels on each
side (3000 preferred). Apple's [show cover specification](https://podcasters.apple.com/support/5514-show-cover-template)
has the current details. `scripts/build_podcast_feed.py` copies the cover and
audio into a **local output directory** and creates `feed.xml` and
`episodes.json`. It never uploads. Keep that directory private until the
reader chooses hosting. Use a base URL that will later serve the directory
over HTTPS; `example.invalid` is suitable for an offline rehearsal.

```bash
python3 scripts/build_podcast_feed.py \
  --output-dir /tmp/my-paper-feed --base-url https://example.invalid/podcast \
  --audio audio/edition.m4a --artwork audio/cover.png \
  --show-title 'My Paper' --show-description 'A spoken daily paper' \
  --author 'My Name' --episode-title 'My first edition' \
  --episode-description 'The main story and what to do' --dry-run
# Remove --dry-run only when the local plan is correct.
```

The builder uses RSS 2.0 with a stable GUID, RFC 2822 date, show title,
description, language, author, category, explicit label, artwork, episode
title, notes, duration, and an enclosure whose `length` is the audio file's
actual byte count. It defaults to `itunes:block` for a private-by-URL feed;
use `--visibility public` only when a public directory listing is intended.
An episode with identical audio bytes is refused instead of duplicated. The
cover is shared by the show; reuse the same artwork on later runs. Changing
the image extension on a later run needs a deliberate feed review.

Before any upload, parse the XML and check each enclosure URL, MIME type,
length, GUID, artwork URL and dimensions. On the intended host, the feed,
cover and media must respond to GET and HEAD; media must answer a byte-range
request with `206 Partial Content`. The [Apple RSS requirements](https://podcasters.apple.com/support/823-podcast-requirements)
also require a reachable RSS URL and at least one episode for directory
submission. A local `127.0.0.1` test proves the files and server behavior,
not reachability or acceptance by Apple.

## 5. Choose hosting and follow in Apple Podcasts

- **Private by URL:** put the generated directory on an HTTPS static host
  that serves HEAD and byte ranges. Share the unlisted feed URL only with
  intended listeners. The URL is a bearer link: anyone who gets it can fetch
  the feed and audio. `itunes:block` asks directories not to list it; it is
  not access control. The listener's phone must be able to reach the host.
- **Public directory:** host the same files at stable, publicly reachable
  HTTPS URLs, build with `--visibility public`, then the show owner signs in
  to Apple Podcasts Connect, adds a show with an RSS feed, validates it,
  reviews rights and availability, and publishes it. This is a separate
  owner action; the local builder never does it. See Apple's
  [submission steps](https://podcasters.apple.com/support/897-submit-a-show).

For an unlisted feed, the listener opens Apple Podcasts on iPhone, then
**Library → Edit → Add a Show by URL**, enters the reachable feed URL, and
taps Follow. On Mac, use **File → Add a Show by URL**. Apple says this
[tests a feed without submitting it to the directory](https://podcasters.apple.com/support/828-test-your-podcast).
The final phone test is to see the cover, stream, download, and seek within
the episode. Record the chosen host and URL in private `DELIVERY.md`, not in
this repository.
