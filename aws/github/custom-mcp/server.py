#!/usr/bin/env python3

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import requests

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


# ============================================================
# CONFIGURATION
# ============================================================

MCP_API_KEY = os.environ.get("MCP_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

GITHUB_API = "https://api.github.com"

if not MCP_API_KEY:
    raise RuntimeError("MCP_API_KEY environment variable missing")

if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN environment variable missing")


# ============================================================
# MCP API KEY AUTH
# ============================================================

class APIKeyAuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next
    ):

        supplied_key = request.headers.get("x-api-key")

        if not supplied_key:

            auth = request.headers.get(
                "authorization",
                ""
            )

            if auth.lower().startswith("bearer "):
                supplied_key = auth[7:]

        if (
            not supplied_key
            or not secrets.compare_digest(
                supplied_key,
                MCP_API_KEY
            )
        ):

            return JSONResponse(
                {"error": "Unauthorized"},
                status_code=401
            )

        return await call_next(request)


# ============================================================
# MCP SERVER
# ============================================================

mcp = FastMCP(
    "GitHub Deployment Remediation MCP",

    host="0.0.0.0",

    transport_security=
    TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
)

app = mcp.streamable_http_app()

app.add_middleware(
    APIKeyAuthMiddleware
)


# ============================================================
# GITHUB HTTP CLIENT
# ============================================================

def github_headers():

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2026-03-10"
    }


def github_get(
    path: str,
    params: Optional[dict] = None
):

    response = requests.get(
        f"{GITHUB_API}{path}",
        headers=github_headers(),
        params=params,
        timeout=30
    )

    if not response.ok:

        raise RuntimeError(
            f"GitHub API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()


# ============================================================
# HELPERS
# ============================================================

def timestamp():

    return datetime.now(
        timezone.utc
    ).isoformat()


def validate_repo(
    owner: str,
    repo: str
):

    if not owner or not repo:
        raise ValueError(
            "owner and repo are required"
        )

    forbidden = [
        " ",
        "..",
        "/",
        "\\"
    ]

    for value in [owner, repo]:

        if any(
            character in value
            for character in forbidden
        ):

            raise ValueError(
                "Invalid GitHub owner/repository name"
            )


def validate_sha(commit_sha: str):

    if not commit_sha:
        raise ValueError(
            "commit_sha is required"
        )

    if len(commit_sha) != 40:
        raise ValueError(
            "commit_sha must be a full 40-character SHA"
        )

    allowed = set(
        "0123456789abcdefABCDEF"
    )

    if not all(
        character in allowed
        for character in commit_sha
    ):

        raise ValueError(
            "Invalid commit SHA"
        )


# ============================================================
# TOOL 1
# CURRENT COMMIT
# ============================================================

@mcp.tool()
def get_current_commit(
    owner: str,
    repo: str,
    branch: str = "main"
) -> Dict[str, Any]:

    """
    Get the current HEAD commit of a GitHub branch.
    """

    validate_repo(owner, repo)

    data = github_get(
        f"/repos/{owner}/{repo}/commits/{branch}"
    )

    return {

        "timestamp": timestamp(),

        "repository":
            f"{owner}/{repo}",

        "branch":
            branch,

        "sha":
            data["sha"],

        "message":
            data["commit"]["message"],

        "author":
            data["commit"]["author"]["name"],

        "date":
            data["commit"]["author"]["date"]

    }


# ============================================================
# TOOL 2
# COMMIT DETAILS
# ============================================================

@mcp.tool()
def get_commit_details(
    owner: str,
    repo: str,
    commit_sha: str
) -> Dict[str, Any]:

    """
    Inspect a GitHub commit including changed files,
    additions, deletions and parent commits.
    """

    validate_repo(owner, repo)
    validate_sha(commit_sha)

    data = github_get(
        f"/repos/{owner}/{repo}/commits/{commit_sha}"
    )

    files = []

    for file in data.get("files", []):

        files.append({

            "filename":
                file.get("filename"),

            "status":
                file.get("status"),

            "additions":
                file.get("additions"),

            "deletions":
                file.get("deletions"),

            "changes":
                file.get("changes")

        })

    return {

        "timestamp": timestamp(),

        "repository":
            f"{owner}/{repo}",

        "sha":
            data["sha"],

        "message":
            data["commit"]["message"],

        "author":
            data["commit"]["author"]["name"],

        "parents":
            [
                parent["sha"]
                for parent
                in data.get("parents", [])
            ],

        "files":
            files

    }


# ============================================================
# TOOL 3
# WORKFLOW RUNS
# ============================================================

@mcp.tool()
def get_workflow_runs(
    owner: str,
    repo: str,
    branch: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:

    """
    Get recent GitHub Actions workflow runs.
    """

    validate_repo(owner, repo)

    limit = max(
        1,
        min(limit, 50)
    )

    params = {
        "per_page": limit
    }

    if branch:
        params["branch"] = branch

    data = github_get(
        f"/repos/{owner}/{repo}/actions/runs",
        params=params
    )

    runs = []

    for run in data.get(
        "workflow_runs",
        []
    ):

        runs.append({

            "id":
                run["id"],

            "name":
                run["name"],

            "status":
                run["status"],

            "conclusion":
                run["conclusion"],

            "branch":
                run["head_branch"],

            "commit_sha":
                run["head_sha"],

            "commit_message":
                run["head_commit"]["message"]
                if run.get("head_commit")
                else "",

            "created_at":
                run["created_at"],

            "updated_at":
                run["updated_at"],

            "html_url":
                run["html_url"]

        })

    return {

        "timestamp": timestamp(),

        "repository":
            f"{owner}/{repo}",

        "runs":
            runs

    }


# ============================================================
# INTERNAL GIT COMMAND
# ============================================================

def run_git(
    args,
    cwd,
    env
):

    result = subprocess.run(

        [
            "git",
            *args
        ],

        cwd=cwd,

        env=env,

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        text=True,

        timeout=300

    )

    if result.returncode != 0:

        raise RuntimeError(
            "Git command failed:\n"
            + result.stderr
        )

    return result.stdout.strip()


# ============================================================
# TOOL 4
# ROLLBACK COMMIT
# ============================================================

@mcp.tool()
def rollback_commit(
    owner: str,
    repo: str,
    commit_sha: str,
    branch: str = "main",
    confirm: bool = False
) -> Dict[str, Any]:

    """
    Safely revert a specific GitHub commit.

    This creates a NEW revert commit.

    It does NOT:
    - reset history
    - force push
    - delete commits

    confirm must be true before the rollback is executed.
    """

    validate_repo(owner, repo)
    validate_sha(commit_sha)

    if not confirm:

        return {

            "action":
                "rollback_commit",

            "status":
                "AWAITING_CONFIRMATION",

            "repository":
                f"{owner}/{repo}",

            "branch":
                branch,

            "commit_to_revert":
                commit_sha,

            "message":
                "Rollback was NOT executed. "
                "Set confirm=true after approval."

        }


    # --------------------------------------------------------
    # Verify the requested commit
    # --------------------------------------------------------

    commit = github_get(
        f"/repos/{owner}/{repo}/commits/{commit_sha}"
    )

    parents = commit.get(
        "parents",
        []
    )

    if len(parents) != 1:

        raise RuntimeError(
            "The selected commit is a merge commit. "
            "Automatic rollback is disabled for merge "
            "commits. Revert it manually or extend the "
            "tool with an explicit mainline parameter."
        )


    # --------------------------------------------------------
    # Verify branch currently points to expected history
    # --------------------------------------------------------

    branch_data = github_get(
        f"/repos/{owner}/{repo}/commits/{branch}"
    )

    current_sha = branch_data["sha"]


    # --------------------------------------------------------
    # Create temporary workspace
    # --------------------------------------------------------

    temp_dir = tempfile.mkdtemp(
        prefix="github-rollback-"
    )

    try:

        repo_url = (
            f"https://github.com/"
            f"{owner}/{repo}.git"
        )


        # ----------------------------------------------------
        # Git authentication through temporary credential
        # ----------------------------------------------------

        credential_file = os.path.join(
            temp_dir,
            "git-credentials"
        )

        with open(
            credential_file,
            "w"
        ) as f:

            f.write(
                f"https://x-access-token:"
                f"{GITHUB_TOKEN}"
                f"@github.com\n"
            )


        env = os.environ.copy()

        env[
            "GIT_TERMINAL_PROMPT"
        ] = "0"

        env[
            "GIT_CONFIG_GLOBAL"
        ] = os.devnull

        env[
            "GIT_CONFIG_SYSTEM"
        ] = os.devnull

        env[
            "HOME"
        ] = temp_dir

        # Git credential helper reads the temporary file.
        run_git(
            [
                "config",
                "--global",
                "credential.helper",
                f"store --file={credential_file}"
            ],
            cwd=temp_dir,
            env=env
        )


        # ----------------------------------------------------
        # Clone only the required branch
        # ----------------------------------------------------

        repo_dir = os.path.join(
            temp_dir,
            "repo"
        )

        run_git(

            [
                "clone",

                "--branch",
                branch,

                "--single-branch",

                repo_url,

                repo_dir
            ],

            cwd=temp_dir,

            env=env
        )


        # ----------------------------------------------------
        # Make sure local HEAD matches GitHub branch
        # ----------------------------------------------------

        local_sha = run_git(
            [
                "rev-parse",
                "HEAD"
            ],
            cwd=repo_dir,
            env=env
        )

        if local_sha != current_sha:

            raise RuntimeError(
                "Repository changed while rollback "
                "was being prepared. Aborting."
            )


        # ----------------------------------------------------
        # Verify target commit exists on branch history
        # ----------------------------------------------------

        try:

            run_git(
                [
                    "merge-base",
                    "--is-ancestor",
                    commit_sha,
                    "HEAD"
                ],
                cwd=repo_dir,
                env=env
            )

        except RuntimeError:

            raise RuntimeError(
                f"Commit {commit_sha} is not an ancestor "
                f"of branch {branch}. Rollback aborted."
            )


        # ----------------------------------------------------
        # Configure bot identity
        # ----------------------------------------------------

        run_git(
            [
                "config",
                "user.name",
                "AWS DevOps Agent Rollback"
            ],
            cwd=repo_dir,
            env=env
        )

        run_git(
            [
                "config",
                "user.email",
                "aws-devops-agent@users.noreply.github.com"
            ],
            cwd=repo_dir,
            env=env
        )


        # ----------------------------------------------------
        # Perform SAFE GIT REVERT
        # ----------------------------------------------------

        revert_message = (
            f"Revert commit {commit_sha[:7]} "
            f"via AWS DevOps Agent"
        )

        run_git(

            [
                "revert",

                "--no-edit",

                commit_sha
            ],

            cwd=repo_dir,

            env=env
        )


        # ----------------------------------------------------
        # Get new revert SHA
        # ----------------------------------------------------

        new_sha = run_git(

            [
                "rev-parse",
                "HEAD"
            ],

            cwd=repo_dir,

            env=env
        )


        # ----------------------------------------------------
        # Push revert commit
        # ----------------------------------------------------

        run_git(

            [
                "push",

                "origin",

                branch
            ],

            cwd=repo_dir,

            env=env
        )


        return {

            "timestamp":
                timestamp(),

            "status":
                "ROLLBACK_COMPLETED",

            "repository":
                f"{owner}/{repo}",

            "branch":
                branch,

            "reverted_commit":
                commit_sha,

            "new_revert_commit":
                new_sha,

            "commit_message":
                revert_message,

            "github_url":
                f"https://github.com/"
                f"{owner}/{repo}/commit/"
                f"{new_sha}",

            "next_step":
                "GitHub Actions should trigger "
                "from the new revert commit."

        }


    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# HEALTH CHECK
# ============================================================

@mcp.tool()
def health_check():

    return {

        "status":
            "healthy",

        "service":
            "GitHub Deployment Remediation MCP",

        "time":
            timestamp()

    }


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        app,

        host="0.0.0.0",

        port=8080

    )
