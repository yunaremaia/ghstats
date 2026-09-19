"""Tests for error handling in ghstats fetcher."""
import pytest
from unittest.mock import patch, MagicMock

from ghstats.fetcher import StatsFetcher, GHRuntimeError


class TestGHRuntimeError:
    """Test the custom runtime error."""
    def test_error_creation(self):
        err = GHRuntimeError("test error message")
        assert str(err) == "test error message"


class TestRunGHErrorHandling:
    """Test that _run_gh properly raises errors instead of swallowing them."""
    
    @pytest.fixture
    def fetcher(self):
        return StatsFetcher("testuser")
    
    @patch("ghstats.fetcher.subprocess.run")
    def test_gh_not_installed(self, mock_run, fetcher):
        """Test that FileNotFoundError is wrapped in GHRuntimeError when gh is not installed."""
        import subprocess
        
        mock_run.side_effect = FileNotFoundError("gh: command not found")
        
        with pytest.raises(GHRuntimeError, match="gh CLI not found"):
            fetcher._run_gh(["users", "testuser"])
    
    @patch("ghstats.fetcher.subprocess.run")
    def test_gh_not_authenticated(self, mock_run, fetcher):
        """Test that 401 errors are raised when gh is not authenticated."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="401 Authentication failed",
        )
        
        with pytest.raises(GHRuntimeError, match="401 Authentication"):
            fetcher._run_gh(["users", "testuser"])
    
    @patch("ghstats.fetcher.subprocess.run")
    def test_gh_api_error(self, mock_run, fetcher):
        """Test that non-zero exit codes with stderr are raised."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="API rate limit exceeded",
        )
        
        with pytest.raises(GHRuntimeError, match="API rate limit exceeded"):
            fetcher._run_gh(["graphql", "-f", "query={test}"])
    
    @patch("ghstats.fetcher.subprocess.run")
    def test_gh_timeout(self, mock_run, fetcher):
        """Test that timeout errors are raised."""
        from subprocess import TimeoutExpired
        
        mock_run.side_effect = TimeoutExpired("gh", 30)
        
        with pytest.raises(GHRuntimeError, match="timed out after 30 seconds"):
            fetcher._run_gh(["users", "testuser"])
    
    @patch("ghstats.fetcher.subprocess.run")
    def test_gh_json_decode_error(self, mock_run, fetcher):
        """Test that JSON decode errors are raised."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="invalid json {",
            stderr="",
        )
        
        with pytest.raises(GHRuntimeError, match="Failed to parse gh CLI JSON output"):
            fetcher._run_gh(["users", "testuser", "--json"])
    
    @patch("ghstats.fetcher.subprocess.run")
    def test_authenticated_call_succeeds(self, mock_run, fetcher):
        """Test that successful authenticated calls work."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"login": "testuser", "name": "Test User"}',
            stderr="",
        )
        
        result = fetcher._run_gh(["users", "testuser"])
        
        assert result == {"login": "testuser", "name": "Test User"}
