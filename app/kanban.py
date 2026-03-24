"""Kanban board data: fetch GitHub issues/PRs and categorize into columns."""

import json
import os
import re
import subprocess
from typing import Optional

from app.agents import get_openclaw_agents

# Repos to fetch — override with KANBAN_REPOS env var (comma-separated)
DEFAULT_REPOS = ["ddfeyes/ops-dashboard", "ddfeyes/svc-dash"]

LABEL_TAG_MAP: dict[str, str] = {
    "feature": "feat",
    "feat": "feat",
    "enhancement": "feat",
    "bug": "fix",
    "fix": "fix",
    "hotfix": "fix",
    "infrastructure": "infra",
    "infra": "infra",
    "ops": "infra",
    "chore": "chore",
    "docs": "docs",
}

ISSUE_REF_RE = re.compile(
    r"(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE
)


def _get_repos() -> list[str]:
    env = os.environ.get("KANBAN_REPOS", "")
    if env.strip():
        return [r.strip() for r in env.split(",") if r.strip()]
    return DEFAULT_REPOS


def _label_to_tag(label_name: str) -> str:
    return LABEL_TAG_MAP.get(label_name.lower(), label_name.lower())


def _run_gh(args: list[str]) -> list[dict]:
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh CLI error: {result.stderr.strip()}")
    return json.loads(result.stdout or "[]")


def _extract_issue_refs(body: Optional[str]) -> set[int]:
    if not body:
        return set()
    return {int(m) for m in ISSUE_REF_RE.findall(body)}


def _categorize_issue(
    labels: set[str],
    state: str,
    has_assignees: bool,
    linked_pr: Optional[dict],
) -> str:
    if state == "CLOSED":
        return "done"
    if "blocked" in labels:
        return "blocked"
    if linked_pr is not None:
        return "review"
    if "in-progress" in labels or "in progress" in labels or has_assignees:
        return "progress"
    return "backlog"


def _build_card(
    *,
    card_id: str,
    title: str,
    column: str,
    label_names: list[str],
    assignees: list[dict],
    pr_url: Optional[str],
    timestamp: Optional[str],
    url: str,
    agent_statuses: dict[str, str] | None = None,
) -> dict:
    tags = list({_label_to_tag(n) for n in label_names})
    agent = assignees[0]["login"] if assignees else None
    agent_status: Optional[str] = None
    if agent and agent_statuses:
        agent_status = agent_statuses.get(agent.lower())
    return {
        "id": card_id,
        "title": title,
        "column": column,
        "tags": tags,
        "pr_url": pr_url,
        "agent": agent,
        "agent_status": agent_status,
        "timestamp": timestamp,
        "url": url,
    }


def _build_agent_statuses() -> dict[str, str]:
    """Build a login→status mapping from the agents list (best-effort)."""
    try:
        agents = get_openclaw_agents()
        return {
            (a.get("id") or "").lower(): a.get("status") or "offline"
            for a in agents
            if a.get("id")
        }
    except Exception:
        return {}


def fetch_kanban_cards() -> list[dict]:
    """Fetch issues and PRs from configured repos and return kanban cards.

    Returns an empty list when gh CLI is unavailable or unauthenticated so
    that the endpoint always responds with 200 (the frontend shows an empty
    board rather than crashing).
    """
    repos = _get_repos()
    agent_statuses = _build_agent_statuses()
    cards: list[dict] = []

    for repo in repos:
        try:
            issues = _run_gh([
                "issue", "list",
                "--repo", repo,
                "--state", "all",
                "--limit", "200",
                "--json", "number,title,labels,assignees,createdAt,closedAt,url,state,body",
            ])
        except Exception:
            # gh not available or not authenticated — skip this repo
            continue

        try:
            open_prs = _run_gh([
                "pr", "list",
                "--repo", repo,
                "--state", "open",
                "--limit", "100",
                "--json", "number,title,labels,assignees,createdAt,url,state,body,isDraft,headRefName",
            ])
        except Exception:
            open_prs = []

        # Map issue number → linked open PR
        pr_by_issue: dict[int, dict] = {}
        for pr in open_prs:
            for ref in _extract_issue_refs(pr.get("body")):
                pr_by_issue[ref] = pr

        issue_numbers: set[int] = set()

        for issue in issues:
            number: int = issue["number"]
            issue_numbers.add(number)
            label_names = [lbl["name"] for lbl in issue.get("labels", [])]
            label_set = {n.lower() for n in label_names}
            assignees = issue.get("assignees", [])
            linked_pr = pr_by_issue.get(number)

            column = _categorize_issue(
                labels=label_set,
                state=issue.get("state", "OPEN"),
                has_assignees=bool(assignees),
                linked_pr=linked_pr,
            )
            timestamp = issue.get("closedAt") or issue.get("createdAt")

            cards.append(_build_card(
                card_id=f"{repo}#{number}",
                title=issue["title"],
                column=column,
                label_names=label_names,
                assignees=assignees,
                pr_url=linked_pr["url"] if linked_pr else None,
                timestamp=timestamp,
                url=issue["url"],
                agent_statuses=agent_statuses,
            ))

        # Standalone open PRs (not linked to any issue in this repo)
        for pr in open_prs:
            refs = _extract_issue_refs(pr.get("body"))
            if refs and refs.intersection(issue_numbers):
                continue  # already represented by its linked issue card
            label_names = [lbl["name"] for lbl in pr.get("labels", [])]
            assignees = pr.get("assignees", [])
            cards.append(_build_card(
                card_id=f"{repo}#pr{pr['number']}",
                title=pr["title"],
                column="review",
                label_names=label_names,
                assignees=assignees,
                pr_url=pr["url"],
                timestamp=pr.get("createdAt"),
                url=pr["url"],
                agent_statuses=agent_statuses,
            ))

    return cards
