"""Tests for ghstats fetcher."""
import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ghstats.fetcher import (
    ContributionDay,
    GHRuntimeError,
    StatsFetcher,
    UserStats,
)


def _return_stdout(mock_run):
    """gh succeeds but prints undecodable output; json.loads raises inside _run_gh."""
    mock_run.return_value = MagicMock(returncode=0, stdout="{oops", stderr="")


def _raise_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["gh", "api"], timeout=30)


def _raise_missing_binary(mock_run):
    mock_run.side_effect = FileNotFoundError(2, "No such file or directory", "gh")


class TestContributionDay:
    def test_creation(self):
        day = ContributionDay(date="2026-01-01", count=5, color="#216e39")
        assert day.date == "2026-01-01"
        assert day.count == 5


class TestUserStats:
    def test_defaults(self):
        stats = UserStats()
        assert stats.login == ""
        assert stats.contributions.total_contributions == 0
        assert stats.pull_requests.total_opened == 0
        assert stats.issues.total_opened == 0


class TestStatsFetcher:
    @pytest.fixture
    def fetcher(self):
        return StatsFetcher("yunaremaia")

    def test_init(self, fetcher):
        assert fetcher.username == "yunaremaia"

    def test_init_empty(self):
        f = StatsFetcher("")
        assert f.username == ""

    @patch("ghstats.fetcher.subprocess.run")
    def test_fetch_user_stats(self, mock_run, fetcher):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"name": "Yunaremaia", "followers": {"totalCount": 10}, "following": {"totalCount": 5}}',
            stderr="",
        )
        stats = fetcher.fetch_user_stats()
        assert stats.login == "yunaremaia"
        assert isinstance(stats, UserStats)

    @patch("ghstats.fetcher.subprocess.run")
    def test_fetch_repo_stats(self, mock_run, fetcher):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"stargazers_count": 100, "forks_count": 20}',
            stderr="",
        )
        stats = fetcher.fetch_repo_stats("owner/repo")
        assert isinstance(stats, dict)

    @pytest.mark.parametrize(
        "configure,cause_type,cause_check",
        [
            # The decode position is the whole point of chaining this arm: the
            # GHRuntimeError message embeds it, but only the cause keeps it typed.
            (_return_stdout, json.JSONDecodeError,
             lambda e: e.pos == 1 and "line 1 column" in str(e)),
            (_raise_timeout, subprocess.TimeoutExpired,
             lambda e: e.timeout == 30),
            (_raise_missing_binary, FileNotFoundError,
             lambda e: e.filename == "gh"),
        ],
        ids=["invalid-json", "timeout", "gh-missing"],
    )
    @patch("ghstats.fetcher.subprocess.run")
    def test_run_gh_chains_the_original_cause(self, mock_run, fetcher, configure,
                                             cause_type, cause_check):
        """Each GHRuntimeError must keep the exception that caused it as __cause__.

        The messages are deliberately uninformative ("gh command timed out after
        30s", a fixed install hint), so the diagnostics that actually identify the
        failure -- the JSON decode position, TimeoutExpired.cmd/.timeout,
        FileNotFoundError.filename -- survive only on the chained cause. Without
        `raise ... from` those attributes are lost and the traceback degrades to
        "During handling of the above exception, another exception occurred".
        """
        configure(mock_run)

        with pytest.raises(GHRuntimeError) as excinfo:
            fetcher._run_gh(["user"])

        assert type(excinfo.value.__cause__) is cause_type, (
            f"__cause__ is {excinfo.value.__cause__!r}, expected {cause_type.__name__}"
        )
        assert cause_check(excinfo.value.__cause__)
