"""Tests for ghstats fetcher."""
import pytest
from unittest.mock import patch, MagicMock

from ghstats.fetcher import (
    StatsFetcher, UserStats, ContributionCalendar,
    PullRequestStats, IssueStats, ContributionDay
)


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
