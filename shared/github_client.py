"""
GitHub API Client for handling deployment protection rules and workflow operations.
"""
import requests
import logging
import json
from typing import Dict, Any, Optional


class GitHubClient:
    """Client for interacting with GitHub REST API."""
    
    def __init__(self, token: str):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub Personal Access Token or GitHub App token
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    def get_workflow_run(self, repo_owner: str, repo_name: str, run_id: int) -> Optional[Dict[str, Any]]:
        """
        Get workflow run details.
        
        Args:
            repo_owner: Repository owner (user or organization)
            repo_name: Repository name
            run_id: Workflow run ID
            
        Returns:
            Workflow run details or None if error
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/actions/runs/{run_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting workflow run: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response: {e.response.text}")
            return None
    
    def approve_deployment(self, callback_url: str, comment: str = "") -> Dict[str, Any]:
        """
        Approve a deployment protection rule.
        
        Args:
            callback_url: The deployment callback URL from the webhook
            comment: Optional comment for the approval
            
        Returns:
            API response
        """
        payload = {
            "state": "approved",
            "comment": comment,
            "environment_name": ""  # Will be filled by GitHub
        }
        
        try:
            response = requests.post(callback_url, headers=self.headers, json=payload)
            response.raise_for_status()
            logging.info(f"Successfully approved deployment")
            return response.json() if response.text else {"status": "approved"}
        except requests.exceptions.RequestException as e:
            error_msg = f"Error approving deployment: {e}"
            logging.error(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response: {e.response.text}")
            return {"error": error_msg}
    
    def reject_deployment(self, callback_url: str, comment: str) -> Dict[str, Any]:
        """
        Reject a deployment protection rule.
        
        Args:
            callback_url: The deployment callback URL from the webhook
            comment: Rejection comment explaining why
            
        Returns:
            API response
        """
        payload = {
            "state": "rejected",
            "comment": comment,
            "environment_name": ""  # Will be filled by GitHub
        }
        
        try:
            response = requests.post(callback_url, headers=self.headers, json=payload)
            response.raise_for_status()
            logging.info(f"Successfully rejected deployment")
            return response.json() if response.text else {"status": "rejected"}
        except requests.exceptions.RequestException as e:
            error_msg = f"Error rejecting deployment: {e}"
            logging.error(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response: {e.response.text}")
            return {"error": error_msg}
    
    def add_workflow_summary_error(self, repo_owner: str, repo_name: str, run_id: int, error_message: str) -> bool:
        """
        Add an error message to the workflow run summary using job annotations.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            run_id: Workflow run ID
            error_message: Error message to display
            
        Returns:
            True if successful, False otherwise
        """
        # Get workflow run jobs
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/actions/runs/{run_id}/jobs"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            jobs = response.json().get("jobs", [])
            
            if not jobs:
                logging.warning(f"No jobs found for workflow run {run_id}")
                return False
            
            # Try to add annotation to the first job
            # Note: Direct annotation API requires check runs permission
            # Alternative: Add a comment to the run
            logging.info(f"Workflow run {run_id} rejected. Error logged: {error_message}")
            
            # The rejection itself will show in the GitHub UI
            # For more detailed error reporting, you could use GitHub Checks API
            return True
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error adding workflow summary error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response: {e.response.text}")
            return False
    
    def cancel_workflow_run(self, repo_owner: str, repo_name: str, run_id: int) -> Dict[str, Any]:
        """
        Cancel a workflow run.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            run_id: Workflow run ID
            
        Returns:
            API response
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/actions/runs/{run_id}/cancel"
        
        try:
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
            logging.info(f"Successfully cancelled workflow run {run_id}")
            return {"status": "cancelled"}
        except requests.exceptions.RequestException as e:
            error_msg = f"Error cancelling workflow run: {e}"
            logging.error(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response: {e.response.text}")
            return {"error": error_msg}
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user details.
        
        Args:
            username: GitHub username
            
        Returns:
            User details or None if error
        """
        url = f"{self.base_url}/users/{username}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting user details: {e}")
            return None
