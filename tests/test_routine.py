from __future__ import annotations

import io
import json
import os
import plistlib
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from morning_paper import cli, routine


class FakeRun:
    """Records every scheduler subprocess call; no launchctl/systemctl/crontab in CI."""

    def __init__(self, fail_prefixes: tuple[tuple[str, ...], ...] = (), stdout_map=None):
        self.calls: list[list[str]] = []
        self.inputs: list[str | None] = []
        self.fail_prefixes = fail_prefixes
        self.stdout_map = stdout_map or {}

    def __call__(self, args: list[str], input_text: str | None = None):
        self.calls.append(list(args))
        self.inputs.append(input_text)
        returncode = 0
        for prefix in self.fail_prefixes:
            if tuple(args[: len(prefix)]) == prefix:
                returncode = 1
        stdout = ""
        for prefix, text in self.stdout_map.items():
            if tuple(args[: len(prefix)]) == prefix:
                stdout = text
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")


class RoutineHomeTestCase(unittest.TestCase):
    """Every test runs against a throwaway HOME so no real agent dirs are touched."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        patcher = patch.dict(os.environ, {"HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)


class LaunchdPlistTests(RoutineHomeTestCase):
    def test_default_plist_content(self) -> None:
        data = routine.build_launchd_plist()
        self.assertEqual(data["Label"], "com.morning-paper.edition")
        # The chosen semantics: StartCalendarInterval fires daily at 05:00
        # local time; launchd coalesces runs missed during sleep into one
        # run at the next wake. RunAtLoad stays False so install never
        # triggers an immediate edition.
        self.assertEqual(data["StartCalendarInterval"], {"Hour": 5, "Minute": 0})
        self.assertIs(data["RunAtLoad"], False)
        self.assertTrue(data["StandardOutPath"].endswith("morning-paper/routine.log"))
        self.assertEqual(data["StandardOutPath"], data["StandardErrorPath"])
        self.assertEqual(data["ProgramArguments"][:2], ["/bin/sh", "-c"])
        wrapped = data["ProgramArguments"][2]
        self.assertIn('claude -p "Run the morning-paper edition skill', wrapped)
        self.assertIn("--permission-mode acceptEdits", wrapped)
        self.assertIn(routine.RUN_START_PREFIX, wrapped)
        self.assertIn(routine.RUN_EXIT_PREFIX, wrapped)
        self.assertIn("PATH", data["EnvironmentVariables"])

    def test_custom_time_and_command(self) -> None:
        data = routine.build_launchd_plist("06:30", "echo hello")
        self.assertEqual(data["StartCalendarInterval"], {"Hour": 6, "Minute": 30})
        self.assertIn("echo hello; rc=$?;", data["ProgramArguments"][2])

    def test_plist_serializes(self) -> None:
        blob = plistlib.dumps(routine.build_launchd_plist())
        reread = plistlib.loads(blob)
        self.assertEqual(reread["Label"], "com.morning-paper.edition")

    def test_unwrap_roundtrip(self) -> None:
        for command in (routine.DEFAULT_COMMAND, "echo hi", "my-tool --flag 'x y'"):
            self.assertEqual(routine._unwrap_command(routine._wrap_command(command)), command)

    def test_invalid_time_rejected(self) -> None:
        for bad in ("25:00", "05:61", "5", "morning", "5:0"):
            with self.assertRaises(ValueError):
                routine.parse_time(bad)


class UnitGenerationTests(RoutineHomeTestCase):
    def test_systemd_timer_persistent(self) -> None:
        timer = routine.build_systemd_timer("05:00")
        self.assertIn("OnCalendar=*-*-* 05:00:00", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("WantedBy=timers.target", timer)

    def test_systemd_service_escapes_percent(self) -> None:
        service = routine.build_systemd_service("echo hi")
        self.assertIn("ExecStart=/bin/sh -c", service)
        self.assertIn("echo hi; rc=$?;", service)
        # the date format's % signs must be doubled for systemd
        self.assertIn("%%Y-%%m-%%d", service)
        self.assertNotIn("%Y-%m-%d", service.replace("%%", ""))
        self.assertIn(f"StandardOutput=append:{routine.log_path()}", service)

    def test_cron_line_escapes_and_notes_schedule(self) -> None:
        line = routine.build_cron_line("06:15", "echo hi")
        self.assertTrue(line.startswith("15 6 * * * /bin/sh -c '"))
        self.assertTrue(line.endswith(routine.CRON_MARKER))
        self.assertIn(r"\%Y", line)  # cron eats bare %
        self.assertIn("'\\''", line)  # single quotes inside the single-quoted command


class InstallDarwinTests(RoutineHomeTestCase):
    def _install(self, argv: list[str], fake: FakeRun):
        with patch.object(routine, "_run", fake), patch.object(
            routine, "_current_platform", return_value="darwin"
        ), patch.object(routine, "_resolve_claude", return_value="/usr/local/bin/claude"):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cli.main(argv)
        return rc, stdout.getvalue(), stderr.getvalue()

    def test_install_writes_plist_and_bootstraps(self) -> None:
        fake = FakeRun()
        rc, out, _ = self._install(["routine", "install"], fake)
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["installed"])
        self.assertTrue(payload["loaded"])
        self.assertEqual(payload["scheduler"], "launchd")
        self.assertEqual(payload["schedule"]["time"], "05:00")
        self.assertIn("coalesced", payload["schedule"]["semantics"])
        self.assertEqual(payload["command"], routine.DEFAULT_COMMAND)
        plist_file = self.home / "Library" / "LaunchAgents" / "com.morning-paper.edition.plist"
        self.assertTrue(plist_file.is_file())
        with plist_file.open("rb") as handle:
            data = plistlib.load(handle)
        self.assertEqual(data["StartCalendarInterval"], {"Hour": 5, "Minute": 0})
        bootstrap_calls = [c for c in fake.calls if c[:2] == ["launchctl", "bootstrap"]]
        self.assertEqual(len(bootstrap_calls), 1)
        self.assertTrue(bootstrap_calls[0][2].startswith("gui/"))

    def test_install_custom_time(self) -> None:
        fake = FakeRun()
        rc, out, _ = self._install(["routine", "install", "--time", "6:45"], fake)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["schedule"]["time"], "06:45")

    def test_install_falls_back_to_legacy_load(self) -> None:
        fake = FakeRun(fail_prefixes=(("launchctl", "bootstrap"),))
        rc, out, _ = self._install(["routine", "install"], fake)
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["loaded"])
        self.assertIn("legacy", payload["note"])
        self.assertIn(["launchctl", "load", str(routine.launchd_plist_path())], fake.calls)

    def test_install_bad_time_exits_2(self) -> None:
        fake = FakeRun()
        rc, _, err = self._install(["routine", "install", "--time", "25:99"], fake)
        self.assertEqual(rc, 2)
        self.assertIn("invalid --time", err)
        self.assertEqual(fake.calls, [])


class NoClaudeBinaryTests(RoutineHomeTestCase):
    def test_install_without_claude_warns_and_shows_command(self) -> None:
        fake = FakeRun()
        with patch.object(routine, "_run", fake), patch.object(
            routine, "_current_platform", return_value="darwin"
        ), patch.object(routine, "_resolve_claude", return_value=None):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cli.main(["routine", "install"])
        self.assertEqual(rc, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["installed"])
        self.assertIn("claude", payload["warning"])
        self.assertEqual(payload["command"], routine.DEFAULT_COMMAND)
        self.assertIn("`claude` binary not found", stderr.getvalue())
        self.assertIn(routine.DEFAULT_COMMAND, stderr.getvalue())
        self.assertFalse(routine.launchd_plist_path().exists())
        self.assertEqual(fake.calls, [])

    def test_explicit_command_skips_the_claude_check(self) -> None:
        fake = FakeRun()
        with patch.object(routine, "_run", fake), patch.object(
            routine, "_current_platform", return_value="darwin"
        ), patch.object(routine, "_resolve_claude", return_value=None):
            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                rc = cli.main(["routine", "install", "--command", "my-own-editor --go"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["installed"])
        self.assertEqual(payload["command"], "my-own-editor --go")


class InstallLinuxTests(RoutineHomeTestCase):
    def test_systemd_user_timer_path(self) -> None:
        fake = FakeRun()
        with patch.object(routine, "_run", fake), patch.object(
            routine, "_current_platform", return_value="linux"
        ), patch.object(routine, "_resolve_claude", return_value="/usr/bin/claude"), patch.object(
            routine, "_tool_exists", lambda name: name == "systemctl"
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                rc = cli.main(["routine", "install", "--time", "07:00"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["scheduler"], "systemd")
        timer = routine.systemd_timer_path().read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* 07:00:00", timer)
        self.assertIn("Persistent=true", timer)
        self.assertTrue(routine.systemd_service_path().is_file())
        self.assertIn(["systemctl", "--user", "daemon-reload"], fake.calls)
        self.assertIn(
            ["systemctl", "--user", "enable", "--now", "morning-paper-edition.timer"],
            fake.calls,
        )

    def test_cron_fallback_when_no_systemd(self) -> None:
        fake = FakeRun(stdout_map={("crontab", "-l"): "0 9 * * * existing-job\n"})
        with patch.object(routine, "_run", fake), patch.object(
            routine, "_current_platform", return_value="linux"
        ), patch.object(routine, "_resolve_claude", return_value="/usr/bin/claude"), patch.object(
            routine, "_tool_exists", lambda name: name == "crontab"
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                rc = cli.main(["routine", "install"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["scheduler"], "cron")
        self.assertIn("no missed-run coalescing", payload["note"])
        written = fake.inputs[-1]
        self.assertIn("0 9 * * * existing-job", written)
        self.assertIn(routine.CRON_MARKER, written)
        self.assertTrue(any("0 5 * * *" in line for line in written.splitlines()))


class StatusTests(RoutineHomeTestCase):
    LOG = (
        "[morning-paper routine] start 2026-06-11T05:00:01-0700\n"
        "some claude output\n"
        "[morning-paper routine] exit 1\n"
        "[morning-paper routine] start 2026-06-12T05:00:02-0700\n"
        "edition rendered\n"
        "[morning-paper routine] exit 0\n"
    )

    def test_parse_routine_log_takes_last_run(self) -> None:
        parsed = routine.parse_routine_log(self.LOG)
        self.assertEqual(parsed, {"started": "2026-06-12T05:00:02-0700", "exit_code": 0})

    def test_parse_routine_log_run_in_flight(self) -> None:
        text = self.LOG + "[morning-paper routine] start 2026-06-13T05:00:00-0700\n"
        parsed = routine.parse_routine_log(text)
        self.assertEqual(parsed["started"], "2026-06-13T05:00:00-0700")
        self.assertIsNone(parsed["exit_code"])

    def test_parse_routine_log_empty(self) -> None:
        self.assertIsNone(routine.parse_routine_log(""))
        self.assertIsNone(routine.parse_routine_log("unrelated noise\n"))

    def test_status_not_installed(self) -> None:
        with patch.object(routine, "_run", FakeRun()), patch.object(
            routine, "_tool_exists", lambda name: False
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["routine", "status"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["installed"])
        self.assertIsNone(payload["scheduler"])
        self.assertIn("routine install", payload["hint"])

    def test_status_installed_launchd(self) -> None:
        # install (mocked), then write a log and ask for status
        install_fake = FakeRun()
        with patch.object(routine, "_run", install_fake), patch.object(
            routine, "_current_platform", return_value="darwin"
        ), patch.object(routine, "_resolve_claude", return_value="/usr/local/bin/claude"):
            with redirect_stdout(io.StringIO()):
                cli.main(["routine", "install", "--time", "05:30"])
        routine.log_path().parent.mkdir(parents=True, exist_ok=True)
        routine.log_path().write_text(self.LOG, encoding="utf-8")
        status_fake = FakeRun(
            stdout_map={
                ("launchctl", "print"): (
                    "gui/501/com.morning-paper.edition = {\n"
                    "\tstate = waiting\n"
                    "\tlast exit code = 0\n"
                    "}\n"
                )
            }
        )
        with patch.object(routine, "_run", status_fake), patch.object(
            routine, "_tool_exists", lambda name: name == "launchctl"
        ):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["routine", "status"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["installed"])
        self.assertEqual(payload["scheduler"], "launchd")
        self.assertEqual(payload["schedule"]["time"], "05:30")
        self.assertEqual(payload["command"], routine.DEFAULT_COMMAND)
        self.assertEqual(payload["last_run"]["started"], "2026-06-12T05:00:02-0700")
        self.assertEqual(payload["last_run"]["exit_code"], 0)
        self.assertEqual(payload["launchd"]["state"], "waiting")
        self.assertTrue(payload["next_fire"].count("05:30") == 1)
        self.assertEqual(payload["log"], str(routine.log_path()))

    def test_next_fire_rolls_to_tomorrow(self) -> None:
        from datetime import datetime, timezone

        now = datetime(2026, 6, 12, 9, 0, tzinfo=timezone.utc)
        self.assertEqual(routine.next_fire("05:00", now=now), "2026-06-13T05:00+00:00")
        self.assertEqual(routine.next_fire("10:00", now=now), "2026-06-12T10:00+00:00")


class UninstallTests(RoutineHomeTestCase):
    def test_uninstall_is_idempotent(self) -> None:
        fake = FakeRun()
        with patch.object(routine, "_run", fake), patch.object(
            routine, "_current_platform", return_value="darwin"
        ), patch.object(routine, "_resolve_claude", return_value="/usr/local/bin/claude"), patch.object(
            routine, "_tool_exists", lambda name: name == "launchctl"
        ):
            with redirect_stdout(io.StringIO()):
                cli.main(["routine", "install"])
            self.assertTrue(routine.launchd_plist_path().is_file())

            first, second = io.StringIO(), io.StringIO()
            with redirect_stdout(first):
                rc1 = cli.main(["routine", "uninstall"])
            with redirect_stdout(second):
                rc2 = cli.main(["routine", "uninstall"])
        self.assertEqual((rc1, rc2), (0, 0))
        payload1 = json.loads(first.getvalue())
        self.assertTrue(payload1["uninstalled"])
        self.assertEqual(payload1["scheduler"], "launchd")
        self.assertFalse(routine.launchd_plist_path().exists())
        payload2 = json.loads(second.getvalue())
        self.assertFalse(payload2["uninstalled"])
        self.assertFalse(payload2["installed"])
        bootout_calls = [c for c in fake.calls if c[:2] == ["launchctl", "bootout"]]
        self.assertTrue(bootout_calls)

    def test_uninstall_systemd_removes_units(self) -> None:
        fake = FakeRun()
        with patch.object(routine, "_run", fake), patch.object(
            routine, "_current_platform", return_value="linux"
        ), patch.object(routine, "_resolve_claude", return_value="/usr/bin/claude"), patch.object(
            routine, "_tool_exists", lambda name: name == "systemctl"
        ):
            with redirect_stdout(io.StringIO()):
                cli.main(["routine", "install"])
                rc = cli.main(["routine", "uninstall"])
        self.assertEqual(rc, 0)
        self.assertFalse(routine.systemd_timer_path().exists())
        self.assertFalse(routine.systemd_service_path().exists())
        self.assertIn(
            ["systemctl", "--user", "disable", "--now", "morning-paper-edition.timer"],
            fake.calls,
        )


class DoctorRoutineTests(RoutineHomeTestCase):
    def test_doctor_json_reports_routine_absent_without_error(self) -> None:
        with patch.object(routine, "_tool_exists", lambda name: False):
            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                with patch.object(cli, "_print_update_notice"):
                    rc = cli.main(["doctor", "--json"])
        payload = json.loads(stdout.getvalue())
        self.assertIn("routine", payload)
        self.assertFalse(payload["routine"]["installed"])
        self.assertIsNone(payload["routine"]["scheduler"])
        # absence must not break doctor: status reflects renderer/modules only
        self.assertIn(payload["status"], {"ok", "fallback-only", "broken"})
        self.assertIn(rc, {0, 1})

    def test_doctor_json_reports_routine_installed(self) -> None:
        with patch.object(routine, "_run", FakeRun()), patch.object(
            routine, "_current_platform", return_value="darwin"
        ), patch.object(routine, "_resolve_claude", return_value="/usr/local/bin/claude"):
            with redirect_stdout(io.StringIO()):
                cli.main(["routine", "install", "--time", "06:00"])
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            with patch.object(cli, "_print_update_notice"):
                cli.main(["doctor", "--json"])
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["routine"]["installed"])
        self.assertEqual(payload["routine"]["scheduler"], "launchd")
        self.assertEqual(payload["routine"]["time"], "06:00")

    def test_doctor_human_output_mentions_routine(self) -> None:
        with patch.object(routine, "_tool_exists", lambda name: False):
            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                with patch.object(cli, "_print_update_notice"):
                    cli.main(["doctor"])
        self.assertIn("routine: not installed", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
