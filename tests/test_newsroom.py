from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from morning_paper import __version__, cli


class NewsroomScaffoldTest(unittest.TestCase):
    def test_newsroom_init_writes_resumable_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "newsroom"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["newsroom", "init", str(root), "--name", "Desk Paper"])
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["newsroom_path"], str(root.resolve()))

            required = [
                "SETUP.md",
                "setup-state.json",
                "CLAUDE.md",
                "README.md",
                "specs/_template.md",
                "specs/the-read.md",
                "specs/front-page.md",
                "specs/reading.md",
                "preferences/voice.md",
                "preferences/algorithm-prior.yaml",
                "preferences/checks.yaml",
                "collectors/_lib.sh",
                "collectors/run_all.sh",
                "collectors/shipped.sh",
                "collectors/read.sh",
                "collectors/local-drop.sh",
                "memory/reads-ledger.md",
                "memory/MEMORY.md",
                "memory/threads/README.md",
                "editions/.gitignore",
                "editions/operator-answers.template.md",
                "examples/edition-skeleton.md",
                "inbox/.gitkeep",
            ]
            for relative in required:
                self.assertTrue((root / relative).exists(), relative)

            state = json.loads((root / "setup-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["installed_version"], __version__)
            self.assertEqual(state["newsroom_path"], str(root.resolve()))
            self.assertIn("doctor", state)
            self.assertIn("demo", state)
            self.assertIn("plugin_state", state)
            self.assertIn("source_choices", state)
            self.assertIn("printer_choice", state)
            self.assertIn("pending_questions", state)
            self.assertIn("next_action", state)

            setup = (root / "SETUP.md").read_text(encoding="utf-8")
            self.assertIn("Installed version", setup)
            self.assertIn("Demo PDF", setup)
            self.assertIn("Source Choices", setup)
            self.assertIn("Printer", setup)

            constitution = (root / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("The Read leads", constitution)
            self.assertIn('Empty sources print "not configured"', constitution)

            the_read = (root / "specs" / "the-read.md").read_text(encoding="utf-8")
            self.assertIn("The four moves", the_read)
            self.assertIn("NO MIRRORING", the_read)

            front_page = (root / "specs" / "front-page.md").read_text(encoding="utf-8")
            self.assertIn("headline written as a judgment with a", front_page)
            self.assertIn("verb", front_page)

            reading = (root / "specs" / "reading.md").read_text(encoding="utf-8")
            self.assertIn("Source mix", reading)
            self.assertIn("Fresh vs repeat", reading)

            prior = (root / "preferences" / "algorithm-prior.yaml").read_text(encoding="utf-8")
            self.assertIn("own your algorithm", prior)
            self.assertIn("pure velocity", prior)

            skeleton = (root / "examples" / "edition-skeleton.md").read_text(encoding="utf-8")
            self.assertIn("mp-stats", skeleton)
            self.assertIn("Write a Headline With a Verb", skeleton)

            for script in ("_lib.sh", "run_all.sh", "shipped.sh", "read.sh", "local-drop.sh"):
                self.assertTrue(os.access(root / "collectors" / script, os.X_OK), script)
                subprocess.run(["bash", "-n", str(root / "collectors" / script)], check=True)

    def test_newsroom_init_does_not_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "newsroom"
            rc = cli.main(["newsroom", "init", str(root)])
            self.assertEqual(rc, 0)
            voice = root / "preferences" / "voice.md"
            voice.write_text("custom voice\n", encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["newsroom", "init", str(root)])
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertIn("preferences/voice.md", payload["skipped"])
            self.assertEqual(voice.read_text(encoding="utf-8"), "custom voice\n")

            rc = cli.main(["newsroom", "init", str(root), "--force"])
            self.assertEqual(rc, 0)
            self.assertNotEqual(voice.read_text(encoding="utf-8"), "custom voice\n")

    def test_newsroom_state_updates_json_and_setup_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "newsroom"
            self.assertEqual(cli.main(["newsroom", "init", str(root)]), 0)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    [
                        "newsroom",
                        "state",
                        str(root),
                        "--set",
                        "demo.pdf_path=/tmp/demo.pdf",
                        "--set",
                        "demo.opened_on_screen=true",
                        "--set",
                        "doctor.strict_passed=true",
                        "--set",
                        "plugin_state.codex=installed",
                        "--set",
                        "printer_choice.command=lp demo.pdf",
                        "--pending",
                        "Which feeds should I add?",
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            state = payload["state"]
            self.assertEqual(state["demo"]["pdf_path"], "/tmp/demo.pdf")
            self.assertTrue(state["demo"]["opened_on_screen"])
            self.assertTrue(state["doctor"]["strict_passed"])
            self.assertEqual(state["plugin_state"]["codex"], "installed")
            self.assertEqual(state["printer_choice"]["command"], "lp demo.pdf")
            self.assertEqual(state["pending_questions"], ["Which feeds should I add?"])

            persisted = json.loads((root / "setup-state.json").read_text(encoding="utf-8"))
            self.assertTrue(persisted["demo"]["opened_on_screen"])
            setup = (root / "SETUP.md").read_text(encoding="utf-8")
            self.assertIn("<!-- morning-paper setup-state:begin -->", setup)
            self.assertIn("Demo PDF: /tmp/demo.pdf", setup)
            self.assertIn("Codex: installed", setup)
            self.assertIn("Which feeds should I add?", setup)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["newsroom", "state", str(root), "--clear-pending"])
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["state"]["pending_questions"], [])
            self.assertIn("- None.", (root / "SETUP.md").read_text(encoding="utf-8"))

    def test_newsroom_state_requires_existing_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            from contextlib import redirect_stderr

            with redirect_stderr(stderr):
                rc = cli.main(["newsroom", "state", str(Path(tmp) / "missing"), "--set", "status=ready"])
            self.assertEqual(rc, 1)
            self.assertIn("run `morning-paper newsroom init", stderr.getvalue())

    def test_scaffolded_collectors_read_the_explicit_edition_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "newsroom"
            bin_dir = tmp_path / "bin"
            log = tmp_path / "calls.log"
            bin_dir.mkdir()
            fake = bin_dir / "morning-paper"
            fake.write_text(f"#!/usr/bin/env bash\necho \"$@\" >> {log!s}\n", encoding="utf-8")
            os.chmod(fake, 0o755)
            rc = cli.main(["newsroom", "init", str(root)])
            self.assertEqual(rc, 0)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
            result = subprocess.run(
                ["bash", "run_all.sh", "2026-06-22"],
                cwd=root / "collectors",
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("collectors for 2026-06-22", result.stdout)
            self.assertIn("queue list --date 2026-06-22", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
