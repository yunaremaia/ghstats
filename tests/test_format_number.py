"""Tests for _format_number rounding near the k/M boundary."""

import pytest

from ghstats.cli import _format_number


@pytest.mark.parametrize(
    "value, expected",
    [
        (999, "999"),
        (1_000, "1.0k"),
        (999_949, "999.9k"),
        (999_950, "1.0M"),
        (999_999, "1.0M"),
        (1_000_000, "1.0M"),
        (1_049_999, "1.0M"),
    ],
)
def test_format_number_near_boundaries(value, expected):
    assert _format_number(value) == expected


def test_format_number_never_shows_a_thousand_k():
    for value in range(999_000, 1_000_001, 7):
        assert not _format_number(value).startswith("1000")
