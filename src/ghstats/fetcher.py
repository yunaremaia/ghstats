"""GitHub Stats fetcher using GraphQL API."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


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


class GHRuntimeError(RuntimeError):
    """Raised when gh CLI is missing or unauthenticated."""


# GitHub caps a REST page at 100 items; the repo walk below always asks for
# whole pages and trims the result, and REST search rejects anything larger.
_MAX_PER_PAGE = 100
# Slack room on top of ceil(limit / 100) for users whose pages are mostly forks.
_MAX_REPO_PAGES = 2


def _repo_name_from_url(api_url: str) -> str:
    """Turn a REST ``repository_url`` into an ``owner/name`` slug.

    ``https://api.github.com/repos/owner/name`` -> ``owner/name``.
    """
    marker = "/repos/"
    index = api_url.find(marker)
    if index == -1:
        return ""
    return api_url[index + len(marker):].strip("/")


class StatsFetcher:
    """Fetch GitHub stats using gh CLI."""

    def __init__(self, username: str):
        self.username = username

    def _run_gh(self, args: list[str]) -> dict | list:
        """Run gh CLI and return JSON output.

        Raises:
            GHRuntimeError: If gh is missing, unauthenticated, or the query fails.
        """
        cmd = ["gh", "api"] + args
        try:
            # Return codes are inspected explicitly below to map gh's stderr onto
            # GHRuntimeError, so check=False preserves that handling.
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
            if result.returncode != 0:
                stderr = result.stderr.strip()
                if "authentication" in stderr.lower() or "401" in stderr:
                    raise GHRuntimeError(
                        "GitHub CLI not authenticated. Run `gh auth login` or set GH_TOKEN env var.\n"
                        f"Original error: {stderr}"
                    )
                if "not found" in stderr.lower():
                    raise GHRuntimeError(
                        f"Resource not found.\nOriginal error: {stderr}"
                    )
                raise GHRuntimeError(
                    f"gh api failed with exit code {result.returncode}.\n"
                    f"stderr: {stderr}"
                )
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                # `from e`: the decode position (line/column of stdout) is the
                # actual diagnosis, and GHRuntimeError is a public error callers
                # may inspect, so the cause must stay reachable as __cause__.
                raise GHRuntimeError(
                    f"Invalid JSON from gh: {e}\nstdout: {result.stdout[:500]}"
                ) from e
        except subprocess.TimeoutExpired as e:
            # `from e`: the message cannot name the command, but TimeoutExpired
            # carries .cmd and .timeout. Which gh call hung is the first thing a
            # production traceback has to answer.
            raise GHRuntimeError("gh command timed out after 30s") from e
        except FileNotFoundError as e:
            # `from e`: FileNotFoundError.filename distinguishes "gh is not
            # installed" from "gh is installed but not on PATH / broken symlink",
            # which the fixed message above cannot express.
            raise GHRuntimeError(
                "gh CLI not found. Install from https://cli.github.com/") from e

    def _search_issues(
        self,
        query: str,
        per_page: int = 1,
        sort: str = "",
        order: str = "",
    ) -> dict:
        """Run a REST search query and return the whole response envelope.

        ``gh search issues`` is a separate subcommand with its own flags, so it
        cannot be routed through :meth:`_run_gh`, which always prepends
        ``gh api``. The REST endpoint ``search/issues`` is reachable via
        ``gh api`` and returns ``total_count`` plus ``items``, which is what the
        callers need. ``-X GET`` is required: without it ``gh api`` switches to
        POST as soon as ``-f`` parameters are present.

        Args:
            query: Search query string, e.g. ``author:octocat type:pr``.
            per_page: Page size, capped at the API maximum of 100.
            sort: Optional sort field, e.g. ``updated``.
            order: Optional sort direction, ``asc`` or ``desc``.

        Returns:
            The decoded JSON response; ``{}`` when the payload is not an object.

        Raises:
            GHRuntimeError: If the query fails.
        """
        per_page = max(1, min(per_page, _MAX_PER_PAGE))
        args = [
            "search/issues",
            "-X", "GET",
            "-f", f"q={query}",
            "-f", f"per_page={per_page}",
        ]
        if sort:
            args += ["-f", f"sort={sort}"]
        if order:
            args += ["-f", f"order={order}"]
        result = self._run_gh(args)
        return result if isinstance(result, dict) else {}

    def fetch_user_stats(self) -> UserStats:
        """Fetch comprehensive user stats."""
        stats = UserStats(login=self.username)

        # Basic user info
        user_data = self._run_gh([f"users/{self.username}"])
        if user_data:
            stats.name = user_data.get("name") or ""
            stats.followers = user_data.get("followers") or 0
            stats.following = user_data.get("following") or 0
            stats.public_repos = user_data.get("public_repos") or 0

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
        search_prs = self._search_issues(f"author:{self.username} type:pr")
        stats.pull_requests.total_opened = search_prs.get("total_count", 0)

        merged_prs = self._search_issues(f"author:{self.username} type:pr is:merged")
        stats.pull_requests.total_merged = merged_prs.get("total_count", 0)

        # Issue stats
        opened_issues = self._search_issues(f"author:{self.username} type:issue")
        stats.issues.total_opened = opened_issues.get("total_count", 0)

        return stats

    def fetch_repo_stats(self, repo: str) -> dict:
        """Fetch stats for a specific repo."""
        repo_data = self._run_gh([f"repos/{repo}"])
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
        repos: list[dict] = []
        page = 1
        # A user can own many more repos than `limit` while only a few are
        # non-forks, so bound the number of pages instead of trusting the
        # exit condition to stop an unbounded walk.
        max_pages = max(1, -(-limit // _MAX_PER_PAGE) + _MAX_REPO_PAGES)
        while len(repos) < limit and page <= max_pages:
            per_page = min(_MAX_PER_PAGE, limit - len(repos))
            # `gh api` rejects --per-page/--paginate; paging params belong in
            # the endpoint query string.
            data = self._run_gh([
                f"users/{self.username}/repos?per_page={per_page}&page={page}",
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
            page += 1
        repos.sort(key=lambda r: r["stars"], reverse=True)
        return repos[:limit]

    def fetch_contribution_history(self, days: int = 30) -> list[dict]:
        """Fetch recent contribution activity."""
        activities: list[dict] = []
        # GitHub search only accepts a YYYY-MM-DD cutoff; a full ISO-8601
        # timestamp is rejected as a malformed query. Compute it in UTC so the
        # day boundary matches the `updated:` window we ask for.
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        # Fetch recent PRs
        results = self._search_issues(
            f"author:{self.username} type:pr updated:>={since}",
            per_page=30,
            sort="updated",
            order="desc",
        )
        items = results.get("items")
        for pr in items if isinstance(items, list) else []:
            repo = _repo_name_from_url(pr.get("repository_url", ""))
            merged_at = (pr.get("pull_request") or {}).get("merged_at")
            activities.append({
                "type": "pr",
                "title": pr.get("title", ""),
                "repo": repo,
                "state": "merged" if merged_at else pr.get("state", "").lower(),
                "date": pr.get("updated_at", ""),
                "url": pr.get("html_url", ""),
            })

        # Sort by date
        activities.sort(key=lambda x: x.get("date", ""), reverse=True)
        return activities[:50]
