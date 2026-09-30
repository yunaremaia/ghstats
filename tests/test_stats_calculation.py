"""Tests for stats calculation and formatting helpers (issue #28)."""

import pytest

from ghstats.cli import _comparison_metrics, _format_date, _format_number
from ghstats.fetcher import UserStats


# --- _format_number ---


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0"),
        (7, "7"),
        (999, "999"),
        (1_000, "1.0k"),
        (1_500, "1.5k"),
        (1_000_000, "1.0M"),
        (2_500_000, "2.5M"),
    ],
)
def test_format_number(value, expected):
    assert _format_number(value) == expected


# --- _format_date ---


def test_format_date_iso_with_z_suffix():
    assert _format_date("2026-09-15T10:30:00Z") == "2026-09-15"


def test_format_date_iso_with_offset():
    assert _format_date("2026-09-15T23:59:59+02:00") == "2026-09-15"


def test_format_date_empty_string_returns_dash():
    assert _format_date("") == "—"


def test_format_date_invalid_string_falls_back_to_first_ten_chars():
    assert _format_date("not-a-date-at-all") == "not-a-date"


# --- _comparison_metrics ---


def _full_user() -> UserStats:
    stats = UserStats(login="octocat", followers=120, following=8, public_repos=15)
    stats.contributions.total_contributions = 842
    stats.pull_requests.total_opened = 40
    stats.pull_requests.total_merged = 31
    stats.issues.total_opened = 12
    return stats


def test_comparison_metrics_returns_all_totals():
    assert _comparison_metrics(_full_user()) == {
        "Followers": 120,
        "Following": 8,
        "Public Repos": 15,
        "Contributions": 842,
        "PRs Opened": 40,
        "PRs Merged": 31,
        "Issues Opened": 12,
    }


def test_comparison_metrics_new_user_is_all_zeros():
    metrics = _comparison_metrics(UserStats(login="newbie"))
    assert set(metrics.values()) == {0}
    assert len(metrics) == 7


def test_comparison_metrics_no_contributions_counts_as_zero():
    stats = _full_user()
    stats.contributions = None
    assert _comparison_metrics(stats)["Contributions"] == 0


def test_comparison_metrics_missing_pr_and_issue_stats_count_as_zero():
    stats = _full_user()
    stats.pull_requests = None
    stats.issues = None
    metrics = _comparison_metrics(stats)
    assert metrics["PRs Opened"] == 0
    assert metrics["PRs Merged"] == 0
    assert metrics["Issues Opened"] == 0


def test_comparison_metrics_none_totals_count_as_zero():
    stats = _full_user()
    stats.followers = None
    stats.contributions.total_contributions = None
    metrics = _comparison_metrics(stats)
    assert metrics["Followers"] == 0
    assert metrics["Contributions"] == 0
    assert metrics["Following"] == 8
