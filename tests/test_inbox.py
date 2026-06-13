from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

from morning_paper import cli
from morning_paper.article_print import Article, ArticleExtractionError
from morning_paper.config import ContributorConfig, InboxConfig, MorningPaperConfig
from morning_paper.inbox import derive_smtp_host, extract_first_url, poll_inbox


READER = "reader@example.com"
SAM = "sam@example.com"


def _mail(sender: str, subject: str, body: str, *, html: bool = False) -> bytes:
    msg = EmailMessage()
    msg["From"] = f"Somebody <{sender}>"
    msg["To"] = READER
    msg["Subject"] = subject
    if html:
        msg.set_content(body, subtype="html")
    else:
        msg.set_content(body)
    return msg.as_bytes()


class FakeIMAP:
    """Stands in for imaplib.IMAP4_SSL; one mailbox dict shared per test."""

    instances: list["FakeIMAP"] = []
    mailbox_data: dict[bytes, bytes] = {}

    def __init__(self, host: str) -> None:
        self.host = host
        self.logged_in: tuple[str, str] | None = None
        self.selected: str | None = None
        self.seen: list[bytes] = []
        FakeIMAP.instances.append(self)

    def login(self, user: str, password: str):
        self.logged_in = (user, password)
        return ("OK", [b"Logged in"])

    def select(self, mailbox: str):
        self.selected = mailbox
        return ("OK", [b"1"])

    def search(self, charset, *criteria):
        ids = b" ".join(sorted(FakeIMAP.mailbox_data.keys()))
        return ("OK", [ids])

    def fetch(self, msg_id: bytes, spec: str):
        assert "PEEK" in spec, "fetch must use BODY.PEEK so reading never marks Seen"
        return ("OK", [(msg_id + b" (BODY[] {...})", FakeIMAP.mailbox_data[msg_id])])

    def store(self, msg_id: bytes, flags: str, value: str):
        self.seen.append(msg_id)
        return ("OK", [])

    def logout(self):
        return ("BYE", [])

    @classmethod
    def reset(cls, mailbox: dict[bytes, bytes]) -> None:
        cls.instances = []
        cls.mailbox_data = dict(mailbox)


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host: str) -> None:
        self.host = host
        self.logged_in: tuple[str, str] | None = None
        self.sent: list[EmailMessage] = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user: str, password: str):
        self.logged_in = (user, password)

    def send_message(self, message: EmailMessage):
        self.sent.append(message)

    @classmethod
    def reset(cls) -> None:
        cls.instances = []


def _article() -> Article:
    sentence = "A complete sentence with enough words to look like real prose."
    return Article(
        url="https://example.com/story",
        title="A Staged Story",
        author="Author",
        source_name="Example",
        body="",
        blocks=[("paragraph", sentence) for _ in range(5)],
    )


class InboxTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.config = MorningPaperConfig()
        self.config.outputs.directory = self.tmp / "out"
        self.config.outputs.directory.mkdir(parents=True)
        self.config.inbox = InboxConfig(
            enabled=True,
            imap_host="imap.example.com",
            imap_user=READER,
            subject_tag="paper",
            contributors=[ContributorConfig(email=SAM, name="Sam")],
            reply=True,
        )
        env = patch.dict("os.environ", {"MORNING_PAPER_IMAP_PASSWORD": "app-password"})
        env.start()
        self.addCleanup(env.stop)
        FakeSMTP.reset()

    def _poll(self, mailbox: dict[bytes, bytes], **kwargs) -> dict:
        FakeIMAP.reset(mailbox)
        with patch("imaplib.IMAP4_SSL", FakeIMAP), patch("smtplib.SMTP_SSL", FakeSMTP):
            return poll_inbox(self.config, date_str="2026-06-12", **kwargs)

    def _queue(self) -> list[dict]:
        queue_file = self.tmp / "out" / "staging" / "2026-06-12" / "queue.json"
        if not queue_file.exists():
            return []
        return json.loads(queue_file.read_text(encoding="utf-8"))


class MastheadGateTest(InboxTestCase):
    def test_non_masthead_sender_is_skipped_and_left_unread(self) -> None:
        result = self._poll(
            {
                b"1": _mail("stranger@example.com", "paper: read this", "https://example.com/story"),
                b"2": _mail(SAM, "paper: a note", "Just a note for tomorrow."),
            }
        )
        self.assertEqual(result["polled"], 2)
        self.assertEqual([s["from"] for s in result["skipped"]], ["stranger@example.com"])
        self.assertIn("masthead", result["skipped"][0]["reason"])
        self.assertEqual(len(result["staged"]), 1)
        self.assertEqual(result["staged"][0]["from"], SAM)
        # only Sam's message is marked Seen; the stranger's stays unread
        self.assertEqual(FakeIMAP.instances[0].seen, [b"2"])
        # the stranger's URL never reached the queue
        self.assertEqual(len(self._queue()), 1)
        self.assertEqual(self._queue()[0]["contributor"], "Sam")

    def test_subject_tag_filter(self) -> None:
        result = self._poll({b"1": _mail(SAM, "lunch on sunday?", "no link here")})
        self.assertEqual(result["staged"], [])
        self.assertIn("subject tag", result["skipped"][0]["reason"])
        self.assertEqual(FakeIMAP.instances[0].seen, [])


class StagingTest(InboxTestCase):
    def test_url_mail_stages_via_fetch_article(self) -> None:
        with patch("morning_paper.staging.fetch_article", return_value=_article()) as fetched:
            result = self._poll(
                {b"1": _mail(SAM, "[paper] worth your time", "you should read this https://example.com/story ok")}
            )
        fetched.assert_called_once()
        self.assertEqual(fetched.call_args[0][0], "https://example.com/story")
        staged = result["staged"][0]
        self.assertEqual(staged["kind"], "url")
        self.assertEqual(staged["source"], "https://example.com/story")
        self.assertEqual(staged["contributor"], "Sam")
        self.assertEqual(staged["title"], "worth your time")
        self.assertEqual(self._queue()[0]["contributor"], "Sam")

    def test_note_only_mail_stages_as_note(self) -> None:
        result = self._poll({b"1": _mail(SAM, "paper: from the garden", "The tomatoes finally came in.")})
        staged = result["staged"][0]
        self.assertEqual(staged["kind"], "note")
        self.assertEqual(staged["source"], SAM)
        self.assertEqual(staged["title"], "from the garden")
        queue = self._queue()
        self.assertEqual(queue[0]["kind"], "note")
        staged_md = (self.tmp / "out" / "staging" / "2026-06-12" / f"{queue[0]['slug']}.md").read_text(encoding="utf-8")
        self.assertIn("tomatoes", staged_md)

    def test_html_only_mail_is_treated_as_untrusted_text(self) -> None:
        body = (
            "<p>read <a href=\"https://example.com/story\">this</a></p>"
            "<script>steal('credentials')</script>"
        )
        with patch("morning_paper.staging.fetch_article", return_value=_article()):
            result = self._poll({b"1": _mail(SAM, "paper", body, html=True)})
        staged = result["staged"][0]
        self.assertEqual(staged["kind"], "url")
        self.assertEqual(staged["source"], "https://example.com/story")
        # nothing from the script block survives anywhere
        self.assertNotIn("steal", json.dumps(result))

    def test_failed_extraction_skips_and_never_marks_seen(self) -> None:
        with patch(
            "morning_paper.staging.fetch_article",
            side_effect=ArticleExtractionError("could not extract"),
        ):
            result = self._poll({b"1": _mail(SAM, "paper: read", "https://example.com/broken")})
        self.assertEqual(result["staged"], [])
        self.assertIn("extraction failed", result["skipped"][0]["reason"])
        self.assertEqual(FakeIMAP.instances[0].seen, [])
        self.assertEqual(self._queue(), [])
        self.assertEqual(FakeSMTP.instances, [])


class DryRunTest(InboxTestCase):
    def test_dry_run_stages_nothing_and_touches_nothing(self) -> None:
        result = self._poll(
            {b"1": _mail(SAM, "paper: a note", "Just a note.")},
            dry_run=True,
        )
        self.assertTrue(result["dry_run"])
        self.assertEqual(len(result["staged"]), 1)
        self.assertTrue(result["staged"][0]["would_stage"])
        self.assertEqual(result["replied"], 0)
        self.assertEqual(self._queue(), [])
        self.assertEqual(FakeIMAP.instances[0].seen, [])
        self.assertEqual(FakeSMTP.instances, [])


class ReplyTest(InboxTestCase):
    def test_reply_is_warm_from_the_reader_with_page_estimate(self) -> None:
        result = self._poll({b"1": _mail(SAM, "paper: from the garden", "The tomatoes finally came in.")})
        self.assertEqual(result["replied"], 1)
        smtp = FakeSMTP.instances[0]
        # smtp host derived from the imap host; sender is the reader's own address
        self.assertEqual(smtp.host, "smtp.example.com")
        self.assertEqual(smtp.logged_in, (READER, "app-password"))
        message = smtp.sent[0]
        self.assertEqual(message["From"], READER)
        self.assertEqual(message["To"], SAM)
        self.assertEqual(message["Subject"], "Re: paper: from the garden")
        body = message.get_content()
        self.assertIn("Got it", body)
        self.assertIn("Morning Paper tomorrow morning", body)
        self.assertIn("about 1 page", body)
        self.assertIn("☕", body)

    def test_reply_disabled_sends_nothing(self) -> None:
        self.config.inbox.reply = False
        result = self._poll({b"1": _mail(SAM, "paper: note", "A note.")})
        self.assertEqual(result["replied"], 0)
        self.assertEqual(FakeSMTP.instances, [])
        self.assertEqual(len(result["staged"]), 1)


class HelpersTest(unittest.TestCase):
    def test_derive_smtp_host(self) -> None:
        self.assertEqual(derive_smtp_host("imap.gmail.com"), "smtp.gmail.com")
        self.assertEqual(derive_smtp_host("imap.mail.me.com"), "smtp.mail.me.com")
        self.assertEqual(derive_smtp_host("mail.example.org"), "mail.example.org")

    def test_extract_first_url(self) -> None:
        self.assertEqual(
            extract_first_url("look: https://example.com/a?x=1 and https://example.com/b"),
            "https://example.com/a?x=1",
        )
        self.assertEqual(extract_first_url("no links"), "")


class CliInboxTest(unittest.TestCase):
    def _write_config(self, tmp: Path, *, inbox_block: str) -> Path:
        config_path = tmp / "config.yaml"
        config_path.write_text(
            f"""name: Morning Paper
timezone: America/Los_Angeles
outputs:
  directory: {tmp / 'out'}
{inbox_block}
""",
            encoding="utf-8",
        )
        return config_path

    def test_inbox_json_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            config_path = self._write_config(
                tmp,
                inbox_block=f"""inbox:
  enabled: true
  imap_host: imap.example.com
  imap_user: {READER}
  contributors:
    - email: {SAM}
      name: Sam
""",
            )
            FakeIMAP.reset({b"1": _mail(SAM, "paper: note", "A note for tomorrow.")})
            FakeSMTP.reset()
            stdout = io.StringIO()
            with patch.dict("os.environ", {"MORNING_PAPER_IMAP_PASSWORD": "app-password"}):
                with patch("imaplib.IMAP4_SSL", FakeIMAP), patch("smtplib.SMTP_SSL", FakeSMTP):
                    with redirect_stdout(stdout):
                        rc = cli.main(["inbox", "poll", "--config", str(config_path)])
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            for key in ("polled", "staged", "replied", "skipped", "edition_date", "dry_run"):
                self.assertIn(key, payload)
            self.assertEqual(payload["polled"], 1)
            self.assertEqual(len(payload["staged"]), 1)
            self.assertEqual(payload["replied"], 1)
            self.assertEqual(payload["skipped"], [])

    def test_inbox_disabled_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            config_path = self._write_config(tmp, inbox_block="")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                rc = cli.main(["inbox", "--config", str(config_path)])
            self.assertEqual(rc, 1)
            message = stderr.getvalue()
            self.assertIn("not configured", message)
            self.assertIn("inbox.enabled", message)
            self.assertIn("docs/inbox.md", message)

    def test_enabled_inbox_requires_masthead(self) -> None:
        from morning_paper.config import ConfigError, load_config

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            config_path = self._write_config(
                tmp,
                inbox_block=f"""inbox:
  enabled: true
  imap_host: imap.example.com
  imap_user: {READER}
""",
            )
            with self.assertRaises(ConfigError) as ctx:
                load_config(config_path)
            self.assertIn("contributors", str(ctx.exception))

    def test_password_in_config_is_rejected(self) -> None:
        from morning_paper.config import ConfigError, load_config

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            config_path = self._write_config(
                tmp,
                inbox_block=f"""inbox:
  enabled: true
  imap_host: imap.example.com
  imap_user: {READER}
  imap_password: hunter2
  contributors:
    - email: {SAM}
      name: Sam
""",
            )
            with self.assertRaises(ConfigError) as ctx:
                load_config(config_path)
            self.assertIn("MORNING_PAPER_IMAP_PASSWORD", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
