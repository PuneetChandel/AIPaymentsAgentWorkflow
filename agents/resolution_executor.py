"""
Resolution Executor Agent - Executes approved resolutions
"""
from services.service_factory import ServiceFactory
from agents.workflow_state import WorkflowState
from agents.workflow_context import get_current_case_id, get_current_run_id, get_current_customer_id
from utils.logging_config import get_logger

logger = get_logger('agents.resolution_executor')


def execute_resolution_agent(state: WorkflowState) -> WorkflowState:
    """Execute the human-approved resolution"""
    
    # Initialize services
    db = ServiceFactory.get_database_service()
    salesforce = ServiceFactory.get_salesforce_service()
    zuora = ServiceFactory.get_zuora_service()
    
    # Get current workflow context from context manager
    current_case_id = get_current_case_id()
    current_customer_id = get_current_customer_id()
    current_run_id = get_current_run_id()
    
    try:
        logger.info(f"Executing resolution for case {current_case_id}")
        
        db.update_workflow_state(current_run_id, {
            'current_step': 'execute_resolution'
        })
        
        human_review = state.get('human_review_data', {})
        approved_resolution = human_review.get('decision', state['resolution_proposal'])
        
        if human_review.get('status') != 'approved':
            logger.error("SECURITY VIOLATION: Attempting to execute resolution without human approval!")
            logger.error(f"Human review status: {human_review.get('status', 'unknown')}")
            raise ValueError("Cannot execute resolution without human approval")
        
        logger.info(f"Human approval confirmed - status: {human_review.get('status')}")
        logger.info(f"Approved by: {human_review.get('reviewer', 'unknown')}")
        logger.info(f"Approved resolution: {approved_resolution}")
        
        if approved_resolution['action'] in ['full_refund', 'partial_refund']:
            account_number = current_customer_id
            logger.info(f"Creating refund in Zuora for account {account_number}")
            logger.info("REFUND CREATION - This happens ONLY after human approval")
            
            refund_id = zuora.create_refund(
                account_number=account_number,
                amount=approved_resolution['amount'],
                reason=approved_resolution['reason']
            )
            logger.info(f"Created refund {refund_id} in Zuora")
            
            approved_resolution['refund_id'] = refund_id
        else:
            logger.info(f"No refund required for action: {approved_resolution['action']}")
        
        logger.info(f"Updating case {current_case_id} in Salesforce")
        salesforce.update_case(
            case_id=current_case_id,
            resolution=approved_resolution,
            status='Resolved'
        )
        
        state.update({
            'current_step': 'execute_resolution',
            'final_resolution': approved_resolution
        })
        
        db.update_workflow_state(current_run_id, {
            'final_resolution': state['final_resolution']
        })
        
        logger.info(f"Resolution executed for case {current_case_id}")
        return state
        
    except Exception as e:
        logger.error(f"Error executing resolution: {e}")
        state['error_message'] = str(e)
        return state 