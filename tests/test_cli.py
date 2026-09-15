"""Tests for ghstats CLI commands."""

from click.testing import CliRunner

from ghstats.cli import cli
from ghstats.fetcher import UserStats


def _user(login: str, followers: int, contributions: int) -> UserStats:
    stats = UserStats(login=login, followers=followers)
    stats.contributions.total_contributions = contributions
    stats.public_repos = followers // 2
    stats.pull_requests.total_opened = followers // 5
    stats.pull_requests.total_merged = followers // 10
    stats.issues.total_opened = followers // 4
    return stats


def test_compare_renders_winners(monkeypatch):
    users = {
        "alice": _user("alice", followers=12, contributions=30),
        "bob": _user("bob", followers=8, contributions=30),
    }
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_stats",
        lambda fetcher: users[fetcher.username],
    )

    result = CliRunner().invoke(cli, ["compare", "alice", "bob"])

    assert result.exit_code == 0
    assert "GitHub User Comparison" in result.output
    assert "Followers" in result.output
    assert "alice" in result.output
    assert "alice, bob" in result.output


def test_compare_json_output(monkeypatch):
    users = {
        "alice": _user("alice", followers=12, contributions=30),
        "bob": _user("bob", followers=8, contributions=20),
    }
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_stats",
        lambda fetcher: users[fetcher.username],
    )

    result = CliRunner().invoke(cli, ["compare", "alice", "bob", "--json-output"])

    assert result.exit_code == 0
    assert '"users": [' in result.output
    assert '"name": "Followers"' in result.output
    assert '"winners": [\n        "alice"' in result.output


def test_compare_requires_two_users():
    result = CliRunner().invoke(cli, ["compare", "alice"])

    assert result.exit_code != 0
    assert "between 2 and 5 usernames" in result.output
