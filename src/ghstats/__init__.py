"""ghstats — GitHub Stats Dashboard."""
from importlib.metadata import PackageNotFoundError, version as _metadata_version

from ghstats.fetcher import (
    ContributionCalendar,
    IssueStats,
    PullRequestStats,
    StatsFetcher,
    UserStats,
)

try:
    __version__ = _metadata_version("ghstats-py")
except PackageNotFoundError:  # running from a source checkout, not an install
    __version__ = "0.0.0.dev0"

__all__ = ["ContributionCalendar", "IssueStats", "PullRequestStats", "StatsFetcher", "UserStats"]
