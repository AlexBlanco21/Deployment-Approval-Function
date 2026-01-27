import azure.functions as func
import logging
import json
import os
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from shared import GitHubClient, ApprovalValidator

app = func.FunctionApp()

@app.function_name(name="ApprovalWebhook")
@app.route(route="approval-webhook", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def approval_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to handle GitHub Actions deployment protection rule webhooks.
    
    This function:
    1. Receives webhook notifications when environment approval is required
    2. Validates that the deployment was initiated by the authorized user
    3. Rejects deployment if unauthorized user is detected
    4. Adds error to workflow run summary
    """
    logging.info('GitHub Actions Approval Webhook function received a request.')
    
    try:
        # Parse the webhook payload
        req_body = req.get_json()
        logging.info(f"Received webhook payload: {json.dumps(req_body, indent=2)}")
        
        # Verify webhook signature (optional but recommended)
        webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
        if webhook_secret:
            signature = req.headers.get("X-Hub-Signature-256")
            if not verify_signature(req.get_body(), signature, webhook_secret):
                logging.error("Invalid webhook signature")
                return func.HttpResponse(
                    json.dumps({"error": "Invalid signature"}),
                    status_code=401,
                    mimetype="application/json"
                )
        
        # Initialize GitHub client
        github_token = os.environ.get("GITHUB_TOKEN")
        authorized_user = os.environ.get("AUTHORIZED_USER", "APZW3PRD_BCP")
        
        if not github_token:
            error_msg = "GitHub configuration is missing (GITHUB_TOKEN)"
            logging.error(error_msg)
            return func.HttpResponse(
                json.dumps({"error": error_msg}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Extract webhook information
        action = req_body.get("action")
        deployment_callback_url = req_body.get("deployment_callback_url")
        deployment = req_body.get("deployment", {})
        repository = req_body.get("repository", {})
        workflow = req_body.get("workflow", {})
        
        # Validate that this is a deployment_protection_rule event
        event_type = req.headers.get("X-GitHub-Event", "")
        if event_type != "deployment_protection_rule" or action != "requested":
            logging.warning(f"Received non-deployment protection event: {event_type}, action: {action}")
            return func.HttpResponse(
                json.dumps({"message": "Not a deployment protection rule request, skipping"}),
                status_code=200,
                mimetype="application/json"
            )
        
        # Extract deployment information
        repo_full_name = repository.get("full_name")
        repo_owner = repository.get("owner", {}).get("login")
        repo_name = repository.get("name")
        environment_name = deployment.get("environment")
        run_id = workflow.get("id")
        
        logging.info(f"Processing deployment protection for environment: {environment_name}")
        logging.info(f"Repository: {repo_full_name}")
        logging.info(f"Run ID: {run_id}")
        logging.info(f"Callback URL: {deployment_callback_url}")
        
        # Initialize clients
        github_client = GitHubClient(github_token)
        validator = ApprovalValidator(github_client, authorized_user)
        
        # Validate the user who initiated the deployment
        validation_result = validator.validate_deployment_user(req_body)
        
        if not validation_result["is_valid"]:
            # User is not authorized - reject the deployment
            initiated_by = validation_result.get("initiated_by", "Unknown")
            error_message = f"El usuario utilizado para el despliegue no se encuentra autorizado para desplegar en {environment_name}"
            
            logging.error(f"Unauthorized user detected: {initiated_by}")
            logging.error(error_message)
            
            # Reject the deployment via callback URL
            rejection_result = github_client.reject_deployment(
                callback_url=deployment_callback_url,
                comment=error_message
            )
            
            # Add error to workflow run summary
            if run_id:
                github_client.add_workflow_summary_error(
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    run_id=run_id,
                    error_message=error_message
                )
            
            return func.HttpResponse(
                json.dumps({
                    "status": "rejected",
                    "reason": error_message,
                    "initiated_by": initiated_by,
                    "authorized_user": authorized_user,
                    "rejection_result": rejection_result
                }),
                status_code=200,
                mimetype="application/json"
            )
        
        # User is authorized - approve the deployment
        initiated_by = validation_result.get("initiated_by", "Unknown")
        success_message = f"Usuario autorizado: {initiated_by}. Despliegue permitido en {environment_name}"
        
        logging.info(success_message)
        
        # Approve the deployment via callback URL
        approval_result = github_client.approve_deployment(
            callback_url=deployment_callback_url,
            comment=success_message
        )
        
        return func.HttpResponse(
            json.dumps({
                "status": "approved",
                "message": success_message,
                "initiated_by": initiated_by,
                "environment": environment_name,
                "approval_result": approval_result
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except ValueError as ve:
        error_msg = f"Invalid request body: {str(ve)}"
        logging.error(error_msg)
        return func.HttpResponse(
            json.dumps({"error": error_msg}),
            status_code=400,
            mimetype="application/json"
        )
    
    except Exception as e:
        error_msg = f"Unexpected error processing webhook: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": error_msg}),
            status_code=500,
            mimetype="application/json"
        )


def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """
    Verify that the payload was sent from GitHub by validating SHA256 signature.
    
    Args:
        payload_body: Request body bytes
        signature_header: X-Hub-Signature-256 header value
        secret: GitHub webhook secret
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        return False
    
    hash_object = hmac.new(secret.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)
