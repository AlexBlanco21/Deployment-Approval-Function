"""
Shared modules for GitHub Actions approval automation.

This package contains the GitHub API client and approval validator.
"""

from .github_client import GitHubClient
from .approval_validator import ApprovalValidator

__all__ = ["GitHubClient", "ApprovalValidator"]
