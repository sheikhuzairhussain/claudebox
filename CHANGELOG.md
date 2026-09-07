# Changelog

## 0.1.0

- Package the launcher as a uv-managed Python project with a console entry point.
- Add help, profile listing, and confirmed deletion to Trash.
- Launch profiles with Electron's `--user-data-dir` command-line flag.
- Verify actual open storage paths before reporting a launch or focusing a window.
- Stop a newly launched process if it ignores the requested directory.
- Protect profile deletion using actual storage paths rather than process labels.
- Add regression tests for the account isolation failure and macOS CI.

The original launcher trusted `CLAUDE_USER_DATA_DIR` and a process marker.
Claude desktop 1.46388.4 removes the override in packaged builds, so a process
labelled with a new profile could still open the default account. The command-line
flag works independently of that variable: a second profile opened at sign-in on
the same installed build. The user subsequently confirmed the two-profile workflow works.
