"""GitHub Stats fetcher using GraphQL API."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterator


@dataclass
class ContributionDay:
    """A single day of contributions."""
    date: str
    count: int
    color: str = ""


@dataclass
class ContributionCalendar:
    """Full contribution calendar."""
    total_contributions: int = 0
    weeks: list[list[ContributionDay]] = field(default_factory=list)


@dataclass
class PullRequestStats:
    """Pull request statistics."""
    total_opened: int = 0
    total_merged: int = 0
    total_closed: int = 0
    total_review_requests: int = 0
    total_reviews: int = 0
    repos: list[str] = field(default_factory=list)


@dataclass
class IssueStats:
    """Issue statistics."""
    total_opened: int = 0
    total_closed: int = 0
    total_commented: int = 0


@dataclass
class UserStats:
    """Complete user stats."""
    login: str = ""
    name: str = ""
    followers: int = 0
    following: int = 0
    stars_received: int = 0
    public_repos: int = 0
    contributions: ContributionCalendar = field(default_factory=ContributionCalendar)
    pull_requests: PullRequestStats = field(default_factory=PullRequestStats)
    issues: IssueStats = field(default_factory=IssueStats)
    total_commits: int = 0


class StatsFetcher:
    """Fetch GitHub stats using gh CLI."""

    def __init__(self, username: str):
        self.username = username

    def _run_gh(self, args: list[str]) -> dict | list:
        """Run gh CLI and return JSON output."""
        cmd = ["gh", "api"] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {} if "--json" in args else []
            return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            return {} if "--json" in args else []

    def fetch_user_stats(self) -> UserStats:
        """Fetch comprehensive user stats."""
        stats = UserStats(login=self.username)

        # Basic user info
        user_data = self._run_gh(["users", self.username])
        if user_data:
            stats.name = user_data.get("name", "")
            stats.followers = user_data.get("followers", {}).get("totalCount", 0)
            stats.following = user_data.get("following", {}).get("totalCount", 0)
            stats.public_repos = user_data.get("repositories", {}).get("totalCount", 0)
            stats.stars_received = user_data.get("repositories", {}).get("totalCount", 0)

        # Contribution calendar
        contrib_data = self._run_gh([
            "graphql",
            "-f", f"query={{ user(login: \"{self.username}\") {{ contributionsCollection {{ contributionCalendar {{ totalContributions weeks {{ contributionDays {{ date contributionCount color }} }} }} }} }} }}",
        ])
        if contrib_data and "data" in contrib_data:
            cal = contrib_data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            stats.contributions.total_contributions = cal.get("totalContributions", 0)
            for week in cal.get("weeks", []):
                week_days = []
                for day in week.get("contributionDays", []):
                    week_days.append(ContributionDay(
                        date=day.get("date", ""),
                        count=day.get("contributionCount", 0),
                        color=day.get("color", ""),
                    ))
                stats.contributions.weeks.append(week_days)

        # PR stats
        search_prs = self._run_gh([
            "search",
            "issues",
            f"author:{self.username} type:pr",
            "--limit", "1",
        ])
        if isinstance(search_prs, dict):
            stats.pull_requests.total_opened = search_prs.get("total_count", 0)

        merged_prs = self._run_gh([
            "search",
            "issues",
            f"author:{self.username} type:pr is:merged",
            "--limit", "1",
        ])
        if isinstance(merged_prs, dict):
            stats.pull_requests.total_merged = merged_prs.get("total_count", 0)

        # Issue stats
        opened_issues = self._run_gh([
            "search",
            "issues",
            f"author:{self.username} type:issue",
            "--limit", "1",
        ])
        if isinstance(opened_issues, dict):
            stats.issues.total_opened = opened_issues.get("total_count", 0)

        return stats

    def fetch_repo_stats(self, repo: str) -> dict:
        """Fetch stats for a specific repo."""
        repo_data = self._run_gh(["repos", repo])
        if not repo_data:
            return {}

        return {
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "watchers": repo_data.get("watchers_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "language": repo_data.get("language", ""),
            "description": repo_data.get("description", ""),
            "created_at": repo_data.get("created_at", ""),
            "updated_at": repo_data.get("updated_at", ""),
        }

    def fetch_user_repos(self, limit: int = 30) -> list[dict]:
        """Fetch user's public repos."""
        repos = []
        page = 1
        while len(repos) < limit:
            per_page = min(100, limit - len(repos))
            data = self._run_gh([
                f"users/{self.username}/repos",
                "--paginate",
                f"--per-page={per_page}",
            ])
            if not data or not isinstance(data, list):
                break
            for r in data:
                if not r.get("fork", False):
                    repos.append({
                        "name": r.get("name", ""),
                        "full_name": r.get("full_name", ""),
                        "stars": r.get("stargazers_count", 0),
                        "forks": r.get("forks_count", 0),
                        "language": r.get("language", ""),
                        "description": r.get("description", ""),
                        "updated_at": r.get("updated_at", ""),
                    })
            if len(data) < per_page:
                break
        return repos[:limit]

    def fetch_contribution_history(self, days: int = 30) -> list[dict]:
        """Fetch recent contribution activity."""
        activities = []
        since = (datetime.now() - timedelta(days=days)).isoformat() + "Z"

        # Fetch recent PRs
        prs = self._run_gh([
            "search",
            "issues",
            f"author:{self.username} type:pr updated:>={since}",
            "--sort", "updated",
            "--order", "desc",
            "--limit", "30",
            "--json", "number,title,repository,state,mergedAt,updatedAt,url",
        ])
        if isinstance(prs, list):
            for pr in prs:
                repo = pr.get("repository", {}).get("nameWithOwner", "")
                activities.append({
                    "type": "pr",
                    "title": pr.get("title", ""),
                    "repo": repo,
                    "state": "merged" if pr.get("mergedAt") else pr.get("state", "").lower(),
                    "date": pr.get("updatedAt", ""),
                    "url": pr.get("url", ""),
                })

        # Sort by date
        activities.sort(key=lambda x: x.get("date", ""), reverse=True)
        return activities[:50]
