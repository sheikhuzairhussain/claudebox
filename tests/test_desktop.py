"""Check real storage paths rather than trusting profile launch markers."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from claudebox import desktop


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("work/WebStorage/QuotaManager", True),
        ("personal/WebStorage/QuotaManager", False),
        ("work-extra/WebStorage/QuotaManager", False),
        ("work/claudebox-launch.log", False),
        ("work/.claudebox.pid", False),
    ],
)
def test_only_profile_storage_proves_isolation(tmp_path, monkeypatch, relative, expected):
    monkeypatch.setattr(
        desktop.subprocess,
        "run",
        Mock(return_value=SimpleNamespace(returncode=0, stdout=f"n{tmp_path / relative}\n")),
    )
    assert desktop.profile_in_use(123, tmp_path / "work") is expected


def test_default_symlink_resolves_to_personal(tmp_path, monkeypatch):
    personal = tmp_path / "personal"
    personal.mkdir()
    default = tmp_path / "Claude"
    default.symlink_to(personal)
    monkeypatch.setattr(
        desktop.subprocess,
        "run",
        Mock(
            return_value=SimpleNamespace(
                returncode=0, stdout=f"n{default}/WebStorage/QuotaManager\n"
            )
        ),
    )
    assert desktop.profile_in_use(123, personal)


def test_inspection_failure_does_not_claim_profile_is_unused(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop.subprocess, "run", Mock(return_value=SimpleNamespace(returncode=1)))
    monkeypatch.setattr(desktop.os, "kill", Mock())
    with pytest.raises(RuntimeError, match="Cannot verify"):
        desktop.profile_in_use(123, tmp_path)


def test_exited_process_is_unused(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop.subprocess, "run", Mock(return_value=SimpleNamespace(returncode=1)))
    monkeypatch.setattr(desktop.os, "kill", Mock(side_effect=ProcessLookupError))
    assert not desktop.profile_in_use(123, tmp_path)
