"""Tests for ghstats CLI commands."""

from click.testing import CliRunner

from ghstats.cli import _comparison_rows, cli
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


def test_comparison_rows_empty_list():
    assert _comparison_rows([]) == []


def test_comparison_rows_missing_and_mismatched_fields():
    user_a = UserStats(login="alice", followers=10)
    user_a.pull_requests = None  # type: ignore[assignment]
    user_a.contributions = None  # type: ignore[assignment]
    user_a.issues = None  # type: ignore[assignment]

    user_b = _user("bob", followers=5, contributions=20)

    rows = _comparison_rows([user_a, user_b])
    row_dict = {name: (vals, winners) for name, vals, winners in rows}

    assert "Followers" in row_dict
    assert row_dict["Followers"] == ([10, 5], ["alice"])

    assert "Contributions" in row_dict
    assert row_dict["Contributions"] == ([0, 20], ["bob"])

    assert "PRs Opened" in row_dict
    assert row_dict["PRs Opened"] == ([0, 1], ["bob"])


def test_comparison_rows_both_missing_or_default():
    user_a = UserStats(login="alice")
    user_b = UserStats(login="bob")
    rows = _comparison_rows([user_a, user_b])
    for _metric_name, values, winners in rows:
        assert values == [0, 0]
        assert winners == ["alice", "bob"]


def test_compare_cli_with_partial_stats(monkeypatch):
    user_a = UserStats(login="alice", followers=15)
    user_a.pull_requests = None  # type: ignore[assignment]
    user_a.contributions = None  # type: ignore[assignment]
    user_a.issues = None  # type: ignore[assignment]

    user_b = _user("bob", followers=10, contributions=50)

    users = {"alice": user_a, "bob": user_b}
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_stats",
        lambda fetcher: users[fetcher.username],
    )

    result = CliRunner().invoke(cli, ["compare", "alice", "bob"])
    assert result.exit_code == 0
    assert "GitHub User Comparison" in result.output
    assert "alice" in result.output
    assert "bob" in result.output
