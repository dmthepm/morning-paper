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
                "draft.md",
                "render-result.json",
                "review.json",
                "operator-answers.md",
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
            render_result = json.loads((edition_dir / "render-result.json").read_text(encoding="utf-8"))
            self.assertEqual(render_result["status"], "pending")
            self.assertIn("morning-paper render", render_result["command"])
            review = json.loads((edition_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(review["status"], "pending")
            self.assertIn("morning-paper review", review["command"])
            operator_answers = (edition_dir / "operator-answers.md").read_text(encoding="utf-8")
            self.assertIn("Visuals", operator_answers)
            self.assertIn("Delivery", operator_answers)
            self.assertIn("Taste To Save", operator_answers)
            self.assertIn("VISUALS.md", operator_answers)
            self.assertIn("Print Tomorrow", operator_answers)
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
            self.assertEqual(payload["artifacts"]["feedback_plan"], str((edition_dir / "feedback-plan.md").resolve()))
            self.assertIn("feedback-plan.md", payload["next_action"])

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
