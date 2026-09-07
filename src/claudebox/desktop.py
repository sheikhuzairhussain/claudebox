"""Inspect the data directory actually used by a Claude desktop process."""

import os
import subprocess
from pathlib import Path


def profile_in_use(pid: int, directory: Path) -> bool:
    """Check open storage files, not launch arguments or environment markers."""
    result = subprocess.run(
        ["/usr/sbin/lsof", "-p", str(pid), "-Fn"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        raise RuntimeError(f"Cannot verify Claude process {pid}'s profile directory")
    directory = directory.resolve()
    storage_roots = {"WebStorage", "Local Storage", "IndexedDB", "Session Storage"}
    for line in result.stdout.splitlines():
        if not line.startswith("n/"):
            continue
        try:
            relative = Path(line[1:]).resolve().relative_to(directory)
        except ValueError:
            continue
        if relative.parts and (
            relative.parts[0] in storage_roots or relative.parts[0] == "Cookies"
        ):
            return True
    return False
