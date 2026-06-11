# The contributor inbox — "the masthead"

People you trust email you articles; they land in tomorrow's staging queue;
the sender gets a warm confirmation back. Your spouse, your co-founder, your
group chat's designated finder-of-things — they become contributors to your
paper, and the paper says so in print: staged contributor items carry a
**FROM SAM** kicker.

No webhook, no service, no new dependency. `morning-paper inbox` polls a
mailbox over IMAP (stdlib only), stages what the masthead sent, and replies
from your own address.

## The sentence to send your contributors

Once it's set up, the entire onboarding for a contributor is one sentence:

> See something I should read? Email it to me with "paper" in the subject — it'll be on my desk tomorrow morning.

That's it. They email a link (or just a note — notes stage too), and the next
edition carries it with their name on the kicker.

## Quick start

1. Add the block to `~/.config/morning-paper/config.yaml`:

```yaml
inbox:
  enabled: true
  imap_host: imap.gmail.com        # or imap.mail.me.com for iCloud
  imap_user: you@gmail.com
  mailbox: INBOX
  # only mail whose subject contains this word is staged; set "" to take all
  subject_tag: paper
  # THE MASTHEAD — the allowlist. Mail from anyone else is never staged.
  contributors:
    - email: someone-you-trust@example.com
      name: Sam
  # send a warm confirmation back from your own address when something stages
  reply: true
  # smtp_host/smtp_user default to the imap values (imap.* host becomes smtp.*)
```

2. Set the password in the environment — **never in config**:

```bash
export MORNING_PAPER_IMAP_PASSWORD="your-app-password"
```

(If your SMTP credential differs from IMAP, also set
`MORNING_PAPER_SMTP_PASSWORD`.) Put the export in
`~/.config/morning-paper/env.sh` alongside any other credentials, and source
it from the shell or scheduled job that runs the poll. A config file
containing any `password` key is rejected with an error pointing here.

3. Preview without touching anything:

```bash
morning-paper inbox --dry-run
```

4. Poll for real:

```bash
morning-paper inbox        # alias: morning-paper inbox poll
```

JSON out:

```json
{
  "edition_date": "2026-06-12",
  "dry_run": false,
  "polled": 3,
  "staged": [ { "slug": "...", "kind": "url", "contributor": "Sam", "est_pages": 4, ... } ],
  "replied": 1,
  "skipped": [ { "from": "stranger@example.com", "reason": "not on the masthead" } ],
  "warnings": []
}
```

## App passwords

Your normal account password will not work (and should never be typed into a
config-adjacent shell anyway). Both major providers issue scoped app
passwords:

**Gmail**
1. Turn on 2-Step Verification (required): myaccount.google.com → Security.
2. Create an app password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   — name it `morning-paper`, copy the 16-character password.
3. Hosts: `imap_host: imap.gmail.com` (SMTP `smtp.gmail.com` is derived
   automatically).

**iCloud**
1. Sign in at [account.apple.com](https://account.apple.com) → Sign-In and
   Security → App-Specific Passwords → generate one named `morning-paper`.
2. Hosts: `imap_host: imap.mail.me.com` (SMTP `smtp.mail.me.com` is derived
   automatically). `imap_user` is your full iCloud address.

## Keeping it tidy: plus-addressing

If you'd rather not poll your whole inbox, give contributors a plus address —
`you+paper@gmail.com` works without any setup (Gmail and iCloud both deliver
plus-addressed mail to the same account). Then add a filter that labels
those messages (Gmail labels are IMAP mailboxes) and point the poll at it:

```yaml
mailbox: paper        # the Gmail label / IMAP folder your filter applies
```

With a dedicated mailbox you can also set `subject_tag: ""` — the address is
the filter, so the subject no longer needs the magic word.

## What gets staged

- **A link** — the first `http(s)` URL in the body is fetched and staged
  exactly like `morning-paper stage <url>`: same extractor, same honest
  truncation flags, same page estimate. Subject (minus the tag) becomes the
  title override.
- **Just a note** — no URL means the mail body stages as a `note`: your
  contributor can send two paragraphs about the garden and it prints.
- Either way the staged item records `contributor: <name>`, and editions
  render it with a FROM <NAME> kicker.

The sender's confirmation (when `reply: true`) is short and warm, sent from
your own address: *"Got it — this is in Morning Paper tomorrow morning
(about 4 pages). ☕"*

## The security model, stated plainly

- **The masthead is the gate.** Mail from any sender not on the
  `contributors` list is skipped and reported in the JSON — never staged, no
  matter what the subject or body says.
- **All mail content is untrusted text.** HTML-only messages have script and
  style blocks removed and every tag stripped before anything is read from
  them; nothing from a mail is ever executed or rendered as live HTML.
- **Seen only on success.** A message is marked read only after its content
  staged. A failed extraction or a crashed poll leaves the mail unread for
  the next attempt — and one bad message never takes down the poll; it lands
  in `skipped` with a reason.
- **No passwords in config.** The credential lives in the environment, and
  the config loader rejects any `password` key in the inbox block.

## In the morning routine

The `edition` skill runs `morning-paper inbox` before composing, so anything
the masthead sent overnight is in the queue by the time the editor reads it.
Running it again is always safe: only unread mail is considered.
