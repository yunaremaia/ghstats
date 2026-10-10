"""Tests for ghstats CLI commands."""

import ast
from pathlib import Path

from click.testing import CliRunner

from ghstats.cli import _comparison_rows, cli
from ghstats.fetcher import UserStats

CLI_SOURCE = Path(__file__).resolve().parent.parent / "src" / "ghstats" / "cli.py"


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
    import json
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
    parsed = json.loads(result.output)
    assert parsed["users"] == ["alice", "bob"]
    assert any(m["name"] == "Followers" for m in parsed["metrics"])


def test_stats_json_output_is_parseable(monkeypatch):
    import json
    user = _user("alice", followers=10, contributions=25)
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_stats",
        lambda self: user,
    )
    result = CliRunner().invoke(cli, ["stats", "alice", "--json-output"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["login"] == "alice"
    assert data["followers"] == 10


def test_repos_json_output_is_parseable(monkeypatch):
    import json
    repos = [{"name": "repo1", "stars": 5, "forks": 0}]
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_repos",
        lambda self, limit: repos,
    )
    result = CliRunner().invoke(cli, ["repos", "alice", "--json-output"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["name"] == "repo1"


def test_activity_json_output_is_parseable(monkeypatch):
    import json
    acts = [{"type": "pr", "title": "feat", "repo": "r", "state": "open"}]
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_contribution_history",
        lambda self, days: acts,
    )
    result = CliRunner().invoke(cli, ["activity", "alice", "--json-output"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["title"] == "feat"



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


def test_zip_calls_pass_strict_explicitly():
    """A bare zip() silently truncates to the shorter sequence.

    Every zip() in the compare path pairs a user list with a value list of the
    same length, so the truncation is invisible until a refactor makes them
    diverge — and then it drops a user from the JSON payload with no error at
    all. Requiring `strict=` turns that silent corruption into a loud failure.
    """
    tree = ast.parse(CLI_SOURCE.read_text(encoding="utf-8"), filename=str(CLI_SOURCE))
    zips = [node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "zip"]

    assert zips, "expected zip() calls in cli.py; this guard would be vacuous"
    missing = [
        f"cli.py:{node.lineno}" for node in zips
        if not any(kw.arg == "strict" for kw in node.keywords)
    ]
    assert not missing, (
        f"these zip() calls have no explicit strict=: {missing}. A bare zip() "
        "truncates to the shortest sequence, so a length mismatch between users "
        "and values would silently drop a user instead of raising."
    )


def test_compare_json_fails_loudly_when_value_lengths_diverge(monkeypatch):
    """The behavioural counterpart of the strict= check.

    `_comparison_rows` is stubbed to hand back a row with fewer values than
    there are users — exactly the shape of the future refactor that would make
    the two sequences disagree. zip(strict=True) must raise instead of quietly
    emitting a payload that is missing a user.
    """
    users = {
        "alice": _user("alice", followers=12, contributions=30),
        "bob": _user("bob", followers=8, contributions=30),
    }
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_stats",
        lambda fetcher: users[fetcher.username],
    )
    monkeypatch.setattr(
        "ghstats.cli._comparison_rows",
        lambda stats_list: [("Followers", [12], ["alice"])],
    )

    result = CliRunner().invoke(cli, ["compare", "alice", "bob", "--json-output"])

    assert isinstance(result.exception, ValueError), (
        "zip() truncated a 2-user comparison to 1 value and the command still "
        f"exited 0: {result.output!r}"
    )


def test_csv_user_export(monkeypatch, tmp_path):
    users = {
        "alice": _user("alice", followers=12, contributions=30),
    }
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_stats",
        lambda fetcher: users[fetcher.username],
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["csv", "alice"])
    assert result.exit_code == 0
    assert "metric,value" in result.output
    assert "username,alice" in result.output
    assert "followers,12" in result.output
    assert "total_contributions,30" in result.output

    # File output test
    out_file = tmp_path / "alice.csv"
    file_result = runner.invoke(cli, ["csv", "alice", "--output", str(out_file)])
    assert file_result.exit_code == 0
    assert out_file.exists()
    assert "username,alice" in out_file.read_text(encoding="utf-8")


def test_csv_compare_export(monkeypatch):
    users = {
        "alice": _user("alice", followers=12, contributions=30),
        "bob": _user("bob", followers=8, contributions=20),
    }
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_stats",
        lambda fetcher: users[fetcher.username],
    )

    result = CliRunner().invoke(cli, ["csv", "alice", "bob"])
    assert result.exit_code == 0
    lines = [line.strip() for line in result.output.strip().split("\n")]
    assert lines[0] == "metric,alice,bob"
    assert "followers,12,8" in lines
    assert "contributions,30,20" in lines


def test_markdown_report_export(monkeypatch, tmp_path):
    users = {
        "alice": _user("alice", followers=12, contributions=30),
    }
    repos = [
        {"name": "repo1", "stars": 5, "forks": 2, "language": "Python", "description": "test repo"},
    ]
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_stats",
        lambda fetcher: users[fetcher.username],
    )
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_user_repos",
        lambda fetcher, limit=10: repos,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["markdown", "alice"])
    assert result.exit_code == 0
    assert "# GitHub Stats: alice" in result.output
    assert "| Followers | 12 |" in result.output
    assert "## Top Repos" in result.output
    assert "| repo1 | 5 | 2 | Python |" in result.output

    # File output test
    out_file = tmp_path / "report.md"
    file_result = runner.invoke(cli, ["markdown", "alice", "-o", str(out_file)])
    assert file_result.exit_code == 0
    assert out_file.exists()
    assert "# GitHub Stats: alice" in out_file.read_text(encoding="utf-8")


def test_markdown_activity_export(monkeypatch):
    activities = [
        {"type": "pr", "title": "Add feature", "repo": "owner/repo", "state": "merged", "date": "2026-10-01T12:00:00Z"},
        {"type": "issue", "title": "Fix bug", "repo": "owner/repo", "state": "open", "date": "2026-10-02T12:00:00Z"},
    ]
    monkeypatch.setattr(
        "ghstats.cli.StatsFetcher.fetch_contribution_history",
        lambda fetcher, days=30: activities,
    )

    result = CliRunner().invoke(cli, ["markdown", "activity", "alice", "--days", "14"])
    assert result.exit_code == 0
    assert "# Recent Activity: @alice (last 14 days)" in result.output
    assert "| PR | Add feature | owner/repo | merged | 2026-10-01 |" in result.output
    assert "| Issue | Fix bug | owner/repo | open | 2026-10-02 |" in result.output

