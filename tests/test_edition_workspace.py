from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml

from morning_paper import cli


class EditionWorkspaceTest(unittest.TestCase):
    def _config_path(self, tmp_path: Path) -> Path:
        config_path = tmp_path / "config.yaml"
        rc = cli.main(["init", "--config", str(config_path)])
        self.assertEqual(rc, 0)
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config["outputs"]["directory"] = str(tmp_path / "out")
        config["sources"]["hacker_news"]["enabled"] = False
        config["sources"]["rss"] = []
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        return config_path

    def _minimal_pdf(self, path: Path) -> None:
        path.write_bytes(
            b"%PDF-1.4\n"
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >> endobj\n"
            b"%%EOF\n"
        )

    def test_edition_prepare_writes_all_resume_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            edition_dir = newsroom / "editions" / "2026-06-22"
            self.assertEqual(payload["edition_dir"], str(edition_dir.resolve()))

            expected = {
                "source-inventory.json",
                "collector-report.md",
                "queue-snapshot.json",
                "estimate-result.json",
                "draft.md",
                "render-result.json",
                "review.json",
                "visual-qa.json",
                "final-editor.json",
                "final-editor.md",
                "operator-answers.md",
                "desk-sheet.md",
                "feedback-plan.md",
            }
            self.assertEqual(set(payload["written"]), expected)
            for filename in expected:
                self.assertTrue((edition_dir / filename).exists(), filename)

            source_inventory = json.loads((edition_dir / "source-inventory.json").read_text(encoding="utf-8"))
            self.assertEqual(source_inventory["source_model"]["posture"], "reader_stack_first")
            self.assertIn("work_systems", source_inventory["source_model"]["reader_owned_inputs"])
            self.assertEqual(source_inventory["sources"][0]["id"], "hacker_news")
            self.assertEqual(source_inventory["sources"][0]["status"], "disabled")
            self.assertEqual(source_inventory["newsroom"]["status"], "configured")
            collector_ids = {item["id"] for item in source_inventory["newsroom"]["collectors"]}
            self.assertIn("collector:local-drop", collector_ids)
            queue = json.loads((edition_dir / "queue-snapshot.json").read_text(encoding="utf-8"))
            self.assertEqual(queue["date"], "2026-06-22")
            self.assertEqual(queue["count"], 0)
            estimate_result = json.loads((edition_dir / "estimate-result.json").read_text(encoding="utf-8"))
            self.assertEqual(estimate_result["status"], "pending")
            self.assertIn("morning-paper edition estimate", estimate_result["command"])
            render_result = json.loads((edition_dir / "render-result.json").read_text(encoding="utf-8"))
            self.assertEqual(render_result["status"], "pending")
            self.assertIn("morning-paper render", render_result["command"])
            review = json.loads((edition_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(review["status"], "pending")
            self.assertIn("morning-paper review", review["command"])
            visual_qa = json.loads((edition_dir / "visual-qa.json").read_text(encoding="utf-8"))
            self.assertEqual(visual_qa["status"], "pending")
            self.assertIn("morning-paper edition visual-qa", visual_qa["command"])
            final_editor = json.loads((edition_dir / "final-editor.json").read_text(encoding="utf-8"))
            self.assertEqual(final_editor["status"], "pending")
            self.assertIn("morning-paper edition final-editor", final_editor["command"])
            self.assertIn("Status: pending", (edition_dir / "final-editor.md").read_text(encoding="utf-8"))
            operator_answers = (edition_dir / "operator-answers.md").read_text(encoding="utf-8")
            self.assertIn("Visuals", operator_answers)
            self.assertIn("Delivery", operator_answers)
            self.assertIn("Taste To Save", operator_answers)
            self.assertIn("VISUALS.md", operator_answers)
            self.assertIn("Print Tomorrow", operator_answers)
            desk_sheet = (edition_dir / "desk-sheet.md").read_text(encoding="utf-8")
            self.assertIn("old-desk", desk_sheet)
            self.assertIn("The Desk Sheet", desk_sheet)
            self.assertIn("Tomorrow's deep read", desk_sheet)
            self.assertIn("Notes - 14", desk_sheet)
            feedback_plan = (edition_dir / "feedback-plan.md").read_text(encoding="utf-8")
            self.assertIn("Feedback Plan", feedback_plan)
            self.assertIn("operator-answers.md", feedback_plan)
            self.assertIn("EDITORIAL.md", feedback_plan)
            self.assertIn("VISUALS.md", feedback_plan)
            self.assertIn("SOURCES.md", feedback_plan)
            self.assertIn("DELIVERY.md", feedback_plan)
            self.assertIn("TASTELOG.md", feedback_plan)
            self.assertIn("Applied Feedback", feedback_plan)
            self.assertIn("Do not overfit", feedback_plan)
            self.assertIn("YAML targets", feedback_plan)
            self.assertEqual(payload["artifacts"]["feedback_plan"], str((edition_dir / "feedback-plan.md").resolve()))
            self.assertEqual(payload["artifacts"]["desk_sheet"], str((edition_dir / "desk-sheet.md").resolve()))
            self.assertEqual(payload["artifacts"]["final_editor"], str((edition_dir / "final-editor.json").resolve()))
            self.assertIn("final-editor", payload["next_action"])

    def test_edition_prepare_respects_disabled_desk_sheet_preference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            (newsroom / "preferences" / "desk-sheet.yaml").write_text(
                "enabled: false\ntemplate: no10\n",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                )

            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            edition_dir = newsroom / "editions" / "2026-06-22"
            self.assertFalse((edition_dir / "desk-sheet.md").exists())
            self.assertNotIn("desk-sheet.md", payload["written"])
            self.assertNotIn("desk_sheet", payload["artifacts"])

    def test_edition_prepare_applies_desk_sheet_knobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            (newsroom / "preferences" / "desk-sheet.yaml").write_text(
                "enabled: true\nnotes_lines: 11\nask_count: 2\ntomorrow_choices: 3\n",
                encoding="utf-8",
            )

            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                ),
                0,
            )

            desk_sheet = (newsroom / "editions" / "2026-06-22" / "desk-sheet.md").read_text(encoding="utf-8")
            self.assertIn("Notes - 11", desk_sheet)
            self.assertIn("Asks - 2", desk_sheet)
            self.assertIn("TMRW - 3", desk_sheet)
            self.assertIn("Q2", desk_sheet)
            self.assertNotIn("Q3", desk_sheet)
            self.assertIn("M3", desk_sheet)
            self.assertNotIn("M4", desk_sheet)

    def test_final_editor_passes_clean_rendered_reviewed_edition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                ),
                0,
            )
            edition_dir = newsroom / "editions" / "2026-06-22"
            rendered = edition_dir / "edition"
            rendered.mkdir()
            pdf = rendered / "edition.pdf"
            self._minimal_pdf(pdf)
            (rendered / "edition.md").write_text("# Done\n", encoding="utf-8")
            draft = edition_dir / "draft.md"
            estimate_file_mtime = draft.stat().st_mtime
            (edition_dir / "estimate-result.json").write_text(
                json.dumps(
                    {
                        "status": "estimated",
                        "date": "2026-06-22",
                        "file": str(draft.resolve()),
                        "file_mtime": estimate_file_mtime,
                        "est_pages": 1,
                        "words": 2,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (edition_dir / "render-result.json").write_text(
                json.dumps(
                    {
                        "status": "rendered",
                        "date": "2026-06-22",
                        "pages": 1,
                        "warnings": [],
                        "output_dir": str(rendered),
                        "outputs": {
                            "pdf": str(pdf),
                            "markdown": str(rendered / "edition.md"),
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (edition_dir / "review.json").write_text(
                json.dumps(
                    {
                        "status": "clean",
                        "edition": {
                            "artifacts": {
                                "markdown": str(rendered / "edition.md"),
                                "json": str(rendered / "edition.json"),
                            }
                        },
                        "summary": {"flag": 0, "nudge": 0, "info": 0},
                        "findings": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (edition_dir / "visual-qa.json").write_text(
                json.dumps(
                    {
                        "status": "clean",
                        "pdf": {
                            "path": str(pdf),
                            "ok": True,
                            "pages": 1,
                            "header_ok": True,
                            "size_bytes": pdf.stat().st_size,
                        },
                        "findings": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    [
                        "edition",
                        "final-editor",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "clean")
            self.assertEqual(payload["ship_rule"], "deliver")
            self.assertEqual(payload["summary"], {"flag": 0, "nudge": 0, "info": 0})
            self.assertTrue((edition_dir / "final-editor.json").is_file())
            self.assertTrue((edition_dir / "final-editor.md").is_file())
            self.assertIn(str((newsroom / "EDITORIAL.md").resolve()), payload["files_read"])
            self.assertIn("Ship rule: deliver", (edition_dir / "final-editor.md").read_text(encoding="utf-8"))

    def test_final_editor_flags_unproven_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                ),
                0,
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    [
                        "edition",
                        "final-editor",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "review")
            self.assertEqual(payload["ship_rule"], "revise or record an explicit rationale before delivery")
            checks = {item["check"] for item in payload["findings"]}
            self.assertIn("render-complete", checks)
            self.assertIn("review-complete", checks)
            self.assertIn("delivery-proof", checks)
            self.assertIn("estimate-complete", checks)
            self.assertIn("visual-qa", checks)

    def test_final_editor_flags_stale_estimate_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                ),
                0,
            )
            edition_dir = newsroom / "editions" / "2026-06-22"
            draft = edition_dir / "draft.md"
            (edition_dir / "estimate-result.json").write_text(
                json.dumps(
                    {
                        "status": "estimated",
                        "date": "2026-06-22",
                        "file": str(draft.resolve()),
                        "file_mtime": 0,
                        "est_pages": 1,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            draft.write_text("# Changed After Estimate\n\nNew copy.\n", encoding="utf-8")
            rendered = edition_dir / "edition"
            rendered.mkdir()
            pdf = rendered / "edition.pdf"
            self._minimal_pdf(pdf)
            rendered_md = rendered / "edition.md"
            rendered_md.write_text("# Rendered\n", encoding="utf-8")
            (edition_dir / "render-result.json").write_text(
                json.dumps(
                    {
                        "date": "2026-06-22",
                        "pages": 4,
                        "outputs": {"pdf": str(pdf), "markdown": str(rendered_md)},
                        "output_dir": str(rendered),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (edition_dir / "review.json").write_text(
                json.dumps(
                    {
                        "status": "clean",
                        "edition": {"artifacts": {"markdown": str(edition_dir / "other.md")}},
                        "summary": {"flag": 0, "nudge": 0, "info": 0},
                        "findings": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (edition_dir / "visual-qa.json").write_text(
                json.dumps({"status": "pending", "pdf": {"path": str(pdf)}, "findings": []}, indent=2),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    [
                        "edition",
                        "final-editor",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "review")
            checks = {item["check"] for item in payload["findings"]}
            self.assertIn("artifact-freshness", checks)
            self.assertIn("estimate-drift", checks)
            self.assertIn("visual-qa", checks)

    def test_edition_prepare_preserves_draft_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            args = [
                "edition",
                "prepare",
                str(newsroom),
                "--config",
                str(config_path),
                "--date",
                "2026-06-22",
            ]
            self.assertEqual(cli.main(args), 0)
            draft = newsroom / "editions" / "2026-06-22" / "draft.md"
            draft.write_text("# Edited Draft\n\nKeep this.\n", encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(args)
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertIn("draft.md", payload["skipped"])
            self.assertEqual(draft.read_text(encoding="utf-8"), "# Edited Draft\n\nKeep this.\n")

            self.assertEqual(cli.main([*args, "--force"]), 0)
            self.assertNotEqual(draft.read_text(encoding="utf-8"), "# Edited Draft\n\nKeep this.\n")

    def test_apply_feedback_routes_note_to_smallest_durable_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                ),
                0,
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    [
                        "edition",
                        "apply-feedback",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                        "--route",
                        "visuals",
                        "--note",
                        "Make wide charts full measure.",
                        "--why",
                        "reader disliked narrow floating visuals",
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "applied")
            self.assertEqual(payload["route"], "visuals")
            self.assertEqual(payload["decision"], "accepted")
            self.assertEqual(payload["target"], str((newsroom / "VISUALS.md").resolve()))
            self.assertIn(str((newsroom / "TASTELOG.md").resolve()), payload["paths_changed"])

            visuals = (newsroom / "VISUALS.md").read_text(encoding="utf-8")
            self.assertIn("## Feedback Notes", visuals)
            self.assertIn("Make wide charts full measure.", visuals)
            self.assertIn("reader disliked narrow floating visuals", visuals)
            tastelog = (newsroom / "TASTELOG.md").read_text(encoding="utf-8")
            self.assertIn("Make wide charts full measure.", tastelog)
            self.assertIn("VISUALS.md", tastelog)
            feedback_plan = (newsroom / "editions" / "2026-06-22" / "feedback-plan.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Applied Feedback", feedback_plan)
            self.assertNotIn("No feedback applied yet.", feedback_plan)
            self.assertIn("visuals", feedback_plan)
            self.assertIn("VISUALS.md", feedback_plan)

    def test_apply_feedback_can_target_voice_and_section_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                ),
                0,
            )

            voice_out = io.StringIO()
            with redirect_stdout(voice_out):
                rc = cli.main(
                    [
                        "edition",
                        "apply-feedback",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                        "--route",
                        "voice",
                        "--note",
                        "Use the dense operator register by default.",
                    ]
                )
            self.assertEqual(rc, 0)
            voice_payload = json.loads(voice_out.getvalue())
            self.assertEqual(voice_payload["target_relative"], "preferences/voice.md")
            voice = (newsroom / "preferences" / "voice.md").read_text(encoding="utf-8")
            self.assertIn("Use the dense operator register by default.", voice)

            spec_out = io.StringIO()
            with redirect_stdout(spec_out):
                rc = cli.main(
                    [
                        "edition",
                        "apply-feedback",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                        "--route",
                        "the-read",
                        "--note",
                        "The Read should connect work and personal sources before recommending action.",
                        "--why",
                        "reader wants synthesis, not a mirror",
                    ]
                )
            self.assertEqual(rc, 0)
            spec_payload = json.loads(spec_out.getvalue())
            self.assertEqual(spec_payload["target_relative"], "specs/the-read.md")
            the_read = (newsroom / "specs" / "the-read.md").read_text(encoding="utf-8")
            self.assertIn("connect work and personal sources", the_read)
            tastelog = (newsroom / "TASTELOG.md").read_text(encoding="utf-8")
            self.assertIn("preferences/voice.md", tastelog)
            self.assertIn("specs/the-read.md", tastelog)
            feedback_plan = (newsroom / "editions" / "2026-06-22" / "feedback-plan.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("voice", feedback_plan)
            self.assertIn("the-read", feedback_plan)
            self.assertIn("preferences/voice.md", feedback_plan)
            self.assertIn("specs/the-read.md", feedback_plan)

    def test_apply_feedback_keeps_yaml_targets_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                ),
                0,
            )

            for route, phrase in (
                ("prior", "Dampen pure viral velocity."),
                ("checks", "Mute headline-length nudges for the Field Notes section."),
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    rc = cli.main(
                        [
                            "edition",
                            "apply-feedback",
                            str(newsroom),
                            "--config",
                            str(config_path),
                            "--date",
                            "2026-06-22",
                            "--route",
                            route,
                            "--note",
                            phrase,
                        ]
                    )
                self.assertEqual(rc, 0)

            prior = newsroom / "preferences" / "algorithm-prior.yaml"
            checks = newsroom / "preferences" / "checks.yaml"
            self.assertIsNone(yaml.safe_load(prior.read_text(encoding="utf-8")))
            self.assertIsNone(yaml.safe_load(checks.read_text(encoding="utf-8")))
            self.assertIn("# Feedback Notes", prior.read_text(encoding="utf-8"))
            self.assertIn("# -", prior.read_text(encoding="utf-8"))
            self.assertIn("Dampen pure viral velocity.", prior.read_text(encoding="utf-8"))
            self.assertIn("# Feedback Notes", checks.read_text(encoding="utf-8"))
            self.assertIn("Mute headline-length nudges", checks.read_text(encoding="utf-8"))
            feedback_plan = (newsroom / "editions" / "2026-06-22" / "feedback-plan.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("preferences/algorithm-prior.yaml", feedback_plan)
            self.assertIn("preferences/checks.yaml", feedback_plan)

    def test_apply_feedback_examples_cover_every_durable_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "prepare",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-22",
                    ]
                ),
                0,
            )
            examples = [
                ("editorial", "More judgment, less roundup.", "EDITORIAL.md", "accepted"),
                ("sources", "GitHub/Main Branch pulses outrank casual reads when there are open asks.", "SOURCES.md", "accepted"),
                ("delivery", "Email the article view after the PDF lands.", "DELIVERY.md", "accepted"),
                ("front-page", "Front page headlines need a verb and a point of view.", "specs/front-page.md", "accepted"),
                ("reading", "Do not reprint reads I already got.", "specs/reading.md", "accepted"),
                ("taste", "Make the default edition forty pages.", "TASTELOG.md", "rejected"),
            ]
            for route, note, target, decision in examples:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    rc = cli.main(
                        [
                            "edition",
                            "apply-feedback",
                            str(newsroom),
                            "--config",
                            str(config_path),
                            "--date",
                            "2026-06-22",
                            "--route",
                            route,
                            "--decision",
                            decision,
                            "--note",
                            note,
                            "--why",
                            "feedback-loop eval",
                        ]
                    )
                self.assertEqual(rc, 0, route)
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["target_relative"], target)
                self.assertEqual(payload["decision"], decision)

            for target in (
                "EDITORIAL.md",
                "SOURCES.md",
                "DELIVERY.md",
                "specs/front-page.md",
                "specs/reading.md",
            ):
                text = (newsroom / target).read_text(encoding="utf-8")
                self.assertIn("## Feedback Notes", text, target)
                self.assertIn("feedback-loop eval", text, target)

            tastelog = (newsroom / "TASTELOG.md").read_text(encoding="utf-8")
            self.assertIn("More judgment, less roundup.", tastelog)
            self.assertIn("GitHub/Main Branch pulses", tastelog)
            self.assertIn("rejected - Make the default edition forty pages.", tastelog)
            self.assertNotIn("## Feedback Notes", tastelog)

            feedback_plan = (newsroom / "editions" / "2026-06-22" / "feedback-plan.md").read_text(
                encoding="utf-8"
            )
            for route, _note, target, decision in examples:
                self.assertIn(route, feedback_plan)
                self.assertIn(target, feedback_plan)
                self.assertIn(decision, feedback_plan)

    def test_apply_feedback_rejects_missing_route_or_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            newsroom = tmp_path / "newsroom"
            config_path = self._config_path(tmp_path)
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "apply-feedback",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--route",
                        "kitchen",
                        "--note",
                        "Too much soup.",
                    ]
                ),
                1,
            )
            self.assertEqual(
                cli.main(
                    [
                        "edition",
                        "apply-feedback",
                        str(newsroom),
                        "--config",
                        str(config_path),
                        "--route",
                        "editorial",
                    ]
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
