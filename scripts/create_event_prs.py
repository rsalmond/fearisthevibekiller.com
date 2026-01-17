#!/usr/bin/env python3
"""Create one pull request per rendered event QMD file."""
from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


LOGGER = logging.getLogger(__name__)
EVENTS_DIR = Path("data") / "_events"
META_PATTERN = re.compile(r"^<!--\s*event-meta:\s*(.+?)\s*-->$")


def prepare_command(args: list[str], cwd: Path) -> list[str]:
    """Prepare command arguments for execution."""
    if args and args[0] == "git":
        return ["git", "-c", f"safe.directory={cwd.as_posix()}"] + args[1:]
    return args


def run_command(args: list[str], cwd: Path, check: bool = True) -> str:
    """Run a command and return stdout."""
    command = prepare_command(args, cwd)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip()
        if message:
            LOGGER.error("Command failed: %s", message)
        raise
    output = result.stdout.strip()
    if result.stderr.strip():
        LOGGER.debug("Command stderr: %s", result.stderr.strip())
    return output


def ensure_git_identity(root: Path) -> None:
    """Ensure git has a user name and email configured."""
    name = run_command(["git", "config", "user.name"], root, check=False)
    email = run_command(["git", "config", "user.email"], root, check=False)
    if not name:
        run_command(["git", "config", "user.name", "event-bot"], root)
    if not email:
        run_command(["git", "config", "user.email", "event-bot@users.noreply.github.com"], root)


def repo_root() -> Path:
    """Return the repository root directory."""
    output = run_command(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    return Path(output).resolve()


def github_remote_http_url(root: Path) -> Optional[str]:
    """Return an HTTPS remote URL suitable for token auth."""
    origin = run_command(["git", "remote", "get-url", "origin"], root, check=False)
    if not origin:
        return None
    origin = origin.strip()
    if origin.startswith("https://"):
        return origin
    if origin.startswith("git@github.com:"):
        repo_path = origin.split("git@github.com:", 1)[1]
        if repo_path.endswith(".git"):
            repo_path = repo_path[:-4]
        return f"https://github.com/{repo_path}.git"
    return None


def tokenized_remote_url(root: Path) -> Optional[str]:
    """Return a remote URL with token injected for HTTPS auth."""
    token = (
        os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GITHUB_PAT")
    )
    if not token:
        return None
    remote = github_remote_http_url(root)
    if not remote:
        return None
    return remote.replace("https://", f"https://x-access-token:{token}@")


def list_changed_event_files(root: Path) -> list[Path]:
    """Return event QMD files that are new or modified."""
    output = run_command(["git", "status", "--porcelain"], root)
    files: list[Path] = []
    for line in output.splitlines():
        if not line:
            continue
        status = line[:2]
        path_text = line[3:]
        if status.strip() not in {"??", "M", "A"}:
            continue
        path = Path(path_text)
        if path.suffix != ".qmd":
            continue
        if not path.as_posix().startswith(f"{EVENTS_DIR.as_posix()}/"):
            continue
        files.append((root / path).resolve())
    return files


def parse_meta_line(line: str) -> dict:
    """Parse the metadata comment into a dict."""
    match = META_PATTERN.match(line.strip())
    if not match:
        return {}
    payload = match.group(1)
    data: dict[str, str] = {}
    for part in payload.split(";"):
        if not part.strip():
            continue
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def read_event_metadata(path: Path) -> dict:
    """Read the metadata comment from a QMD file."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("<!--"):
            data = parse_meta_line(line)
            if data:
                return data
    return {}


def build_pr_body(
    event_name: str,
    event_date: str,
    post_url: str,
    ticket_link: Optional[str],
    relative_path: Path,
) -> str:
    """Build the pull request body with event metadata."""
    lines = [
        f"Event Name: {event_name or 'Unknown'}",
        f"Event Date: {event_date or 'Unknown'}",
        f"Post URL: {post_url}",
        f"Ticket/Info URL: {ticket_link or 'Unknown'}",
        f"Source File: {relative_path.as_posix()}",
    ]
    return "\n".join(lines)


def branch_name_for_file(path: Path) -> str:
    """Return a branch name for a given event file."""
    base = path.stem.lower()
    cleaned = re.sub(r"[^a-z0-9-]+", "-", base).strip("-")
    return f"auto/event-{cleaned}"


def pr_exists(root: Path, branch: str) -> bool:
    """Return True when a PR already exists for the branch."""
    output = run_command(
        ["gh", "pr", "list", "--head", branch, "--json", "number", "--jq", "length"],
        root,
        check=False,
    )
    try:
        return int(output or "0") > 0
    except ValueError:
        return False


def remote_branch_exists(root: Path, branch: str) -> bool:
    """Return True when the branch already exists on origin."""
    output = run_command(
        ["git", "ls-remote", "--heads", "origin", branch],
        root,
        check=False,
    )
    return bool(output.strip())


def local_branch_exists(root: Path, branch: str) -> bool:
    """Return True when the branch exists locally."""
    output = run_command(["git", "branch", "--list", branch], root, check=False)
    return bool(output.strip())


def create_pr_for_file(root: Path, path: Path, base_branch: str) -> None:
    """Create a pull request for the specified event QMD file."""
    ensure_git_identity(root)
    metadata = read_event_metadata(path)
    post_url = metadata.get("post_url")
    ticket_link = metadata.get("ticket_link")
    event_date = metadata.get("event_date", "")
    event_name = metadata.get("event_name", "")
    if not post_url:
        LOGGER.warning("Skipping %s: missing event metadata comment", path)
        return
    relative_path = path.relative_to(root)
    branch = branch_name_for_file(path)

    if pr_exists(root, branch):
        LOGGER.info("Skipping %s: PR already exists for %s", path, branch)
        return
    if remote_branch_exists(root, branch):
        LOGGER.info("Skipping %s: remote branch %s already exists", path, branch)
        return
    if local_branch_exists(root, branch):
        LOGGER.info("Skipping %s: local branch %s already exists", path, branch)
        return

    original_branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)
    run_command(["git", "switch", "-c", branch], root)
    token_remote = tokenized_remote_url(root)
    try:
        run_command(["git", "add", relative_path.as_posix()], root)
        title = f"Add event: {event_name or path.stem}"
        run_command(["git", "commit", "-m", title], root)
        if token_remote:
            run_command(["git", "push", "-u", token_remote, branch], root)
        else:
            run_command(["git", "push", "-u", "origin", branch], root)
        body = build_pr_body(event_name, event_date, post_url, ticket_link, relative_path)
        run_command(
            [
                "gh",
                "pr",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--base",
                base_branch,
                "--head",
                branch,
            ],
            root,
        )
        LOGGER.info("Created PR for %s", relative_path)
    finally:
        run_command(["git", "switch", original_branch], root, check=False)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Create PRs for new event QMD files.")
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch for the pull requests.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the PR creation workflow."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()
    root = repo_root()
    candidates = list_changed_event_files(root)
    if not candidates:
        LOGGER.info("No new or modified event QMD files found.")
        return 0
    for path in candidates:
        create_pr_for_file(root, path, args.base_branch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
