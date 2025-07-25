"""
Human Review Sender Agent - Sends resolution proposals for human review
"""
from datetime import datetime
from services.service_factory import ServiceFactory
from agents.workflow_state import WorkflowState
from agents.workflow_context import get_current_case_id, get_current_run_id, get_current_customer_id
from utils.logging_config import get_logger

logger = get_logger('agents.human_review_sender')


def send_human_review_agent(state: WorkflowState) -> WorkflowState:
    """Send resolution for human review"""
    
    # Initialize services
    db = ServiceFactory.get_database_service()
    aws = ServiceFactory.get_aws_service()
    email = ServiceFactory.get_email_service()
    
    # Get current workflow context from context manager
    current_case_id = get_current_case_id()
    current_customer_id = get_current_customer_id()
    current_run_id = get_current_run_id()
    
    try:
        logger.info(f"Sending case {current_case_id} for human review")
        
        # Update workflow state
        db.update_workflow_state(current_run_id, {
            'current_step': 'send_human_review'
        })
        
        # Create review request
        review_request = {
            'case_id': current_case_id,
            'customer_id': current_customer_id,
            'resolution': state['resolution_proposal'],
            'case_summary': {
                'customer_name': state['salesforce_data']['account'].get('Name', 'Unknown'),
                'dispute_type': state['salesforce_data']['case'].get('Dispute_Type__c', 'Unknown'),
                'amount': state['salesforce_data']['case'].get('Amount__c', 0),
                'description': state['salesforce_data']['case'].get('Description', '')
            },
            'system_data': {
                'salesforce_case': state['salesforce_data']['case'],
                'salesforce_account': state['salesforce_data']['account'],
                'zuora_subscription': state['zuora_data'],
                'stripe_charges': state['stripe_data']
            },
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'pending_review'
        }
        
        # Send to SQS for human review using AWS service
        message_id = aws.send_human_review_notification(review_request)
        
        if message_id:
            logger.info(f"Human review notification sent successfully: {message_id}")
        else:
            logger.error("Failed to send human review notification")
        
        # Send email notification to approver
        email_data = {
            'case_id': current_case_id,
            'customer_name': state['salesforce_data']['account'].get('Name', 'Unknown'),
            'dispute_type': state['salesforce_data']['case'].get('Dispute_Type__c', 'Unknown'),
            'amount': state['salesforce_data']['case'].get('Amount__c', 0),
            'resolution': state['resolution_proposal']
        }
        
        email_sent = email.send_approval_request(email_data, current_run_id)
        if email_sent:
            logger.info(f"📧 Approval email sent for case {current_case_id}")
        else:
            logger.warning(f"📧 Failed to send approval email for case {current_case_id}")
        
        # Update state
        state.update({
            'current_step': 'send_human_review',
            'error_message': None,  # Clear any previous errors
            'human_review_data': {
                'status': 'pending',
                'message': 'Sent to human review queue',
                'review_request': review_request
            }
        })
        
        # Update database with current state
        try:
            db.update_workflow_state(current_run_id, {
                'current_step': 'send_human_review',
                'human_review_data': state['human_review_data'],
                'status': 'running'
            })
        except Exception as db_error:
            logger.warning(f"Database update warning (continuing): {db_error}")
        
        return state
        
    except Exception as e:
        logger.error(f"Error sending human review: {e}")
        state['error_message'] = str(e)
        return state 