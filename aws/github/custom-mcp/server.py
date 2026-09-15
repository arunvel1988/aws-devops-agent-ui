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

API_KEY_HEADER = os.environ.get(
    "API_Key_Header",
    "X-API-Key"
)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

GITHUB_API = "https://api.github.com"


if not MCP_API_KEY:
    raise RuntimeError(
        "MCP_API_KEY environment variable missing"
    )


if not GITHUB_TOKEN:
    raise RuntimeError(
        "GITHUB_TOKEN environment variable missing"
    )


# ============================================================
# MCP API KEY AUTHENTICATION
# ============================================================

class APIKeyAuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next
    ):

        # Read configured API key header
        supplied_key = request.headers.get(
            API_KEY_HEADER
        )

        # Also support Authorization: Bearer <key>
        if not supplied_key:

            auth = request.headers.get(
                "authorization",
                ""
            )

            if auth.lower().startswith("bearer "):

                supplied_key = auth[7:]


        # Validate API key
        if (
            not supplied_key
            or not secrets.compare_digest(
                supplied_key,
                MCP_API_KEY
            )
        ):

            return JSONResponse(
                {
                    "error": "Unauthorized"
                },
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
# GITHUB API
# ============================================================

def github_headers():

    return {

        "Accept":
            "application/vnd.github+json",

        "Authorization":
            f"Bearer {GITHUB_TOKEN}",

        "X-GitHub-Api-Version":
            "2026-03-10"

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

    if not owner:

        raise ValueError(
            "owner is required"
        )


    if not repo:

        raise ValueError(
            "repo is required"
        )


    forbidden = [

        " ",

        "..",

        "/",

        "\\"

    ]


    for value in [

        owner,

        repo

    ]:

        if any(

            character in value

            for character in forbidden

        ):

            raise ValueError(

                "Invalid GitHub owner/repository name"

            )


def validate_sha(

    commit_sha: str

):

    if not commit_sha:

        raise ValueError(
            "commit_sha is required"
        )


    if len(commit_sha) != 40:

        raise ValueError(

            "commit_sha must be a full "
            "40-character SHA"

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
# GET CURRENT COMMIT
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

    validate_repo(
        owner,
        repo
    )


    data = github_get(

        f"/repos/{owner}/{repo}/commits/{branch}"

    )


    return {

        "timestamp":
            timestamp(),

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
# GET COMMIT DETAILS
# ============================================================

@mcp.tool()
def get_commit_details(

    owner: str,

    repo: str,

    commit_sha: str

) -> Dict[str, Any]:

    """
    Inspect a GitHub commit.

    Returns:
    - commit message
    - author
    - parent commits
    - changed files
    - additions
    - deletions
    """

    validate_repo(
        owner,
        repo
    )


    validate_sha(
        commit_sha
    )


    data = github_get(

        f"/repos/{owner}/{repo}/commits/{commit_sha}"

    )


    files = []


    for file in data.get(
        "files",
        []
    ):

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

        "timestamp":
            timestamp(),

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

                in data.get(
                    "parents",
                    []
                )

            ],

        "files":
            files

    }


# ============================================================
# TOOL 3
# GET GITHUB ACTIONS RUNS
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

    validate_repo(
        owner,
        repo
    )


    limit = max(

        1,

        min(
            limit,
            50
        )

    )


    params = {

        "per_page":
            limit

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

        head_commit = run.get(
            "head_commit"
        )


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

                head_commit["message"]

                if head_commit

                else "",

            "created_at":
                run["created_at"],

            "updated_at":
                run["updated_at"],

            "html_url":
                run["html_url"]

        })


    return {

        "timestamp":
            timestamp(),

        "repository":
            f"{owner}/{repo}",

        "runs":
            runs

    }


# ============================================================
# TOOL 4
# GET WORKFLOW RUN DETAILS
# ============================================================

@mcp.tool()
def get_workflow_run(

    owner: str,

    repo: str,

    run_id: int

) -> Dict[str, Any]:

    """
    Get details of a specific GitHub Actions run.
    """

    validate_repo(
        owner,
        repo
    )


    data = github_get(

        f"/repos/{owner}/{repo}/actions/runs/{run_id}"

    )


    return {

        "repository":
            f"{owner}/{repo}",

        "run_id":
            data["id"],

        "workflow":
            data["name"],

        "status":
            data["status"],

        "conclusion":
            data["conclusion"],

        "branch":
            data["head_branch"],

        "commit_sha":
            data["head_sha"],

        "event":
            data["event"],

        "created_at":
            data["created_at"],

        "updated_at":
            data["updated_at"],

        "html_url":
            data["html_url"]

    }


# ============================================================
# GIT COMMAND HELPER
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
# TOOL 5
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
    Safely rollback a specific GitHub commit.

    The tool creates a NEW Git revert commit.

    It NEVER:
    - git reset
    - git push --force
    - deletes history

    confirm must be true before execution.
    """

    validate_repo(
        owner,
        repo
    )


    validate_sha(
        commit_sha
    )


    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

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

                "Human approval is required. "

                "Call again with confirm=true."

        }


    # --------------------------------------------------------
    # GET COMMIT
    # --------------------------------------------------------

    commit = github_get(

        f"/repos/{owner}/{repo}/commits/{commit_sha}"

    )


    parents = commit.get(
        "parents",
        []
    )


    # --------------------------------------------------------
    # DO NOT AUTOMATICALLY REVERT MERGE COMMITS
    # --------------------------------------------------------

    if len(parents) != 1:

        raise RuntimeError(

            "The selected commit is a merge commit. "

            "Automatic rollback is disabled for "
            "merge commits."

        )


    # --------------------------------------------------------
    # GET CURRENT BRANCH
    # --------------------------------------------------------

    branch_data = github_get(

        f"/repos/{owner}/{repo}/commits/{branch}"

    )


    current_sha = branch_data["sha"]


    # --------------------------------------------------------
    # TEMPORARY DIRECTORY
    # --------------------------------------------------------

    temp_dir = tempfile.mkdtemp(

        prefix="github-rollback-"

    )


    try:

        repo_url = (

            f"https://github.com/"

            f"{owner}/"

            f"{repo}.git"

        )


        # ----------------------------------------------------
        # TEMPORARY GIT CREDENTIAL
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


        os.chmod(
            credential_file,
            0o600
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


        # ----------------------------------------------------
        # CONFIGURE GIT CREDENTIAL HELPER
        # ----------------------------------------------------

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
        # CLONE BRANCH
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
        # CHECK FOR RACE CONDITION
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
                "was being prepared. "

                "Rollback aborted."

            )


        # ----------------------------------------------------
        # VERIFY TARGET COMMIT IS IN BRANCH HISTORY
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

                f"Commit {commit_sha} is not an "
                f"ancestor of branch {branch}. "

                "Rollback aborted."

            )


        # ----------------------------------------------------
        # GIT IDENTITY
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
        # REVERT
        # ----------------------------------------------------

        revert_message = (

            f"Revert commit "

            f"{commit_sha[:7]} "

            f"via AWS DevOps Agent"

        )


        try:

            run_git(

                [

                    "revert",

                    "--no-edit",

                    commit_sha

                ],

                cwd=repo_dir,

                env=env

            )

        except RuntimeError:

            # Abort conflicted revert
            try:

                run_git(

                    [

                        "revert",

                        "--abort"

                    ],

                    cwd=repo_dir,

                    env=env

                )

            except Exception:

                pass


            raise RuntimeError(

                "Git revert produced conflicts. "

                "Rollback was NOT pushed. "

                "Manual conflict resolution is required."

            )


        # ----------------------------------------------------
        # GET REVERT SHA
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
        # PUSH
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


        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

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

        "authentication":
            "API key",

        "api_key_header":
            API_KEY_HEADER,

        "github":
            "configured",

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
