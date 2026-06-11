"""The contributor inbox — "the masthead".

People the reader trusts email articles in; they land in tomorrow's staging
queue; the sender gets a warm confirmation back. Stdlib only: imaplib,
smtplib, email — no new dependencies, no webhook, no service.

Security model, stated plainly:
- The `inbox.contributors` allowlist is THE gate. Mail from any other sender
  is skipped and reported, never staged — regardless of subject or content.
- Every message body is treated as untrusted text. HTML payloads have their
  script/style blocks removed and all tags stripped before anything is read
  from them; nothing from a mail is ever executed or rendered as live HTML.
- The mail password is NEVER in config. It comes from the
  MORNING_PAPER_IMAP_PASSWORD environment variable (and
  MORNING_PAPER_SMTP_PASSWORD when the reply credential is distinct).
- A message is marked Seen ONLY after its content staged successfully, so a
  failed poll leaves the mail unread for the next attempt.
"""

from __future__ import annotations

import html as html_lib
import imaplib
import os
import re
import smtplib
from dataclasses import asdict
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parseaddr

from .article_print import ArticleExtractionError
from .config import InboxConfig, MorningPaperConfig
from .staging import default_edition_date, stage_markdown, stage_url


IMAP_PASSWORD_ENV = "MORNING_PAPER_IMAP_PASSWORD"
SMTP_PASSWORD_ENV = "MORNING_PAPER_SMTP_PASSWORD"

_URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+")
_SCRIPT_STYLE_RE = re.compile(r"<\s*(script|style)\b.*?<\s*/\s*\1\s*>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_REPLY_PREFIX_RE = re.compile(r"^\s*(re|fwd?)\s*:\s*", re.IGNORECASE)


class InboxError(RuntimeError):
    pass


def derive_smtp_host(imap_host: str) -> str:
    """imap.gmail.com -> smtp.gmail.com; imap.mail.me.com -> smtp.mail.me.com.

    The common providers follow the imap./smtp. naming convention; anything
    that does not can set `inbox.smtp_host` explicitly.
    """
    if imap_host.startswith("imap."):
        return "smtp." + imap_host[len("imap."):]
    return imap_host


def _strip_html(raw: str) -> str:
    """Reduce an HTML payload to untrusted plain text — scripts gone first."""
    text = _SCRIPT_STYLE_RE.sub(" ", raw)
    text = _TAG_RE.sub(" ", text)
    text = html_lib.unescape(text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _message_text(msg) -> str:
    """Best plain-text reading of a message; HTML-only mail is stripped to text."""
    plain_parts: list[str] = []
    html_parts: list[str] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        content_type = part.get_content_type()
        if content_type not in {"text/plain", "text/html"}:
            continue  # attachments and anything exotic are ignored, not parsed
        try:
            payload = part.get_content()
        except Exception:
            continue
        if not isinstance(payload, str):
            continue
        if content_type == "text/plain":
            plain_parts.append(payload)
        else:
            html_parts.append(payload)
    if plain_parts:
        return "\n\n".join(plain_parts).strip()
    if html_parts:
        # URLs often live only in href attributes; keep them findable by
        # scanning the de-scripted source before tags are stripped.
        descripted = " ".join(_SCRIPT_STYLE_RE.sub(" ", part) for part in html_parts)
        text = _strip_html(" ".join(html_parts))
        url = _URL_RE.search(descripted)
        if url and not _URL_RE.search(text):
            text = f"{url.group(0)}\n\n{text}"
        return text
    return ""


def extract_first_url(text: str) -> str:
    match = _URL_RE.search(text)
    return match.group(0).rstrip(".,;") if match else ""


def _clean_subject(subject: str, tag: str) -> str:
    cleaned = subject
    while _REPLY_PREFIX_RE.match(cleaned):
        cleaned = _REPLY_PREFIX_RE.sub("", cleaned, count=1)
    if tag:
        cleaned = re.sub(rf"\[\s*{re.escape(tag)}\s*\]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(rf"(?i)\b{re.escape(tag)}\b", "", cleaned, count=1)
    return cleaned.strip(" -—:\t")


def _est_pages_phrase(pages: int) -> str:
    return "about 1 page" if pages <= 1 else f"about {pages} pages"


def reply_body(config: MorningPaperConfig, est_pages: int) -> str:
    return (
        f"Got it — this is in {config.name} tomorrow morning "
        f"({_est_pages_phrase(est_pages)}). ☕"
    )


def _send_replies(config: MorningPaperConfig, replies: list[dict]) -> tuple[int, list[str]]:
    """One SMTP session for all confirmations; failures warn, never crash."""
    inbox = config.inbox
    smtp_host = inbox.smtp_host or derive_smtp_host(inbox.imap_host)
    smtp_user = inbox.smtp_user or inbox.imap_user
    password = os.environ.get(SMTP_PASSWORD_ENV) or os.environ.get(IMAP_PASSWORD_ENV, "")
    sent = 0
    warnings: list[str] = []
    try:
        with smtplib.SMTP_SSL(smtp_host) as smtp:
            smtp.login(smtp_user, password)
            for entry in replies:
                message = EmailMessage()
                message["From"] = smtp_user
                message["To"] = entry["to"]
                subject = entry.get("subject") or ""
                message["Subject"] = f"Re: {subject}" if subject else f"Got it — {config.name}"
                message.set_content(reply_body(config, int(entry["est_pages"])))
                try:
                    smtp.send_message(message)
                    sent += 1
                except Exception as exc:
                    warnings.append(f"reply to {entry['to']} failed: {exc}")
    except Exception as exc:
        warnings.append(
            f"could not send confirmations via {smtp_host}: {exc} "
            "(staged items are unaffected)"
        )
    return sent, warnings


def poll_inbox(
    config: MorningPaperConfig,
    *,
    dry_run: bool = False,
    date_str: str | None = None,
) -> dict:
    """Poll the contributor inbox; stage what the masthead sent.

    Returns {polled, staged, replied, skipped, ...}. One bad message never
    crashes the poll — it lands in `skipped` with a reason and stays unread.
    With dry_run, nothing is staged, replied to, or marked Seen; `staged`
    reports what WOULD stage.
    """
    inbox: InboxConfig = config.inbox
    if not inbox.enabled:
        raise InboxError(
            "the contributor inbox is not configured: set `inbox.enabled: true` with "
            "imap_host, imap_user, and a contributors masthead in config.yaml (see docs/inbox.md)"
        )
    masthead = {c.email.lower(): (c.name or c.email) for c in inbox.contributors if c.email}
    if not masthead:
        raise InboxError("inbox.contributors is empty — the masthead is the allowlist; nothing can stage")
    password = os.environ.get(IMAP_PASSWORD_ENV, "")
    if not password:
        raise InboxError(
            f"set the {IMAP_PASSWORD_ENV} environment variable to your mail app password "
            "(passwords never go in config; see docs/inbox.md)"
        )
    edition_date = date_str or default_edition_date(config)
    result: dict = {
        "edition_date": edition_date,
        "dry_run": dry_run,
        "polled": 0,
        "staged": [],
        "replied": 0,
        "skipped": [],
        "warnings": [],
    }
    replies: list[dict] = []
    conn = imaplib.IMAP4_SSL(inbox.imap_host)
    try:
        conn.login(inbox.imap_user, password)
        conn.select(inbox.mailbox)
        status, data = conn.search(None, "UNSEEN")
        if status != "OK":
            raise InboxError(f"IMAP search failed on {inbox.imap_host}/{inbox.mailbox}: {status}")
        message_ids = data[0].split() if data and data[0] else []
        for msg_id in message_ids:
            result["polled"] += 1
            try:
                _process_message(
                    conn, msg_id, config, masthead,
                    edition_date=edition_date, dry_run=dry_run,
                    result=result, replies=replies,
                )
            except Exception as exc:  # never let one bad message kill the poll
                result["skipped"].append({"from": "", "reason": f"unreadable message: {exc}"})
    finally:
        try:
            conn.logout()
        except Exception:
            pass
    if replies and inbox.reply and not dry_run:
        sent, warnings = _send_replies(config, replies)
        result["replied"] = sent
        result["warnings"].extend(warnings)
    return result


def _process_message(
    conn,
    msg_id: bytes,
    config: MorningPaperConfig,
    masthead: dict[str, str],
    *,
    edition_date: str,
    dry_run: bool,
    result: dict,
    replies: list[dict],
) -> None:
    inbox = config.inbox
    # BODY.PEEK keeps the message unread — Seen is set only after success.
    status, data = conn.fetch(msg_id, "(BODY.PEEK[])")
    if status != "OK" or not data or not data[0]:
        result["skipped"].append({"from": "", "reason": "could not fetch message"})
        return
    raw = data[0][1] if isinstance(data[0], (tuple, list)) else data[0]
    msg = message_from_bytes(raw, policy=policy.default)
    sender = parseaddr(str(msg.get("From", "")))[1].lower()
    subject = str(msg.get("Subject", "") or "")
    # THE gate: the masthead allowlist. No sender match, no staging — ever.
    if sender not in masthead:
        result["skipped"].append({"from": sender, "reason": "not on the masthead"})
        return
    if inbox.subject_tag and inbox.subject_tag.lower() not in subject.lower():
        result["skipped"].append(
            {"from": sender, "reason": f"subject tag '{inbox.subject_tag}' missing"}
        )
        return
    contributor = masthead[sender]
    text = _message_text(msg)
    if not text.strip():
        result["skipped"].append({"from": sender, "reason": "empty message"})
        return
    url = extract_first_url(text)
    title = _clean_subject(subject, inbox.subject_tag)
    if dry_run:
        result["staged"].append(
            {
                "from": sender,
                "contributor": contributor,
                "kind": "url" if url else "note",
                "source": url or sender,
                "title": title or ("" if url else f"Note from {contributor}"),
                "would_stage": True,
            }
        )
        return
    if url:
        try:
            item = stage_url(config, url, date_str=edition_date,
                             title=title or None, contributor=contributor)
        except ArticleExtractionError as exc:
            result["skipped"].append({"from": sender, "reason": f"extraction failed: {exc}"})
            return
    else:
        item = stage_markdown(
            config,
            text,
            date_str=edition_date,
            kind="note",
            source=sender,
            title=title or f"Note from {contributor}",
            contributor=contributor,
        )
    conn.store(msg_id, "+FLAGS", "\\Seen")
    result["staged"].append({"from": sender, **asdict(item)})
    if inbox.reply:
        replies.append({"to": sender, "subject": subject, "est_pages": item.est_pages})
