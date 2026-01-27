"""
Approval Validator - validates that deployments are initiated by authorized users.
"""
import logging
from typing import Dict, Any, Optional


class ApprovalValidator:
    """Validates deployment approvals based on user authorization."""
    
    def __init__(self, github_client, authorized_user: str):
        """
        Initialize the approval validator.
        
        Args:
            github_client: GitHubClient instance
            authorized_user: The authorized username to check against
        """
        self.github_client = github_client
        self.authorized_user = authorized_user
    
    def validate_deployment_user(self, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that the deployment was initiated by an authorized user.
        
        Args:
            webhook_payload: The webhook payload from GitHub
            
        Returns:
            Dictionary with validation results:
            {
                "is_valid": bool,
                "initiated_by": str,
                "run_id": int (optional),
                "details": dict (optional)
            }
        """
        try:
            # GitHub deployment_protection_rule webhook structure
            deployment = webhook_payload.get("deployment", {})
            workflow = webhook_payload.get("workflow", {})
            sender = webhook_payload.get("sender", {})
            
            # Try to get the user who triggered the workflow
            initiated_by = None
            run_id = workflow.get("id")
            
            # Method 1: Check deployment payload (contains the actor who triggered)
            if "payload" in deployment and "actor" in deployment["payload"]:
                initiated_by = deployment["payload"]["actor"]
                logging.info(f"Found initiated_by from deployment.payload.actor: {initiated_by}")
            
            # Method 2: Check workflow triggering_actor (GitHub Actions v2)
            if not initiated_by and "triggering_actor" in workflow:
                triggered_actor = workflow["triggering_actor"]
                if isinstance(triggered_actor, dict):
                    initiated_by = triggered_actor.get("login") or triggered_actor.get("name")
                else:
                    initiated_by = triggered_actor
                logging.info(f"Found initiated_by from workflow.triggering_actor: {initiated_by}")
            
            # Method 3: Check sender (the user who triggered the webhook event)
            if not initiated_by and sender:
                initiated_by = sender.get("login")
                logging.info(f"Found initiated_by from sender: {initiated_by}")
            
            # Method 4: Try to get from workflow run API
            if not initiated_by and run_id:
                repository = webhook_payload.get("repository", {})
                repo_owner = repository.get("owner", {}).get("login")
                repo_name = repository.get("name")
                
                if repo_owner and repo_name:
                    logging.info(f"Attempting to get user from workflow run {run_id}")
                    workflow_run = self.github_client.get_workflow_run(repo_owner, repo_name, run_id)
                    
                    if workflow_run:
                        # Check triggering_actor first
                        if "triggering_actor" in workflow_run:
                            initiated_by = workflow_run["triggering_actor"].get("login")
                            logging.info(f"Found initiated_by from workflow run triggering_actor: {initiated_by}")
                        # Fallback to actor
                        elif "actor" in workflow_run:
                            initiated_by = workflow_run["actor"].get("login")
                            logging.info(f"Found initiated_by from workflow run actor: {initiated_by}")
            
            if not initiated_by:
                logging.error("Could not determine who initiated the deployment")
                return {
                    "is_valid": False,
                    "initiated_by": "Unknown",
                    "error": "Could not determine deployment initiator"
                }
            
            # Clean up the username - GitHub usernames are already clean
            username_clean = self._extract_username(initiated_by)
            authorized_clean = self._extract_username(self.authorized_user)
            
            logging.info(f"Comparing: '{username_clean}' vs authorized: '{authorized_clean}'")
            
            is_valid = username_clean.lower() == authorized_clean.lower()
            
            result = {
                "is_valid": is_valid,
                "initiated_by": initiated_by,
                "username_checked": username_clean
            }
            
            if run_id:
                result["run_id"] = run_id
            
            return result
            
        except Exception as e:
            logging.error(f"Error validating deployment user: {e}", exc_info=True)
            return {
                "is_valid": False,
                "initiated_by": "Unknown",
                "error": str(e)
            }
    
    def _extract_username(self, user_string: str) -> str:
        """
        Extract username from various formats.
        
        For GitHub, usernames are typically clean, but this handles edge cases.
        
        Examples:
        - "user@domain.com" -> "user"
        - "DOMAIN\\user" -> "user"
        - "user" -> "user"
        
        Args:
            user_string: User identifier in various formats
            
        Returns:
            Extracted username
        """
        if not user_string:
            return ""
        
        # Remove email domain
        if "@" in user_string:
            user_string = user_string.split("@")[0]
        
        # Remove domain prefix
        if "\\" in user_string:
            user_string = user_string.split("\\")[-1]
        
        # Remove domain prefix (forward slash)
        if "/" in user_string:
            user_string = user_string.split("/")[-1]
        
        return user_string.strip()
