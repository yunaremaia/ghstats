"""Regression tests for the argv handed to the gh CLI (issue #70).

``gh api`` accepts exactly one positional endpoint argument, so a REST path that
is split across several argv elements (``["users", "yunaremaia"]``) makes every
command abort with ``accepts 1 arg(s), received 2``. These tests pin the exact
argv so a regression is caught without touching the network.

The mocked payloads below are real REST shapes: ``gh api users/<login>`` returns
flat integer counters, not the nested GraphQL objects the tests used before.
"""
import json
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from ghstats.fetcher import StatsFetcher

REST_USER_PAYLOAD = {
    "name": "X",
    "followers": 57,
    "following": 6,
    "public_repos": 144,
}

GRAPHQL_PAYLOAD = {
    "data": {
        "user": {
            "contributionsCollection": {
                "contributionCalendar": {"totalContributions": 4783, "weeks": []}
            }
        }
    }
}

SEARCH_PAYLOAD = {
    "total_count": 471,
    "incomplete_results": False,
    "items": [
        {
            "title": "fix(packaging): rename distribution",
            "state": "closed",
            "updated_at": "2026-10-02T03:34:02Z",
            "html_url": "https://github.com/yunaremaia/ghstats/pull/223",
            "repository_url": "https://api.github.com/repos/yunaremaia/ghstats",
            "pull_request": {"merged_at": "2026-10-02T04:00:00Z"},
        }
    ],
}

REPO_LIST_PAYLOAD = [
    {
        "name": "ghstats",
        "full_name": "yunaremaia/ghstats",
        "fork": False,
        "stargazers_count": 1,
        "forks_count": 5,
        "language": "Python",
        "description": "GitHub Stats Dashboard",
        "updated_at": "2026-10-02T03:27:45Z",
    }
]


class RecordingRun:
    """Stand-in for ``subprocess.run`` that records argv and replies per endpoint."""

    def __init__(self, payloads):
        self.calls = []
        self.payloads = payloads

    def __call__(self, cmd, **kwargs):
        cmd = list(cmd)
        self.calls.append(cmd)
        endpoint = cmd[2] if len(cmd) > 2 else ""
        payload = self.payloads.get(endpoint.split("?")[0], {})
        return subprocess.CompletedProcess(
            cmd, 0, stdout=json.dumps(payload), stderr=""
        )

    @property
    def search_calls(self):
        return [cmd for cmd in self.calls if len(cmd) > 2 and cmd[2] == "search/issues"]

    @property
    def endpoints(self):
        return [cmd[2] if len(cmd) > 2 else "" for cmd in self.calls]

    def fields(self, cmd):
        """Decode a `gh api ... -f k=v` argv into a plain dict."""
        first = cmd.index("-f")
        out = {}
        for i in range(first, len(cmd), 2):
            key, _, value = cmd[i + 1].partition("=")
            out[key] = value
        return out

    def argv_for(self, endpoint):
        for cmd in self.calls:
            if len(cmd) > 2 and cmd[2] == endpoint:
                return cmd
        raise AssertionError(f"{endpoint!r} was never called; got {self.endpoints}")


@pytest.fixture
def fetcher():
    return StatsFetcher("yunaremaia")


class TestUserStatsArgv:
    def test_user_endpoint_is_one_argv_element(self, fetcher, monkeypatch):
        """``gh api users <login>`` is rejected; the path must be a single argv."""
        run = RecordingRun(
            {"users/yunaremaia": REST_USER_PAYLOAD, "graphql": GRAPHQL_PAYLOAD}
        )
        monkeypatch.setattr(subprocess, "run", run)

        fetcher.fetch_user_stats()

        assert run.argv_for("users/yunaremaia") == ["gh", "api", "users/yunaremaia"]

    def test_rest_user_payload_parses_to_integers(self, fetcher, monkeypatch):
        """The REST payload has flat counters; they must land as ints on UserStats."""
        run = RecordingRun(
            {"users/yunaremaia": REST_USER_PAYLOAD, "graphql": GRAPHQL_PAYLOAD}
        )
        monkeypatch.setattr(subprocess, "run", run)

        stats = fetcher.fetch_user_stats()

        assert stats.login == "yunaremaia"
        assert stats.name == "X"
        assert stats.followers == 57
        assert stats.following == 6
        assert stats.public_repos == 144
        assert stats.contributions.total_contributions == 4783
        assert isinstance(stats.followers, int)
        assert isinstance(stats.public_repos, int)


class TestSearchArgv:
    def test_counts_come_from_the_api_search_endpoint(self, fetcher, monkeypatch):
        """`gh api search issues` is not a thing: the REST path is `search/issues`."""
        run = RecordingRun(
            {"users/yunaremaia": REST_USER_PAYLOAD, "graphql": GRAPHQL_PAYLOAD,
             "search/issues": SEARCH_PAYLOAD}
        )
        monkeypatch.setattr(subprocess, "run", run)

        stats = fetcher.fetch_user_stats()

        assert stats.pull_requests.total_opened == 471
        assert stats.pull_requests.total_merged == 471
        assert stats.issues.total_opened == 471
        assert len(run.search_calls) == 3, run.calls
        for cmd in run.search_calls:
            assert cmd[:3] == ["gh", "api", "search/issues"], cmd
            assert "-X" in cmd and cmd[cmd.index("-X") + 1] == "GET", cmd
            assert not any(arg.startswith("--limit") for arg in cmd), cmd

    def test_search_queries_keep_the_expected_qualifiers(self, fetcher, monkeypatch):
        run = RecordingRun(
            {"users/yunaremaia": REST_USER_PAYLOAD, "graphql": GRAPHQL_PAYLOAD,
             "search/issues": SEARCH_PAYLOAD}
        )
        monkeypatch.setattr(subprocess, "run", run)

        fetcher.fetch_user_stats()

        queries = [cmd[cmd.index("-f") + 1] for cmd in run.search_calls]
        assert queries == [
            "q=author:yunaremaia type:pr",
            "q=author:yunaremaia type:pr is:merged",
            "q=author:yunaremaia type:issue",
        ]


class TestActivityArgv:
    def test_recent_prs_use_the_api_search_endpoint(self, fetcher, monkeypatch):
        run = RecordingRun({"search/issues": SEARCH_PAYLOAD})
        monkeypatch.setattr(subprocess, "run", run)

        activities = fetcher.fetch_contribution_history(days=7)

        cmd = run.argv_for("search/issues")
        assert cmd[:3] == ["gh", "api", "search/issues"]
        fields = run.fields(cmd)
        assert "author:yunaremaia" in fields["q"]
        assert "type:pr" in fields["q"]
        assert fields["per_page"] == "30"
        assert fields["sort"] == "updated"
        assert fields["order"] == "desc"
        assert activities[0]["repo"] == "yunaremaia/ghstats"
        assert activities[0]["state"] == "merged"
        assert activities[0]["url"] == "https://github.com/yunaremaia/ghstats/pull/223"

    def test_since_qualifier_is_a_date_gh_search_accepts(self, fetcher, monkeypatch):
        """`updated:>=2026-10-02T03:42:05+00:00Z` is rejected; only YYYY-MM-DD works."""
        run = RecordingRun({"search/issues": SEARCH_PAYLOAD})
        monkeypatch.setattr(subprocess, "run", run)

        fetcher.fetch_contribution_history(days=7)

        expected = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        cmd = run.argv_for("search/issues")
        query = cmd[cmd.index("-f") + 1]
        assert query == f"q=author:yunaremaia type:pr updated:>={expected}"


class TestRepoArgv:
    def test_repo_endpoint_is_one_argv_element(self, monkeypatch):
        run = RecordingRun(
            {"repos/yunaremaia/ghstats": {"stargazers_count": 1, "forks_count": 5}}
        )
        monkeypatch.setattr(subprocess, "run", run)

        stats = StatsFetcher("").fetch_repo_stats("yunaremaia/ghstats")

        assert run.calls[0] == ["gh", "api", "repos/yunaremaia/ghstats"]
        assert stats["stars"] == 1
        assert stats["forks"] == 5

    def test_repo_listing_pages_via_query_params(self, fetcher, monkeypatch):
        """`gh api` has no --per-page flag; paging belongs in the endpoint query."""
        run = RecordingRun({"users/yunaremaia/repos": REPO_LIST_PAYLOAD})
        monkeypatch.setattr(subprocess, "run", run)

        repos = fetcher.fetch_user_repos(limit=5)

        assert len(run.calls) == 1, run.calls
        cmd = run.calls[0]
        assert cmd[0] == "gh" and cmd[1] == "api"
        assert cmd[2].startswith("users/yunaremaia/repos?")
        assert "per_page=5" in cmd[2] and "page=1" in cmd[2]
        assert not any(arg.startswith("--per-page") for arg in cmd), cmd
        assert not any(arg.startswith("--paginate") for arg in cmd), cmd
        assert repos[0]["full_name"] == "yunaremaia/ghstats"

    def test_repo_listing_pagination_stable_per_page(self, fetcher, monkeypatch):
        """Paging must maintain a constant per_page so offsets advance monotonically (issue #81)."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(list(cmd))
            endpoint = cmd[2]
            if "page=1" in endpoint:
                # Page 1 returns 2 repos (1 fork, 1 non-fork)
                page_data = [
                    {"name": "fork1", "full_name": "yunaremaia/fork1", "fork": True, "stargazers_count": 0},
                    {"name": "repo1", "full_name": "yunaremaia/repo1", "fork": False, "stargazers_count": 5},
                ]
            else:
                # Page 2 returns 2 repos (both non-forks)
                page_data = [
                    {"name": "repo2", "full_name": "yunaremaia/repo2", "fork": False, "stargazers_count": 10},
                    {"name": "repo3", "full_name": "yunaremaia/repo3", "fork": False, "stargazers_count": 2},
                ]
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(page_data), stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        repos = fetcher.fetch_user_repos(limit=2)

        assert len(calls) == 2
        # Both pages must request per_page=2 without shrinking to per_page=1 on page 2
        assert "per_page=2&page=1" in calls[0][2]
        assert "per_page=2&page=2" in calls[1][2]
        assert len(repos) == 2
        assert [r["name"] for r in repos] == ["repo2", "repo1"]