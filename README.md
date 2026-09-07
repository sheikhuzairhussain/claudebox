# claudebox

Run separate Claude desktop accounts side by side on macOS.

```sh
claudebox personal
claudebox work
```

Each profile opens in its own window. New profiles prompt you to sign in;
running the command again focuses the existing window.

## Install

Requires macOS, Claude at `/Applications/Claude.app`, Python 3.11+, and
[uv](https://docs.astral.sh/uv/getting-started/installation/) 0.5.7+.

```sh
git clone https://github.com/sheikhuzairhussain/claudebox.git
cd claudebox
uv tool install .
```

If `claudebox` isn't found, run `uv tool update-shell` and open a new terminal.

## Usage

| Command | Action |
| --- | --- |
| `claudebox` or `claudebox --help` | Show help |
| `claudebox <profile>` | Create, open, or focus a profile |
| `claudebox --list` | List profiles |
| `claudebox --delete <profile>` | Move a profile to Trash after confirmation |

Names can contain lowercase letters, digits, hyphens, and underscores, and must
start with a letter or digit.

To delete a profile, quit its Claude window first, then type the profile name
when prompted. This removes local profile data, not your Claude account.

## Profile data

Desktop profiles are stored in:

```text
~/Library/Application Support/Claude-profiles/<profile>/
```

Desktop sign-ins and settings are separate. Claude Code can still share local
project transcripts and memory through `~/.claude`; these profiles are not a
filesystem sandbox. The terminal Claude Code login is unaffected.

### Keep your existing login

Installation leaves your existing Claude data in place. To adopt it as `personal`,
quit Claude, back up `~/Library/Application Support/Claude`, and move that directory
to `Claude-profiles/personal`. The destination must not already exist. Create a
symlink at the original path pointing to the new location if you want ordinary
Claude launches to keep using personal.

### Troubleshooting

- **Sign-in opens the wrong window:** quit the other Claude instances, finish
  signing in, then reopen them.
- **Launch fails:** check `claudebox-launch.log` inside the profile directory.
  The launcher stops a new process if it cannot verify the requested storage path.

The launcher uses Electron's `--user-data-dir` flag and checks the process's open
storage files. Tested with Claude desktop 1.46388.4 on macOS. Claude updates may
affect compatibility.

## Development

```sh
uv sync --locked
uv run claudebox --help
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

Use `uv tool install --editable .` to run your checkout as an installed command.
Tests use temporary directories and mocked process inspection. CI runs on macOS
with Python 3.11 and 3.13. Build artifacts are written to `dist/`.

## Credits and license

Inspired by [Claude-Code-Desktop-Switcher](https://github.com/PriyanshuGeTRekT/Claude-Code-Desktop-Switcher)
for Windows. Independent of Anthropic. [MIT license](LICENSE).
