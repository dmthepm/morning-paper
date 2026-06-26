"""The morning routine: schedule the daily edition without opening a chat.

The editor is an agent, so the scheduled job is just `claude -p` run headless
against the user's existing subscription — no extra API key, no daemon of ours.
This module owns the scheduling ladder's Tier 1/2 rung: a per-user job on the
platform's native scheduler.

Platform mapping:

- darwin  -> launchd (a LaunchAgent plist with ``StartCalendarInterval``).
  Chosen deliberately over cron: launchd *coalesces missed runs* — if the Mac
  was asleep at the scheduled minute, the job fires once on the next wake
  instead of being skipped. That is the product promise ("the paper is ready
  when you open the laptop") without fighting anyone's sleep schedule.
- linux   -> systemd user timer with ``Persistent=true`` (the systemd
  equivalent of coalescing: a missed run is made up at the next opportunity).
  Falls back to a crontab line when systemd is unavailable — with the honest
  note that cron has no coalescing: a run missed during sleep is simply gone.

Everything prints JSON; ``routine status`` parses the run-marker lines this
module wraps around the command, so "did my paper actually build this
morning?" has a machine-readable answer.
"""

from __future__ import annotations

import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


LAUNCHD_LABEL = "com.morning-paper.edition"
SYSTEMD_UNIT = "morning-paper-edition"
CRON_MARKER = "# morning-paper routine"
DEFAULT_TIME = "05:00"

# The default job: run the edition skill headless through the user's own
# Claude subscription. Documented as overridable via `--command` — any shell
# command works; this is just the one that turns the plugin into a newspaper
# delivery service.
DEFAULT_COMMAND = (
    'claude -p "Run the morning-paper edition skill: compose, render, and '
    "deliver today's edition per my newsroom configuration.\" "
    "--permission-mode acceptEdits"
)

# Run markers written around every scheduled invocation so `routine status`
# can report the last run honestly from the log alone.
RUN_START_PREFIX = "[morning-paper routine] start "
RUN_EXIT_PREFIX = "[morning-paper routine] exit "


# --- small seams, kept patchable for tests (no real launchctl/systemctl/crontab in CI) ---


def _current_platform() -> str:
    return sys.platform


def _resolve_claude() -> str | None:
    return shutil.which("claude")


def _tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _run(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, input=input_text, capture_output=True, text=True, timeout=30, check=False
    )


# --- paths ---


def log_path() -> Path:
    # Stated path, independent of config: the log must be findable even when
    # config.yaml is missing or broken (that is exactly when you read a log).
    return Path.home() / ".local" / "share" / "morning-paper" / "routine.log"


def launchd_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"


def systemd_unit_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def systemd_service_path() -> Path:
    return systemd_unit_dir() / f"{SYSTEMD_UNIT}.service"


def systemd_timer_path() -> Path:
    return systemd_unit_dir() / f"{SYSTEMD_UNIT}.timer"


# --- schedule + command plumbing ---


def parse_time(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", value.strip())
    if not match:
        raise ValueError(f"invalid --time {value!r}: expected HH:MM (24h), e.g. 05:00")
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        raise ValueError(f"invalid --time {value!r}: hour 00-23, minute 00-59")
    return hour, minute


def _wrap_command(command: str) -> str:
    """Bracket the job with timestamped run markers for `routine status`."""
    return (
        f"echo \"{RUN_START_PREFIX}$(date '+%Y-%m-%dT%H:%M:%S%z')\"; "
        f"{command}; rc=$?; "
        f'echo "{RUN_EXIT_PREFIX}$rc"; exit $rc'
    )


def _unwrap_command(wrapped: str) -> str | None:
    """Recover the raw command from a wrapper this module generated."""
    match = re.search(r"\)\"; (.*); rc=\$\?; ", wrapped, flags=re.DOTALL)
    return match.group(1) if match else None


def detect_scheduler(platform: str | None = None) -> str:
    platform = platform or _current_platform()
    if platform == "darwin":
        return "launchd"
    if platform.startswith("linux"):
        if _tool_exists("systemctl"):
            return "systemd"
        if _tool_exists("crontab"):
            return "cron"
        return "none"
    return "none"


def schedule_semantics(scheduler: str, time_str: str) -> str:
    if scheduler == "launchd":
        return (
            f"daily at {time_str} local time; runs missed while asleep are "
            "coalesced into one run on wake"
        )
    if scheduler == "systemd":
        return (
            f"daily at {time_str} local time; Persistent=true replays a "
            "missed run at the next opportunity"
        )
    if scheduler == "cron":
        return (
            f"daily at {time_str} local time; NOTE: cron has no coalescing — "
            "a run missed while the machine sleeps is skipped"
        )
    return f"daily at {time_str} local time"


def next_fire(time_str: str, now: datetime | None = None) -> str:
    """Next wall-clock fire time. With coalescing, 'or first wake after'."""
    hour, minute = parse_time(time_str)
    now = now or datetime.now().astimezone()
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate.isoformat(timespec="minutes")


# --- unit generation (pure, fully testable) ---


def build_launchd_plist(
    time_str: str = DEFAULT_TIME,
    command: str = DEFAULT_COMMAND,
    workdir: str | None = None,
) -> dict:
    hour, minute = parse_time(time_str)
    plist: dict = {
        "Label": LAUNCHD_LABEL,
        # /bin/sh -c keeps the command a plain shell string the user can read
        # back out of the plist; launchd itself does no shell parsing.
        "ProgramArguments": ["/bin/sh", "-c", _wrap_command(command)],
        # launchd gives agents a minimal PATH (/usr/bin:/bin:...) that omits
        # the homebrew / uv-tool directories where `claude` actually lives,
        # so freeze the installing user's PATH into the job.
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        },
        # WHY StartCalendarInterval (and not cron or an interval timer):
        # launchd coalesces StartCalendarInterval runs missed during sleep —
        # if the Mac was closed at the scheduled minute, the job fires once on
        # the next wake instead of being skipped. The paper is ready when the
        # laptop opens, whatever time that turns out to be.
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        # Install must not trigger an immediate run; the first edition fires
        # at the next scheduled time.
        "RunAtLoad": False,
        "StandardOutPath": str(log_path()),
        "StandardErrorPath": str(log_path()),
    }
    if workdir:
        # launchd starts agents nowhere near the newsroom; without this key
        # the headless editor cannot find specs/, collectors/, editions/.
        plist["WorkingDirectory"] = workdir
    return plist


def _systemd_escape(command: str) -> str:
    # systemd expands % specifiers inside ExecStart and uses backslash escapes
    # in double-quoted words.
    return command.replace("\\", "\\\\").replace("%", "%%").replace('"', '\\"')


def build_systemd_service(command: str = DEFAULT_COMMAND, workdir: str | None = None) -> str:
    wrapped = _systemd_escape(_wrap_command(command))
    # Without WorkingDirectory the service starts in $HOME and the headless
    # editor cannot find the newsroom (specs/, collectors/, editions/).
    workdir_line = f"WorkingDirectory={workdir}\n" if workdir else ""
    return (
        "[Unit]\n"
        "Description=Morning Paper daily edition\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"{workdir_line}"
        f'ExecStart=/bin/sh -c "{wrapped}"\n'
        f"StandardOutput=append:{log_path()}\n"
        f"StandardError=append:{log_path()}\n"
    )


def build_systemd_timer(time_str: str = DEFAULT_TIME) -> str:
    hour, minute = parse_time(time_str)
    return (
        "[Unit]\n"
        "Description=Morning Paper daily edition timer\n"
        "\n"
        "[Timer]\n"
        f"OnCalendar=*-*-* {hour:02d}:{minute:02d}:00\n"
        "# Persistent=true is the coalescing behavior: a run missed while the\n"
        "# machine was off or asleep is made up at the next opportunity.\n"
        "Persistent=true\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def build_cron_line(
    time_str: str = DEFAULT_TIME,
    command: str = DEFAULT_COMMAND,
    workdir: str | None = None,
) -> str:
    hour, minute = parse_time(time_str)
    if workdir:
        # cron starts jobs in $HOME, where the newsroom is not; cd first. The
        # path rides single-quoted with the same '\'' escape the outer wrapper
        # uses below, so a workdir containing single quotes survives both layers.
        command = "cd '{}' && {}".format(workdir.replace("'", "'\\''"), command)
    # The wrapped command rides inside single quotes, so embedded single
    # quotes (the date format, "today's") become '\'' — and cron turns an
    # unescaped % into a newline inside the command field, hence \%.
    wrapped = _wrap_command(command).replace("'", "'\\''").replace("%", r"\%")
    return (
        f"{minute} {hour} * * * /bin/sh -c '{wrapped}' >> {log_path()} 2>&1 {CRON_MARKER}"
    )


# --- log parsing ---


def parse_routine_log(text: str) -> dict | None:
    """Last run from the marker lines: {'started': iso, 'exit_code': int|None}."""
    started: str | None = None
    exit_code: int | None = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(RUN_START_PREFIX):
            started = line[len(RUN_START_PREFIX) :].strip()
            exit_code = None  # a new run resets the previous run's exit
        elif line.startswith(RUN_EXIT_PREFIX) and started is not None:
            tail = line[len(RUN_EXIT_PREFIX) :].strip()
            exit_code = int(tail) if tail.lstrip("-").isdigit() else None
    if started is None:
        return None
    return {"started": started, "exit_code": exit_code}


def _read_log_tail(max_bytes: int = 65536) -> str:
    path = log_path()
    if not path.is_file():
        return ""
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            return handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


# --- launchd state ---


def _launchctl_state() -> dict | None:
    if not _tool_exists("launchctl"):
        return None
    try:
        proc = _run(["launchctl", "print", f"gui/{os.getuid()}/{LAUNCHD_LABEL}"])
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    state: dict[str, str] = {}
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("state = "):
            state["state"] = line.split("=", 1)[1].strip()
        elif line.startswith("last exit code = "):
            state["last_exit_code"] = line.split("=", 1)[1].strip()
    return state or None


# --- install / uninstall / status ---


def _install_darwin(time_str: str, command: str, workdir: str | None = None) -> tuple[dict, int]:
    plist_file = launchd_plist_path()
    plist_file.parent.mkdir(parents=True, exist_ok=True)
    log_path().parent.mkdir(parents=True, exist_ok=True)
    if plist_file.exists():
        # Re-install: unload the old job first so the new time/command takes.
        _bootout_quietly()
    plist_file.write_bytes(plistlib.dumps(build_launchd_plist(time_str, command, workdir)))
    loaded = False
    note = None
    bootstrap = _run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_file)])
    if bootstrap.returncode == 0:
        loaded = True
    else:
        legacy = _run(["launchctl", "load", str(plist_file)])
        if legacy.returncode == 0:
            loaded = True
            note = "loaded via legacy `launchctl load` (bootstrap unavailable)"
        else:
            note = (
                "plist written but launchctl could not load it now; "
                "launchd picks it up at next login"
            )
    payload = {
        "installed": True,
        "loaded": loaded,
        "scheduler": "launchd",
        "unit": str(plist_file),
    }
    if note:
        payload["note"] = note
    return payload, 0


def _bootout_quietly() -> None:
    res = _run(["launchctl", "bootout", f"gui/{os.getuid()}/{LAUNCHD_LABEL}"])
    if res.returncode != 0:
        _run(["launchctl", "unload", str(launchd_plist_path())])


def _install_systemd(time_str: str, command: str, workdir: str | None = None) -> tuple[dict, int]:
    unit_dir = systemd_unit_dir()
    unit_dir.mkdir(parents=True, exist_ok=True)
    log_path().parent.mkdir(parents=True, exist_ok=True)
    systemd_service_path().write_text(build_systemd_service(command, workdir), encoding="utf-8")
    systemd_timer_path().write_text(build_systemd_timer(time_str), encoding="utf-8")
    _run(["systemctl", "--user", "daemon-reload"])
    enable = _run(["systemctl", "--user", "enable", "--now", f"{SYSTEMD_UNIT}.timer"])
    payload = {
        "installed": True,
        "loaded": enable.returncode == 0,
        "scheduler": "systemd",
        "unit": str(systemd_timer_path()),
    }
    if enable.returncode != 0:
        payload["note"] = "unit files written but `systemctl --user enable --now` failed"
    return payload, 0


def _read_crontab() -> str:
    listing = _run(["crontab", "-l"])
    return listing.stdout if listing.returncode == 0 else ""


def _install_cron(time_str: str, command: str, workdir: str | None = None) -> tuple[dict, int]:
    log_path().parent.mkdir(parents=True, exist_ok=True)
    kept = [
        line for line in _read_crontab().splitlines() if CRON_MARKER not in line
    ]
    kept.append(build_cron_line(time_str, command, workdir))
    write = _run(["crontab", "-"], input_text="\n".join(kept) + "\n")
    payload = {
        "installed": write.returncode == 0,
        "loaded": write.returncode == 0,
        "scheduler": "cron",
        "unit": "crontab",
        "note": (
            "cron has no missed-run coalescing: if the machine is asleep at "
            f"{time_str}, that day's run is skipped"
        ),
    }
    return payload, 0 if write.returncode == 0 else 1


def install_routine(
    time_str: str = DEFAULT_TIME,
    command: str | None = None,
    platform: str | None = None,
    workdir: str | None = None,
) -> tuple[dict, int]:
    hour, minute = parse_time(time_str)  # validates; raises ValueError
    time_str = f"{hour:02d}:{minute:02d}"
    explicit_command = command is not None
    command = command or DEFAULT_COMMAND
    # The scheduled job inherits no shell cwd, so it must be pinned to a
    # directory at install time. The contract: the user installs from their
    # newsroom — capture that directory now so the headless edition run can
    # find specs/, collectors/, and editions/ every morning.
    workdir = os.path.abspath(workdir) if workdir else os.getcwd()
    if not explicit_command and _resolve_claude() is None:
        # The default job is headless Claude; installing it without the binary
        # would just fail silently every morning. Refuse, and hand the user
        # the exact command to wire into whatever scheduler they do have.
        return (
            {
                "installed": False,
                "warning": (
                    "`claude` binary not found on PATH — the default routine runs "
                    "the edition skill headless via Claude Code"
                ),
                "command": command,
                "hint": (
                    "install Claude Code (https://claude.com/claude-code) and retry, "
                    "pass your own --command, or wire the command above into your "
                    "own scheduler"
                ),
            },
            1,
        )
    scheduler = detect_scheduler(platform)
    if scheduler == "launchd":
        payload, code = _install_darwin(time_str, command, workdir)
    elif scheduler == "systemd":
        payload, code = _install_systemd(time_str, command, workdir)
    elif scheduler == "cron":
        payload, code = _install_cron(time_str, command, workdir)
    else:
        return (
            {
                "installed": False,
                "warning": "no supported scheduler found (need launchd, systemd --user, or crontab)",
                "command": command,
                "hint": "wire the command above into your platform's scheduler",
            },
            1,
        )
    payload.update(
        {
            "schedule": {
                "time": time_str,
                "semantics": schedule_semantics(scheduler, time_str),
            },
            "command": command,
            "workdir": workdir,
            "log": str(log_path()),
        }
    )
    return payload, code


def _installed_scheduler() -> str | None:
    """Which scheduler actually has the routine, judged from artifacts on disk."""
    if launchd_plist_path().is_file():
        return "launchd"
    if systemd_timer_path().is_file():
        return "systemd"
    if _tool_exists("crontab") and any(
        CRON_MARKER in line for line in _read_crontab().splitlines()
    ):
        return "cron"
    return None


def _schedule_from_launchd() -> tuple[str | None, str | None, str | None]:
    try:
        with launchd_plist_path().open("rb") as handle:
            data = plistlib.load(handle)
    except Exception:
        return None, None, None
    interval = data.get("StartCalendarInterval") or {}
    time_str = None
    if isinstance(interval, dict) and "Hour" in interval and "Minute" in interval:
        time_str = f"{int(interval['Hour']):02d}:{int(interval['Minute']):02d}"
    command = None
    args = data.get("ProgramArguments") or []
    if len(args) == 3 and args[0] == "/bin/sh":
        command = _unwrap_command(args[2]) or args[2]
    workdir = data.get("WorkingDirectory")
    return time_str, command, workdir if isinstance(workdir, str) else None


def _schedule_from_systemd() -> tuple[str | None, str | None]:
    time_str = None
    command = None
    try:
        timer_text = systemd_timer_path().read_text(encoding="utf-8")
        match = re.search(r"OnCalendar=\*-\*-\* (\d{2}):(\d{2}):\d{2}", timer_text)
        if match:
            time_str = f"{match.group(1)}:{match.group(2)}"
    except OSError:
        pass
    try:
        service_text = systemd_service_path().read_text(encoding="utf-8")
        match = re.search(r'ExecStart=/bin/sh -c "(.*)"', service_text)
        if match:
            unescaped = (
                match.group(1).replace('\\"', '"').replace("%%", "%").replace("\\\\", "\\")
            )
            command = _unwrap_command(unescaped) or unescaped
    except OSError:
        pass
    return time_str, command


def _schedule_from_cron() -> tuple[str | None, str | None]:
    for line in _read_crontab().splitlines():
        if CRON_MARKER not in line:
            continue
        fields = line.split()
        if len(fields) >= 5:
            try:
                return f"{int(fields[1]):02d}:{int(fields[0]):02d}", None
            except ValueError:
                return None, None
    return None, None


def routine_status() -> dict:
    scheduler = _installed_scheduler()
    if scheduler is None:
        return {
            "installed": False,
            "scheduler": None,
            "log": str(log_path()),
            "hint": "optional local fallback: `morning-paper routine install`; prefer your host's native recurrence when available",
        }
    workdir = None
    if scheduler == "launchd":
        time_str, command, workdir = _schedule_from_launchd()
    elif scheduler == "systemd":
        time_str, command = _schedule_from_systemd()
    else:
        time_str, command = _schedule_from_cron()
    payload: dict[str, object] = {
        "installed": True,
        "scheduler": scheduler,
        "schedule": {
            "time": time_str,
            "semantics": schedule_semantics(scheduler, time_str or DEFAULT_TIME),
        },
        "command": command,
        "last_run": parse_routine_log(_read_log_tail()),
        "next_fire": next_fire(time_str) if time_str else None,
        "log": str(log_path()),
    }
    if workdir:
        payload["workdir"] = workdir
    if scheduler == "launchd":
        state = _launchctl_state()
        if state:
            payload["launchd"] = state
        else:
            payload["launchd"] = {"state": "not loaded"}
    return payload


def uninstall_routine() -> tuple[dict, int]:
    scheduler = _installed_scheduler()
    if scheduler is None:
        # Idempotent: uninstalling an absent routine is a no-op, not an error.
        return {"uninstalled": False, "installed": False, "note": "routine was not installed"}, 0
    if scheduler == "launchd":
        _bootout_quietly()
        launchd_plist_path().unlink(missing_ok=True)
    elif scheduler == "systemd":
        _run(["systemctl", "--user", "disable", "--now", f"{SYSTEMD_UNIT}.timer"])
        systemd_timer_path().unlink(missing_ok=True)
        systemd_service_path().unlink(missing_ok=True)
        _run(["systemctl", "--user", "daemon-reload"])
    elif scheduler == "cron":
        kept = [line for line in _read_crontab().splitlines() if CRON_MARKER not in line]
        text = "\n".join(kept)
        _run(["crontab", "-"], input_text=text + "\n" if text else "\n")
    return {"uninstalled": True, "scheduler": scheduler, "log": str(log_path())}, 0


def routine_doctor_summary() -> dict:
    """File-checks only (no subprocess) so doctor stays fast and offline."""
    scheduler = None
    time_str = None
    workdir = None
    if launchd_plist_path().is_file():
        scheduler = "launchd"
        time_str, _, workdir = _schedule_from_launchd()
    elif systemd_timer_path().is_file():
        scheduler = "systemd"
        time_str, _ = _schedule_from_systemd()
    summary: dict[str, object] = {"installed": scheduler is not None, "scheduler": scheduler}
    if time_str:
        summary["time"] = time_str
    if workdir:
        summary["workdir"] = workdir
    return summary


# --- CLI ---


def routine_command(args: list[str]) -> int:
    usage = (
        "usage: morning-paper routine <install|status|uninstall> "
        "[--time HH:MM] [--command CMD] [--workdir PATH]\n"
        "  --workdir PATH  newsroom directory the edition run starts in "
        "(default: current directory)"
    )
    if not args or args[0] in {"-h", "--help"}:
        print(usage)
        return 0
    action, rest = args[0], args[1:]
    time_str = DEFAULT_TIME
    command: str | None = None
    workdir: str | None = None
    index = 0
    while index < len(rest):
        arg = rest[index]
        if arg in {"-h", "--help"}:
            print(usage)
            return 0
        if arg == "--time" and index + 1 < len(rest):
            time_str = rest[index + 1]
            index += 2
            continue
        if arg == "--command" and index + 1 < len(rest):
            command = rest[index + 1]
            index += 2
            continue
        if arg == "--workdir" and index + 1 < len(rest):
            workdir = rest[index + 1]
            index += 2
            continue
        print(f"unknown routine argument: {arg}", file=sys.stderr)
        return 2
    if action == "install":
        if workdir is not None and not os.path.isdir(workdir):
            print(
                f"invalid --workdir {workdir!r}: not an existing directory — pass the "
                "newsroom directory the edition run should start in "
                "(default: current directory)",
                file=sys.stderr,
            )
            return 2
        try:
            payload, code = install_routine(time_str, command, workdir=workdir)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if not payload.get("installed"):
            warning = payload.get("warning")
            if warning:
                print(f"warning: {warning}", file=sys.stderr)
            print(f"command to schedule yourself: {payload.get('command')}", file=sys.stderr)
        print(json.dumps(payload, indent=2))
        return code
    if action == "status":
        print(json.dumps(routine_status(), indent=2))
        return 0
    if action == "uninstall":
        payload, code = uninstall_routine()
        print(json.dumps(payload, indent=2))
        return code
    print(f"unknown routine action: {action}", file=sys.stderr)
    print(usage, file=sys.stderr)
    return 2
