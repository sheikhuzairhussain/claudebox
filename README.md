# claudebox

Open separate Claude desktop profiles from your terminal, with each profile's
local settings and history in its own directory.

```sh
claudebox personal
claudebox work
```

A missing profile is created automatically and opens for first-time sign-in.
Repeated commands focus its existing window.

## Requirements

- macOS with Claude installed at `/Applications/Claude.app`
- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.5.7 or newer

This is an independent utility, not an Anthropic product. It launches Electron
with `--user-data-dir` and verifies the process opened storage in that directory.
It does not switch terminal Claude Code accounts.

## Install

Clone the repository and install with uv:

```sh
git clone https://github.com/sheikhuzairhussain/claudebox.git
cd claudebox
uv tool install .
claudebox --help
```

If uv's executable directory is not on your PATH, run `uv tool update-shell`
and open a new terminal. For an editable installation, use `uv tool install --editable .`.

## Commands

| Command | Behavior |
| --- | --- |
| `claudebox` or `claudebox --help` | Show help |
| `claudebox <profile>` | Create, open, or focus a profile |
| `claudebox --list` | List saved profiles |
| `claudebox --delete <profile>` | Confirm and move a closed profile to Trash |

Profile names contain lowercase letters, digits, underscores, or hyphens and
start with a letter or digit. Names are case-sensitive.

Deletion requires an interactive terminal and typing the exact profile name.
Quit the selected profile's Claude instance before deleting it. If the launcher
cannot inspect a running process, deletion stops rather than guessing.
Local data moves to `~/.Trash`; it does
not delete the Claude account or its cloud data. If personal is the target of
the default Claude directory symlink, that link is removed as well.

## Profile data

Profiles live outside the repository:

```text
~/Library/Application Support/Claude-profiles/<profile>/
```

New directories are accessible only to their owner. Existing permissions are
preserved. Credentials and histories are never copied into this project.
Logs are written to `claudebox-launch.log` inside each profile. The launcher
checks open storage paths with macOS `lsof` before focusing a window. It does not
trust saved PID files, environment markers, or command-line labels on their own.
If a new process does not open the requested storage, the launcher stops that
process and reports an error.

To use your current desktop login as personal, first quit Claude and move the
existing `~/Library/Application Support/Claude` directory to
`~/Library/Application Support/Claude-profiles/personal`. Do this only when the
destination does not already exist. Then create a symlink from the original
Claude directory path to the new personal directory. Keep a backup before
migrating. Installation does not migrate existing data automatically.

During a new profile's first login, macOS may route browser callbacks to another
Claude window. If that happens, quit the other instances, complete login in the
new profile, and reopen them. Concurrent login and Code behavior depends on the
installed Claude version; the automated tests do not authenticate real accounts.

## Development

```sh
uv sync --locked
uv run claudebox --help
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

The package uses a `src` layout, a console entry point, and no runtime
dependencies. Tests use temporary profile directories and mock macOS process
interactions. They do not open Claude, read real credentials, or delete real
profiles. GitHub Actions runs lint, tests, and package builds on macOS with
Python 3.11 and 3.13.

## Compatibility

On macOS Claude desktop 1.46388.4, a second profile was observed opening at the
sign-in screen while the existing personal session remained available. Process
inspection confirmed separate storage directories. The two-profile workflow was subsequently confirmed working by the user.
Automated tests do not authenticate real accounts or verify every Code feature.

`CLAUDE_USER_DATA_DIR` is not equivalent to `--user-data-dir`. This Claude build
removes the environment variable but accepts the command-line flag. The launcher
therefore clears legacy profile environment variables and passes the flag.
The approach was identified in
[Claude-Code-Desktop-Switcher](https://github.com/PriyanshuGeTRekT/Claude-Code-Desktop-Switcher),
whose implementation targets Windows.

## Distribution

`uv build` creates wheel and source archives in `dist/`. The repository contains
application source only; profile data stays outside it. This project is distributed
through GitHub and is not currently published on PyPI.

## License

[MIT](LICENSE).
