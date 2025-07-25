"""
Human Review Waiter Agent - Waits for human review decisions
"""
from services.service_factory import ServiceFactory
from agents.workflow_state import WorkflowState
from agents.workflow_context import get_current_case_id, get_current_run_id
from utils.logging_config import get_logger

logger = get_logger('agents.human_review_waiter')


def wait_human_review_agent(state: WorkflowState) -> WorkflowState:
    """Check for human review decision and route accordingly"""
    
    # Initialize services
    db = ServiceFactory.get_database_service()
    
    # Get current workflow context from context manager
    current_case_id = get_current_case_id()
    current_run_id = get_current_run_id()
    
    try:
        logger.info(f"Checking for human review decision for case {current_case_id}")
        
        # Update workflow state
        db.update_workflow_state(current_run_id, {
            'current_step': 'wait_human_review'
        })
        
        # Check for human review decision in database
        workflow_state = db.get_workflow_state(current_run_id)
        human_review_data = workflow_state.get('human_review_data', {}) if workflow_state else {}
        
        # Update state with latest human review data
        state.update({
            'current_step': 'wait_human_review',
            'human_review_data': human_review_data
        })
        
        # Check if human has made a decision
        if human_review_data.get('status') in ['approved', 'rejected']:
            logger.info(f"Human review decision found: {human_review_data['status']}")
            logger.info("Continuing workflow based on human decision")
        else:
            logger.info(f"No human review decision yet for case {current_case_id}")
            logger.info(f"Workflow will pause here. Use API to resume: POST /human-review/{current_run_id}/decision")
            # Set status to pending if not already set
            if not human_review_data.get('status'):
                state['human_review_data'] = {
                    'status': 'pending',
                    'message': 'Waiting for human review decision'
                }
        
        return state
        
    except Exception as e:
        logger.error(f"Error checking human review: {e}")
        state['error_message'] = str(e)
        return state


def check_human_review_agent(state: WorkflowState) -> str:
    """Check human review status for conditional routing"""
    human_review = state.get("human_review_data", {})
    status = human_review.get("status", "pending")
    
    logger.info(f"Checking human review status: {status}")
    
    if status == "approved":
        logger.info("Human review approved, routing to execute_resolution")
        return "approved"
    elif status == "rejected":
        logger.info("Human review rejected, routing to handle_error")
        return "rejected"
    else:
        logger.info("Human review still pending, continuing to wait")
        return "pending" 