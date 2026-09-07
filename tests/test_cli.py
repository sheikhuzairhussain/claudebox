"""CLI behavior checks with no access to real profiles or applications."""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from claudebox import cli


@pytest.fixture
def profiles(tmp_path, monkeypatch):
    root = tmp_path / "Library/Application Support/Claude-profiles"
    monkeypatch.setattr(cli, "ROOT", root)
    monkeypatch.setattr(cli, "profile_in_use", Mock(return_value=True))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(cli, "find_instance", Mock(return_value=None))
    monkeypatch.setattr(cli, "focus", Mock(return_value=True))
    executable = tmp_path / "Claude"
    executable.touch()
    monkeypatch.setattr(cli, "APP", str(executable))
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    old_umask = os.umask(0o077)
    try:
        yield root
    finally:
        os.umask(old_umask)


@pytest.mark.parametrize("args", [[], ["--help"]])
def test_help_has_no_side_effects(profiles, capsys, args):
    assert cli.main(args) == 0
    assert "--delete <profile>" in capsys.readouterr().out
    assert not profiles.exists()


@pytest.mark.parametrize(
    "args",
    [["../escape"], ["UPPER"], ["with space"], ["--delete"], ["a", "b"], ["--unknown"], [""]],
)
def test_invalid_arguments_do_not_create_profiles(profiles, args):
    assert cli.main(args) == 2
    assert not profiles.exists()


def test_list_only_valid_profile_directories(profiles, capsys):
    assert cli.main(["--list"]) == 0
    assert "No saved profiles" in capsys.readouterr().out
    for name in ["personal", "mytender", ".hidden", "INVALID"]:
        (profiles / name).mkdir(parents=True)
    (profiles / "file").touch()
    (profiles / "linked").symlink_to(profiles / "personal")
    assert cli.main(["--list"]) == 0
    assert capsys.readouterr().out == "mytender\npersonal\n"


def test_launch_uses_flag_and_clears_legacy_environment(profiles, monkeypatch):
    process = SimpleNamespace(pid=123, poll=lambda: None)
    launch = Mock(return_value=process)
    monkeypatch.setattr(cli.subprocess, "Popen", launch)
    monkeypatch.setenv("CLAUDE_USER_DATA_DIR", "/legacy/personal")
    monkeypatch.setenv("CLAUDEBOX_PROFILE", "personal")
    previous = os.environ.get("CLAUDE_USER_DATA_DIR")
    assert cli.main(["mytender"]) == 0
    profile = profiles / "mytender"
    assert profile.stat().st_mode & 0o777 == 0o700
    assert (profile / ".claudebox.pid").read_text() == "123\n"
    environment = launch.call_args.kwargs["env"]
    assert launch.call_args.args[0] == [cli.APP, f"--user-data-dir={profile}"]
    assert "CLAUDE_USER_DATA_DIR" not in environment
    assert "CLAUDEBOX_PROFILE" not in environment
    assert os.environ.get("CLAUDE_USER_DATA_DIR") == previous


def test_existing_instance_is_focused_without_launch(profiles, monkeypatch):
    cli.find_instance.return_value = 456
    launch = Mock()
    monkeypatch.setattr(cli.subprocess, "Popen", launch)
    assert cli.main(["personal"]) == 0
    launch.assert_not_called()
    cli.focus.assert_called_once_with(456)


def test_stale_pid_is_not_trusted(profiles, monkeypatch):
    profile = profiles / "personal"
    profile.mkdir(parents=True)
    (profile / ".claudebox.pid").write_text("99999\n")
    launch = Mock(return_value=SimpleNamespace(pid=321, poll=lambda: None))
    monkeypatch.setattr(cli.subprocess, "Popen", launch)
    assert cli.main(["personal"]) == 0
    launch.assert_called_once()
    assert (profile / ".claudebox.pid").read_text() == "321\n"


def test_failed_launch_returns_error(profiles, monkeypatch, capsys):
    monkeypatch.setattr(cli.subprocess, "Popen", Mock(return_value=SimpleNamespace(poll=lambda: 1)))
    assert cli.main(["personal"]) == 1
    assert "exited during startup" in capsys.readouterr().err
    assert not (profiles / "personal/.claudebox.pid").exists()


def test_launch_rejects_symlink_profile(profiles):
    (profiles / "personal").mkdir(parents=True)
    (profiles / "alias").symlink_to(profiles / "personal")
    assert cli.main(["alias"]) == 1


@pytest.fixture
def saved_profile(profiles, monkeypatch):
    profile = profiles / "personal"
    profile.mkdir(parents=True)
    (profile / "sentinel").write_text("keep this data")
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    return profile


def test_delete_cancel_preserves_data(saved_profile, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "no")
    assert cli.main(["--delete", "personal"]) == 1
    assert (saved_profile / "sentinel").read_text() == "keep this data"


def test_delete_requires_interactive_confirmation(saved_profile, monkeypatch):
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert cli.main(["--delete", "personal"]) == 1
    assert saved_profile.exists()


@pytest.mark.parametrize("responses", [[42], [None, 42]])
def test_delete_refuses_running_or_newly_started_profile(saved_profile, monkeypatch, responses):
    cli.find_instance.side_effect = responses
    monkeypatch.setattr("builtins.input", lambda _: "personal")
    assert cli.main(["--delete", "personal"]) == 1
    assert saved_profile.exists()


def test_delete_moves_data_to_trash_and_removes_personal_link(saved_profile, monkeypatch, tmp_path):
    default = saved_profile.parent.parent / "Claude"
    default.symlink_to(saved_profile)
    monkeypatch.setattr("builtins.input", lambda _: "personal")
    assert cli.main(["--delete", "personal"]) == 0
    assert not saved_profile.exists()
    assert not default.is_symlink()
    trashed = list((tmp_path / ".Trash").iterdir())
    assert len(trashed) == 1
    assert (trashed[0] / "sentinel").read_text() == "keep this data"


def test_delete_unknown_profile_has_no_side_effects(profiles):
    assert cli.main(["--delete", "absent"]) == 1
    assert not profiles.exists()


def test_errors_have_no_traceback(profiles, monkeypatch, capsys):
    monkeypatch.setattr(cli, "run", Mock(side_effect=OSError("permission denied")))
    assert cli.main(["personal"]) == 1
    assert capsys.readouterr().err == "claudebox: permission denied\n"


def test_process_matching_uses_actual_storage(monkeypatch):
    monkeypatch.setattr(
        cli.subprocess, "check_output", Mock(return_value=f"123 {cli.APP}\n456 {cli.APP}\n")
    )
    monkeypatch.setattr(cli, "profile_in_use", Mock(side_effect=[False, True]))
    assert cli.find_instance("mytender", Path("/example/mytender")) == 456


def test_ignored_flag_stops_new_process_without_claiming_success(profiles, monkeypatch, capsys):
    cli.profile_in_use.return_value = False
    process = SimpleNamespace(pid=789, poll=lambda: None, terminate=Mock())
    monkeypatch.setattr(cli.subprocess, "Popen", Mock(return_value=process))
    assert cli.main(["mytender"]) == 1
    assert "did not open the requested profile" in capsys.readouterr().err
    process.terminate.assert_called_once()
    cli.focus.assert_not_called()
    assert not (profiles / "mytender/.claudebox.pid").exists()
