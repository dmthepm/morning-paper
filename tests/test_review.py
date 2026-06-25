"""The `review` verb — editorial QC on a finished edition (0.6.0, scoped 0.6.1).

Phase 0 (the verb + report model + registry runner) and Phase 1 (deterministic
text/art-desk checks + checks.yaml reading). The checker never fails: exit 0 by
default; --strict makes a flag (and only a flag) exit 1.

0.6.1 scopes the two LENGTH checks (line-count, length) to TRUE headlines:
deck/department titles (.dept-title) are long by design and are exempt.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from morning_paper import cli
from morning_paper.reviewers import (
    REGISTRY,
    Preferences,
    load_preferences,
    parse_edition,
    render_human,
    resolve_artifacts,
    run_review,
)


def _write_edition(
    body: str,
    *,
    items: list[dict] | None = None,
    edition_date: str | None = None,
    style: str = "broadsheet",
    palette: str = "color",
) -> Path:
    """Write a composed edition (markdown + optional JSON) into a temp dir."""
    tmp = Path(tempfile.mkdtemp())
    (tmp / "edition.md").write_text(body, encoding="utf-8")
    if items is not None or edition_date is not None:
        payload = {
            "date": edition_date,
            "metadata": {"style": style, "palette": palette},
            "items": {"rss": items or []},
        }
        (tmp / "edition.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp


def _review(body: str, **kw) -> dict:
    return run_review(_write_edition(body, **kw) / "edition.md")


# A balanced, well-formed broadsheet edition that should review CLEAN.
_CLEAN_EDITION = (
    "## Featured Reads\n\n"
    '<div class="article-head"><div class="dept-title">Harbor board approves the new ferry schedule</div></div>\n\n'
    "The board voted to add a morning crossing after a long debate about the cost.\n\n"
    '<div class="article-head"><div class="dept-title">Bakery wins a regional prize for its rye</div></div>\n\n'
    "The judges praised the crust and the crumb in equal measure this spring season.\n\n"
    "## Community Signals\n\n"
    '<div class="article-head"><div class="dept-title">A new compiler ships its first release</div></div>\n\n'
    "The team announced the milestone after three years of steady work on the project.\n\n"
    '<div class="article-head"><div class="dept-title">Engineers debate a faster sort method</div></div>\n\n'
    "The thread drew careful benchmarks from several working programmers this week.\n"
)


class ReportModelTest(unittest.TestCase):
    def test_clean_edition_has_clean_status_and_no_findings(self) -> None:
        report = _review(
            _CLEAN_EDITION,
            items=[{"title": "Harbor board approves schedule", "url": "http://x/1", "score": 5, "published_at": "2026-06-21"}],
            edition_date="2026-06-21",
        )
        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["findings"], [])

    def test_envelope_shape_matches_spec(self) -> None:
        report = _review(_CLEAN_EDITION)
        for key in ("edition", "checks_run", "checks_skipped", "findings", "summary", "status"):
            self.assertIn(key, report)
        for sev in ("info", "nudge", "flag"):
            self.assertIn(sev, report["summary"])
        self.assertIn("sections_reviewed", report["summary"])

    def test_checks_skipped_is_honest_when_no_json(self) -> None:
        # no JSON artifact → stale-dateline cannot run and SAYS so
        report = _review(_CLEAN_EDITION)
        skipped = {c["check"] for c in report["checks_skipped"]}
        self.assertIn("stale-dateline", skipped)

    def test_resolve_artifacts_prefers_render_result_outputs(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        ed = tmp / "2026-06-22"
        rendered = ed / "edition"
        rendered.mkdir(parents=True)
        (ed / "collector-report.md").write_text("# Collector Report\n", encoding="utf-8")
        (ed / "queue-snapshot.json").write_text("{}", encoding="utf-8")
        (rendered / "edition.md").write_text(_CLEAN_EDITION, encoding="utf-8")
        (rendered / "edition.json").write_text(
            json.dumps({"date": "2026-06-22", "metadata": {"style": "broadsheet", "palette": "color"}}),
            encoding="utf-8",
        )
        (ed / "render-result.json").write_text(
            json.dumps(
                {
                    "outputs": {
                        "markdown": str(rendered / "edition.md"),
                        "json": str(rendered / "edition.json"),
                    }
                }
            ),
            encoding="utf-8",
        )

        artifacts = resolve_artifacts(ed)

        self.assertEqual(artifacts["markdown"], rendered / "edition.md")
        self.assertEqual(artifacts["json"], rendered / "edition.json")

    def test_resolve_artifacts_ignores_prepared_workspace_metadata(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        ed = tmp / "2026-06-22"
        rendered = ed / "edition"
        rendered.mkdir(parents=True)
        (ed / "collector-report.md").write_text("# Collector Report\n", encoding="utf-8")
        (ed / "operator-answers.md").write_text("# Operator Answers\n", encoding="utf-8")
        (ed / "queue-snapshot.json").write_text("{}", encoding="utf-8")
        (rendered / "edition.md").write_text(_CLEAN_EDITION, encoding="utf-8")
        (rendered / "edition.json").write_text(
            json.dumps({"date": "2026-06-22", "metadata": {"style": "broadsheet", "palette": "color"}}),
            encoding="utf-8",
        )

        report = run_review(ed)

        self.assertEqual(report["edition"]["artifacts"]["markdown"], str(rendered / "edition.md"))
        self.assertEqual(report["edition"]["artifacts"]["json"], str(rendered / "edition.json"))
        self.assertEqual(report["status"], "clean")

    def test_registry_runs_every_text_check_when_artifacts_present(self) -> None:
        report = _review(
            _CLEAN_EDITION,
            items=[{"title": "x", "url": "http://x/1", "score": 1, "published_at": "2026-06-21"}],
            edition_date="2026-06-21",
        )
        ran = set(report["checks_run"])
        self.assertEqual(ran, {c.id for c in REGISTRY})

    def test_finding_object_carries_location_issue_why(self) -> None:
        report = _review(
            '<div class="mg-kicker">News</div>\n'
            '<div class="mg-title">The Quiet Collapse Of The Municipal Bond Market That Almost '
            "Nobody In The State Capital Will Discuss Openly Today Right Now</div>\n\n"
            "Real body prose so the section has content for the reviewer to read here today.\n"
        )
        flags = [f for f in report["findings"] if f["check"] == "headline-line-count"]
        self.assertTrue(flags)
        f = flags[0]
        for key in ("check", "severity", "location", "issue", "why", "measured", "threshold", "source"):
            self.assertIn(key, f)
        self.assertEqual(f["location"]["kind"], "headline")


class DeterministicChecksTest(unittest.TestCase):
    """Each check fires on a crafted bad input and is silent on clean input."""

    def _checks(self, report: dict, check_id: str) -> list[dict]:
        return [f for f in report["findings"] if f["check"] == check_id]

    def test_1_headline_line_count_flags_a_long_head(self) -> None:
        bad = _review(
            '<div class="mg-title">The Quiet Collapse Of The Municipal Bond Market That Almost '
            "Nobody In The State Capital Will Discuss Openly Today Right Now This Morning</div>\n\n"
            "Real body prose so the section has content to review here today for the desk.\n"
        )
        found = self._checks(bad, "headline-line-count")
        self.assertTrue(found)
        self.assertEqual(found[0]["severity"], "flag")
        self.assertGreaterEqual(found[0]["measured"]["lines"], 3)
        self.assertFalse(self._checks(_review(_CLEAN_EDITION), "headline-line-count"))

    def test_2_headline_length_nudges_over_ceiling(self) -> None:
        bad = _review(
            '<div class="mg-title">Council weighs a fairly modest new plan for the harbor lamps this evening</div>\n\n'
            "Real body prose for content so the section reads as real to the reviewer here.\n"
        )
        found = self._checks(bad, "headline-length")
        self.assertTrue(found)
        self.assertEqual(found[0]["severity"], "nudge")

    def test_long_dept_title_deck_does_not_flag_length_or_line_count(self) -> None:
        # the 0.6.0 false positive: a department/deck title is long BY DESIGN
        # (a multi-sentence summary). It must NOT trip the two LENGTH checks.
        long_deck = (
            "Devon's two same-day Monologue notes plus fourteen newsroom commits "
            "make the lead write itself this morning, and the gap, the connection, "
            "the drift, and the move are all present and mutually reinforcing today."
        )
        report = _review(
            '<div class="dept-kicker">The Read</div>\n'
            f'<div class="dept-title">{long_deck}</div>\n\n'
            "Real body prose so the section reads as genuine content for the desk here today.\n"
        )
        self.assertFalse(self._checks(report, "headline-line-count"))
        self.assertFalse(self._checks(report, "headline-length"))

    def test_real_headline_over_the_line_limit_still_flags(self) -> None:
        # a TRUE headline (.mg-title) that genuinely runs long is exactly what
        # the check should still catch — the scope fix must not blind it.
        report = _review(
            '<div class="mg-kicker">Harborfront</div>\n'
            '<div class="mg-title">The Quiet Collapse Of The Municipal Bond Market That Almost '
            "Nobody In The State Capital Will Discuss Openly Today Right Now This Very Morning</div>\n\n"
            "Real body prose so the section reads as genuine content for the desk here today.\n"
        )
        line_count = self._checks(report, "headline-line-count")
        length = self._checks(report, "headline-length")
        self.assertTrue(line_count)
        self.assertEqual(line_count[0]["severity"], "flag")
        self.assertGreaterEqual(line_count[0]["measured"]["lines"], 3)
        self.assertTrue(length)
        self.assertEqual(length[0]["severity"], "nudge")

    def test_3_headline_verb_presence_flags_a_label_head(self) -> None:
        bad = _review(
            '<div class="dept-title">The Third Quarter Municipal Numbers</div>\n\n'
            "Real body prose so the section is not empty and reads as genuine content here.\n"
        )
        found = self._checks(bad, "headline-verb-presence")
        self.assertTrue(found)
        self.assertEqual(found[0]["severity"], "flag")
        # a head with a verb is silent
        self.assertFalse(self._checks(_review(_CLEAN_EDITION), "headline-verb-presence"))

    def test_4_hed_dek_redundancy_nudges_an_echoing_deck(self) -> None:
        bad = _review(
            '<div class="dept-title">Lighthouse keeper wants a quieter lamp</div>\n'
            '<div class="mg-dek">The lighthouse keeper wants a much quieter lamp tonight</div>\n\n'
            "Real body prose so the section has content for review here today this morning.\n"
        )
        found = self._checks(bad, "hed-dek-redundancy")
        self.assertTrue(found)
        self.assertGreaterEqual(found[0]["measured"]["overlap_ratio"], 0.5)

    def test_5_section_balance_nudges_a_dwarfing_section(self) -> None:
        fat = "\n".join(
            f'<div class="article-head"><div class="dept-title">Story number {n} runs late today</div></div>\n\n'
            f"Real body text for story {n} so the section is full of items and words for sure.\n"
            for n in range(12)
        )
        bad = _review(
            "## Featured Reads\n\n" + fat
            + "\n## Community Signals\n\nOne lonely item lives here all alone today.\n"
            + "\n## Signals\n\nA single short signal item sits here today.\n"
            + "\n## Notes\n\nJust one short note in this section here today.\n"
        )
        found = self._checks(bad, "section-balance")
        self.assertTrue(found)
        self.assertEqual(found[0]["location"]["section"], "Featured Reads")

    def test_6_empty_or_sparse_section_nudges_dead_air(self) -> None:
        bad = _review(
            "## Featured Reads\n\nGood real body content with several words to read here today this morning.\n\n"
            '## Community Signals\n\n<p class="not-configured">No community signals configured.</p>\n'
        )
        found = self._checks(bad, "empty-or-sparse-section")
        self.assertTrue(found)
        self.assertEqual(found[0]["location"]["section"], "Community Signals")

    def test_7_duplicate_headline_nudges_same_url(self) -> None:
        items = [
            {"title": "Big news today", "url": "http://x.com/a", "score": 5, "published_at": "2026-06-21"},
            {"title": "Big news today", "url": "http://x.com/a", "score": 3, "published_at": "2026-06-21"},
        ]
        bad = _review(
            "## Reads\n\nSome real prose content here for the section to read today this morning.\n",
            items=items,
            edition_date="2026-06-21",
        )
        found = self._checks(bad, "duplicate-headline")
        self.assertTrue(found)

    def test_8_stale_dateline_is_info_for_an_old_lead(self) -> None:
        items = [{"title": "Old lead story", "url": "http://x/old", "score": 9, "published_at": "2026-06-08"}]
        bad = _review(
            "## Reads\n\nSome real prose content here for the section to read today this morning.\n",
            items=items,
            edition_date="2026-06-21",
        )
        found = self._checks(bad, "stale-dateline")
        self.assertTrue(found)
        self.assertEqual(found[0]["severity"], "info")

    def test_fresh_lead_does_not_trip_stale_dateline(self) -> None:
        items = [{"title": "Fresh lead", "url": "http://x/new", "score": 9, "published_at": "2026-06-20"}]
        report = _review(
            "## Reads\n\nSome real prose content here for the section to read today this morning.\n",
            items=items,
            edition_date="2026-06-21",
        )
        self.assertFalse(self._checks(report, "stale-dateline"))

    def test_9_visual_provenance_allows_captioned_sourced_figure(self) -> None:
        report = _review(
            "## Visual Desk\n\n"
            '<figure class="mp-figure">\n'
            '  <img src="images/chart.png" alt="Harbor seal count over 14 days">\n'
            "  <figcaption>Harbor seals counted at the breakwater.</figcaption>\n"
            '  <span class="mp-source-note">Source: reader collector, 2026-06-22.</span>\n'
            "</figure>\n\n"
            "A short note explains why this visual earns its ink today.\n"
        )
        self.assertFalse(self._checks(report, "visual-provenance"))

    def test_10_visual_provenance_nudges_unfurnished_or_narrow_visuals(self) -> None:
        report = _review(
            "## Visual Desk\n\n"
            '<figure class="mp-figure" style="width: 42%">\n'
            '  <img src="images/chart.png" alt="Harbor seal count over 14 days">\n'
            "</figure>\n\n"
            "![loose diagram](images/loose.png)\n\n"
            "A short note explains why these visuals need the art desk.\n"
        )
        found = self._checks(report, "visual-provenance")
        self.assertGreaterEqual(len(found), 3)
        issues = "\n".join(f["issue"] for f in found)
        self.assertIn("caption", issues)
        self.assertIn("source/synthetic note", issues)
        self.assertIn("narrow width", issues)
        self.assertIn("Markdown image", issues)

    def test_11_visual_density_nudges_long_text_only_editions(self) -> None:
        report = _review(
            "## Reading\n\n" + ("This is a long text-only edition with no chart or figure. " * 420)
        )
        found = self._checks(report, "visual-density")
        self.assertTrue(found)
        self.assertIn("no major visual", found[0]["issue"])

    def test_12_deck_source_url_nudges_raw_long_urls(self) -> None:
        report = _review(
            '<div class="article-head"><div class="mg-title">A read earns the page today</div>'
            '<div class="mg-dek">1804 words. Published today. Source: '
            'https://every.to/context-window/can-ai-learn-good-judgment</div></div>\n\n'
            "Real body prose so this article has something useful to review today.\n"
        )
        found = self._checks(report, "deck-source-url")
        self.assertTrue(found)
        self.assertIn("raw URL", found[0]["issue"])

    def test_13_stacked_subheads_nudge_imported_heading_ladders(self) -> None:
        report = _review(
            "## Reading\n\n"
            "### Inside Every\n\n"
            "### Dan is cloning Kate, but not in a weird way\n\n"
            "Real body prose follows the imported heading ladder today.\n"
        )
        found = self._checks(report, "stacked-subheads")
        self.assertTrue(found)

    def test_14_unsupported_glyphs_flag_emoji_before_tofu(self) -> None:
        report = _review(
            "## Reading\n\n"
            "🎙️ How I AI should be rewritten without emoji before print.\n"
        )
        found = self._checks(report, "unsupported-glyphs")
        self.assertTrue(found)
        self.assertEqual(found[0]["severity"], "flag")


class PreferencesTest(unittest.TestCase):
    def test_threshold_override_changes_the_number_and_provenance(self) -> None:
        prefs = Preferences(thresholds={"headline-line-count": {"warn_at_lines": 2}})
        # a 2-line head now flags where the default 3 would not
        ed = _write_edition(
            '<div class="mg-title">Council weighs a modest plan for the harbor lamps tonight at long last</div>\n\n'
            "Real body prose so the section has content for review here today this morning.\n"
        )
        report = run_review(ed / "edition.md", prefs=prefs)
        found = [f for f in report["findings"] if f["check"] == "headline-line-count"]
        self.assertTrue(found)
        self.assertEqual(found[0]["threshold"]["warn_at_lines"], 2)
        self.assertEqual(found[0]["threshold"]["source"], "user")

    def test_per_pack_threshold_resolves(self) -> None:
        prefs = Preferences(thresholds={"headline-line-count": {"warn_at_lines": 3, "per_pack": {"zine": 2}}})
        value, source = prefs.threshold("headline-line-count", "warn_at_lines", 3, pack="zine")
        self.assertEqual(value, 2)
        self.assertEqual(source, "user")
        value, source = prefs.threshold("headline-line-count", "warn_at_lines", 3, pack="broadsheet")
        self.assertEqual(value, 3)
        self.assertEqual(source, "user")

    def test_mute_suppresses_a_check_scoped_to_a_section(self) -> None:
        prefs = Preferences(
            mutes=[{"check": "headline-length", "when": {"section": "Field Notes"}}]
        )
        ed = _write_edition(
            '<div class="mg-kicker">Field Notes</div>\n'
            '<div class="mg-title">Council weighs a fairly modest new plan for the harbor lamps this evening</div>\n\n'
            "Real body prose so the section has content for review here today this morning.\n"
        )
        report = run_review(ed / "edition.md", prefs=prefs)
        self.assertFalse([f for f in report["findings"] if f["check"] == "headline-length"])

    def test_global_mute_suppresses_everywhere(self) -> None:
        prefs = Preferences(mutes=[{"check": "stale-dateline", "scope": "global"}])
        report = run_review(
            _write_edition(
                "## Reads\n\nReal prose content for the section to read today this morning here.\n",
                items=[{"title": "Old", "url": "http://x/o", "score": 9, "published_at": "2026-06-01"}],
                edition_date="2026-06-21",
            )
            / "edition.md",
            prefs=prefs,
        )
        self.assertFalse([f for f in report["findings"] if f["check"] == "stale-dateline"])

    def test_load_preferences_reads_checks_yaml_from_tree(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        ed = tmp / "out" / "2026-06-21"
        ed.mkdir(parents=True)
        (ed / "edition.md").write_text("## Reads\n\nbody\n", encoding="utf-8")
        prefs_dir = tmp / "out" / "preferences"
        prefs_dir.mkdir(parents=True)
        (prefs_dir / "checks.yaml").write_text(
            "version: 1\nthresholds:\n  headline-length:\n    nudge_at: 40\n", encoding="utf-8"
        )
        prefs = load_preferences(ed)
        value, source = prefs.threshold("headline-length", "nudge_at", 60)
        self.assertEqual(value, 40)
        self.assertEqual(source, "user")

    def test_missing_checks_yaml_yields_empty_preferences(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        prefs = load_preferences(tmp)
        value, source = prefs.threshold("headline-length", "nudge_at", 60)
        self.assertEqual(value, 60)
        self.assertEqual(source, "default")


class DeterminismTest(unittest.TestCase):
    def test_same_edition_same_prefs_is_byte_identical(self) -> None:
        ed = _write_edition(
            _CLEAN_EDITION,
            items=[{"title": "x", "url": "http://x/1", "score": 1, "published_at": "2026-06-21"}],
            edition_date="2026-06-21",
        )
        a = json.dumps(run_review(ed / "edition.md"), indent=2)
        b = json.dumps(run_review(ed / "edition.md"), indent=2)
        self.assertEqual(a, b)


class CliReviewTest(unittest.TestCase):
    def _build_edition_config(self) -> tuple[Path, Path]:
        tmp = Path(tempfile.mkdtemp())
        ed = tmp / "out" / "2026-06-21"
        ed.mkdir(parents=True)
        (ed / "edition.md").write_text(
            '<div class="dept-kicker">News</div>\n'
            '<div class="mg-title">The Quiet Collapse Of The Municipal Bond Market That Almost '
            "Nobody In The State Capital Will Discuss Openly Today Right Now This Morning</div>\n\n"
            "Real body prose so the section has content for the reviewer to read here today.\n",
            encoding="utf-8",
        )
        cfg = tmp / "config.yaml"
        cfg.write_text(f"name: Test\noutputs:\n  directory: {tmp / 'out'}\n", encoding="utf-8")
        return ed, cfg

    def _run(self, args: list[str]) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = cli.main(args)
        return rc, out.getvalue()

    def test_review_exits_zero_by_default_even_with_a_flag(self) -> None:
        _ed, cfg = self._build_edition_config()
        rc, out = self._run(["review", "--config", str(cfg), "--json"])
        self.assertEqual(rc, 0)
        report = json.loads(out)
        self.assertEqual(report["status"], "review")
        self.assertGreaterEqual(report["summary"]["flag"], 1)

    def test_strict_exits_one_on_a_flag(self) -> None:
        _ed, cfg = self._build_edition_config()
        rc, _out = self._run(["review", "--config", str(cfg), "--strict", "--json"])
        self.assertEqual(rc, 1)

    def test_strict_exits_zero_when_clean(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        ed = tmp / "out" / "2026-06-21"
        ed.mkdir(parents=True)
        (ed / "edition.md").write_text(_CLEAN_EDITION, encoding="utf-8")
        cfg = tmp / "config.yaml"
        cfg.write_text(f"name: Test\noutputs:\n  directory: {tmp / 'out'}\n", encoding="utf-8")
        rc, out = self._run(["review", str(ed), "--config", str(cfg), "--strict"])
        self.assertEqual(rc, 0)
        self.assertIn("clean", out)

    def test_review_default_resolves_latest_edition(self) -> None:
        _ed, cfg = self._build_edition_config()
        rc, out = self._run(["review", "--config", str(cfg)])
        self.assertEqual(rc, 0)
        self.assertIn("FLAG", out)

    def test_explain_shows_threshold_and_provenance(self) -> None:
        _ed, cfg = self._build_edition_config()
        rc, out = self._run(["review", "--config", str(cfg), "--explain", "headline-line-count"])
        self.assertEqual(rc, 0)
        self.assertIn("headline-line-count", out)
        self.assertIn("source", out)

    def test_help_is_zero(self) -> None:
        rc, out = self._run(["review", "--help"])
        self.assertEqual(rc, 0)
        self.assertIn("review", out)

    def test_missing_edition_is_a_clean_error(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        cfg = tmp / "config.yaml"
        cfg.write_text(f"name: Test\noutputs:\n  directory: {tmp / 'empty'}\n", encoding="utf-8")
        out = io.StringIO()
        from contextlib import redirect_stderr

        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = cli.main(["review", "--config", str(cfg)])
        self.assertEqual(rc, 1)
        self.assertIn("no edition", err.getvalue())


class HumanRendererTest(unittest.TestCase):
    def test_clean_render_is_one_quiet_line(self) -> None:
        report = _review(_CLEAN_EDITION)
        text = render_human(report)
        self.assertIn("clean", text)

    def test_flag_render_groups_and_teaches(self) -> None:
        report = _review(
            '<div class="dept-title">The Third Quarter Municipal Numbers</div>\n\n'
            "Real body prose so the section is not empty and reads as genuine content here today.\n"
        )
        text = render_human(report)
        self.assertIn("FLAG", text)
        self.assertIn("→", text)  # the teaching 'why' line


if __name__ == "__main__":
    unittest.main()
