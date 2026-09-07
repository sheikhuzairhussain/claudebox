"""Launch or focus an isolated Claude desktop profile."""

import fcntl
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

from claudebox.desktop import profile_in_use

APP = "/Applications/Claude.app/Contents/MacOS/Claude"
ROOT = Path.home() / "Library/Application Support/Claude-profiles"
HELP = """Usage:
  claudebox <profile>          Open or focus a profile; create it if missing
  claudebox --help             Show this help
  claudebox --list             List saved profiles
  claudebox --delete <profile> Move a closed profile to Trash after confirmation

Examples:
  claudebox personal
  claudebox work

Profile names use lowercase letters, digits, underscores, or hyphens,
and must start with a letter or digit. New profiles require sign-in.
The launcher verifies each window's data directory before reporting success."""


def delete_profile(profile):
    directory = ROOT / profile
    if not directory.is_dir() or directory.is_symlink():
        raise RuntimeError(f"Profile does not exist: {profile}")
    with (ROOT / ".launcher.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if find_instance(profile, directory):
            raise RuntimeError(f"Quit the {profile} Claude instance before deleting it")
        if not sys.stdin.isatty():
            raise RuntimeError("Deletion requires confirmation in an interactive terminal")
        print(
            f"This moves all local data for {profile} to Trash, including its saved login and history."
        )
        if profile == "personal":
            print("It also removes the default Claude directory link to personal.")
        try:
            answer = input(f"Type {profile} to confirm deletion: ")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 1
        if answer != profile:
            print("Cancelled.")
            return 1
        # Recheck after the user has had time to answer.
        if find_instance(profile, directory):
            raise RuntimeError(f"{profile} started running; quit it before deleting")
        trash = Path.home() / ".Trash"
        trash.mkdir(mode=0o700, exist_ok=True)
        target = (
            trash / f"claudebox-{profile}-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        )
        default = ROOT.parent / "Claude"
        remove_link = default.is_symlink() and default.resolve() == directory.resolve()
        directory.rename(target)
        if remove_link:
            try:
                default.unlink()
            except OSError:
                target.rename(directory)
                raise
        print(f"Moved {profile} to Trash: {target}")
    return 0


def focus(pid):
    script = (
        'ObjC.import("AppKit"); '
        f"var app = $.NSRunningApplication.runningApplicationWithProcessIdentifier({pid}); "
        'if (!app || !app.activateWithOptions(3)) throw Error("Could not focus Claude");'
    )
    return (
        subprocess.run(
            ["/usr/bin/osascript", "-l", "JavaScript", "-e", script], capture_output=True
        ).returncode
        == 0
    )


def find_instance(profile, directory):
    # Legacy markers can say work while the process is using personal.
    rows = subprocess.check_output(["/bin/ps", "-axo", "pid=,comm="], text=True)
    for row in rows.splitlines():
        parts = row.strip().split(None, 1)
        if len(parts) != 2 or parts[1] != APP:
            continue
        pid = int(parts[0])
        if profile_in_use(pid, directory):
            return pid
    return None


def run(args):
    if not args or args == ["--help"]:
        print(HELP)
        return 0
    if args == ["--list"]:
        profiles = (
            sorted(
                p.name
                for p in ROOT.iterdir()
                if p.is_dir()
                and not p.is_symlink()
                and re.fullmatch(r"[a-z0-9][a-z0-9_-]*", p.name)
            )
            if ROOT.exists()
            else []
        )
        print("\n".join(profiles) if profiles else "No saved profiles.")
        return 0
    deleting = len(args) == 2 and args[0] == "--delete"
    if (not deleting and len(args) != 1) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args[-1]):
        print(HELP, file=sys.stderr)
        return 2
    profile = args[-1]
    if deleting:
        return delete_profile(profile)
    if not Path(APP).is_file():
        raise RuntimeError("Claude desktop is not installed at /Applications/Claude.app")
    os.umask(0o077)
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = ROOT / profile
    with (ROOT / ".launcher.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if directory.is_symlink():
            raise RuntimeError(f"Profile directory must not be a symlink: {directory}")
        directory.mkdir(mode=0o700, exist_ok=True)
        record = directory / ".claudebox.pid"
        # Rediscover processes instead of trusting a stale or reused PID.
        pid = find_instance(profile, directory)
        if pid:
            record.write_text(f"{pid}\n")
            if not focus(pid):
                raise RuntimeError(f"{profile} is running, but its window could not be focused")
            print(f"Focused Claude profile: {profile}")
            return 0
        record.unlink(missing_ok=True)
        environment = os.environ.copy()
        environment.pop("CLAUDE_USER_DATA_DIR", None)
        environment.pop("CLAUDEBOX_PROFILE", None)
        with (directory / "claudebox-launch.log").open("ab") as log:
            process = subprocess.Popen(
                [APP, f"--user-data-dir={directory}"],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        try:
            for _ in range(40):
                if process.poll() is not None:
                    raise RuntimeError(
                        f"Claude exited during startup; see {directory / 'claudebox-launch.log'}"
                    )
                if profile_in_use(process.pid, directory):
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError(
                    "Claude did not open the requested profile's storage. "
                    "This build may not support --user-data-dir; launch stopped."
                )
        except (OSError, RuntimeError, subprocess.SubprocessError):
            if process.poll() is None:
                process.terminate()
            raise
        record.write_text(f"{process.pid}\n")
        focus(process.pid)
        print(f"Opened Claude profile: {profile}")
    return 0


def main(argv=None):
    """Console entry point; return a shell exit code without exposing tracebacks."""
    try:
        return run(sys.argv[1:] if argv is None else argv)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"claudebox: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
