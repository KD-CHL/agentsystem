#!/usr/bin/env python3
"""Sync local AgentSystem data to the cloud data repository.

The Vercel serverless layer (frontend/api/) serves a read-only snapshot of the
local workspace. This script reads the local SQLite database through the very
same API routes the frontend uses (via TestClient, dev auth mode), which
guarantees byte-identical response shapes, and pushes one JSON snapshot to the
private data repo (default KD-CHL/agentsystem-data) via the GitHub Contents
API. The serverless layer reads it under the key 'agentsystem:cloud_data'.

Run from the project root:
    .venv/bin/python scripts/sync_cloud_data.py [--token PAT] [--dry-run]

The GitHub token is resolved in order: --token, $GITHUB_DATA_TOKEN,
macOS keychain (internet password for github.com).
Honors $https_proxy / $HTTPS_PROXY (urllib reads them automatically).

Excluded by design: users (the cloud layer manages its own), file contents
(only directory trees are synced), and anything secret-bearing (credential
records are metadata-only, enforced by the API itself).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

API_BASE = os.environ.get("GITHUB_API_BASE", "https://api.github.com")
OWNER = os.environ.get("GITHUB_DATA_OWNER", "KD-CHL")
REPO = os.environ.get("GITHUB_DATA_REPO", "agentsystem-data")
BRANCH = os.environ.get("GITHUB_DATA_BRANCH", "main")
FILE_PATH = "agentsystem-cloud_data.json"  # must match key 'agentsystem:cloud_data' in frontend/api/lib/data-store.js
MAX_TASKS = 200
MAX_AUDIT_LOGS = 500
MAX_PROJECT_FILES = 5000


def resolve_token(cli_token: str | None) -> str:
    if cli_token:
        return cli_token
    env_token = os.environ.get("GITHUB_DATA_TOKEN")
    if env_token:
        return env_token
    try:
        result = subprocess.run(
            ["security", "find-internet-password", "-s", "github.com", "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
        token = result.stdout.strip()
        if token:
            return token
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    raise SystemExit(
        "No GitHub token available. Pass --token, set GITHUB_DATA_TOKEN, "
        "or store a PAT as the github.com internet password in the macOS keychain."
    )


def gh_request(token: str, method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", "agentsystem-sync")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read() or b"null")
        except json.JSONDecodeError:
            payload = None
        return exc.code, payload


def build_snapshot() -> dict:
    from fastapi.testclient import TestClient

    from agentsystem.api import create_app
    from agentsystem.container import AppContainer

    # Dev auth mode exposes every read endpoint without a login; the container
    # loads the SQLite database read-only into its write-through cache.
    container = AppContainer(persistent=True)
    client = TestClient(create_app(container))

    def get_json(path: str):
        response = client.get(path)
        response.raise_for_status()
        return response.json()

    print("Reading tasks...")
    tasks = get_json(f"/api/v1/tasks?limit={MAX_TASKS}")
    task_views: dict[str, object] = {}
    task_messages: dict[str, object] = {}
    task_agents: dict[str, object] = {}
    traces: dict[str, object] = {}
    for task in tasks:
        task_id = task["id"]
        trace_id = task.get("trace_id")
        task_views[task_id] = get_json(f"/api/v1/tasks/{task_id}")
        task_messages[task_id] = get_json(f"/api/v1/tasks/{task_id}/messages")
        task_agents[task_id] = get_json(f"/api/v1/agents?task_id={task_id}")
        if trace_id and trace_id not in traces:
            response = client.get(f"/api/v1/traces/{trace_id}")
            if response.status_code == 200:
                traces[trace_id] = response.json()
    print(f"  {len(tasks)} tasks, {len(traces)} traces")

    print("Reading projects...")
    projects = get_json("/api/v1/projects")
    project_files: dict[str, list] = {}
    for project in projects:
        collected: list[object] = []
        queue = [""]
        while queue and len(collected) < MAX_PROJECT_FILES:
            dir_path = queue.pop(0)
            entries = get_json(
                f"/api/v1/projects/{project['id']}/files?path={urllib.parse.quote(dir_path)}"
            )
            for entry in entries:
                collected.append(entry)
                if entry.get("kind") == "directory":
                    queue.append(entry["path"])
        project_files[project["id"]] = collected[:MAX_PROJECT_FILES]
    print(f"  {len(projects)} projects")

    print("Reading agents and capabilities...")
    agents = get_json("/api/v1/agents")
    agent_capabilities: dict[str, object] = {}
    for agent in agents:
        name = agent["agent_name"]
        response = client.get(f"/api/v1/agents/{name}/capabilities")
        if response.status_code == 200:
            agent_capabilities[name] = response.json()

    print("Reading operations, approvals, audit logs...")
    approvals = get_json("/api/v1/approvals")
    operations_summary = get_json("/api/v1/operations/summary")
    audit_logs: list[object] = []
    page_size = 200  # endpoint caps limit at le=200
    while len(audit_logs) < MAX_AUDIT_LOGS:
        page = get_json(f"/api/v1/audit-logs?limit={page_size}&offset={len(audit_logs)}")
        audit_logs.extend(page)
        if len(page) < page_size:
            break
    audit_logs = audit_logs[:MAX_AUDIT_LOGS]
    collaboration_rules = get_json("/api/v1/collaboration/rules")
    capability_policy = get_json("/api/v1/capabilities/policy")
    mcp_servers = get_json("/api/v1/mcp-servers")
    skills = get_json("/api/v1/skills")
    credentials = get_json("/api/v1/credentials")
    model_providers = get_json("/api/v1/model-providers")
    system_info = get_json("/api/v1/system")

    return {
        "tasks": tasks,
        "task_views": task_views,
        "task_messages": task_messages,
        "task_agents": task_agents,
        "agents": agents,
        "approvals": approvals,
        "projects": projects,
        "project_files": project_files,
        "operations_summary": operations_summary,
        "audit_logs": audit_logs,
        "traces": traces,
        "collaboration_rules": collaboration_rules,
        "mcp_servers": mcp_servers,
        "skills": skills,
        "capability_policy": capability_policy,
        "agent_capabilities": agent_capabilities,
        "credentials": credentials,
        "model_providers": model_providers,
        "system": system_info,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def push_snapshot(token: str, snapshot: dict, dry_run: bool = False) -> None:
    payload = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    size_kb = len(payload.encode("utf-8")) / 1024
    print(f"Snapshot size: {size_kb:.1f} KB")
    if dry_run:
        print("Dry run — not pushing.")
        return

    contents_path = f"/repos/{OWNER}/{REPO}/contents/{FILE_PATH}"
    status, current = gh_request(token, "GET", f"{contents_path}?ref={BRANCH}")
    body = {
        "message": f"chore(data): sync snapshot {snapshot['synced_at']}",
        "content": base64.b64encode(payload.encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
    }
    if status == 200 and isinstance(current, dict) and current.get("sha"):
        body["sha"] = current["sha"]  # required for updates
    elif status != 404:
        raise SystemExit(f"Failed to read current snapshot (HTTP {status}): {current}")

    status, result = gh_request(token, "PUT", contents_path, body)
    if status not in (200, 201):
        raise SystemExit(f"Snapshot push failed (HTTP {status}): {result}")
    print(f"Pushed snapshot to {OWNER}/{REPO}/{FILE_PATH} ({BRANCH})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", help="GitHub PAT (defaults to $GITHUB_DATA_TOKEN or keychain)")
    parser.add_argument("--dry-run", action="store_true", help="Build the snapshot but do not push")
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)  # settings.database_url is relative (data/agentsystem.db)
    token = resolve_token(args.token)
    snapshot = build_snapshot()
    push_snapshot(token, snapshot, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
