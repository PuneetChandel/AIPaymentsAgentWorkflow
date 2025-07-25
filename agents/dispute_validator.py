"""
Dispute Validator Agent - Validates dispute data and checks if it's a valid billing dispute
"""
from services.service_factory import ServiceFactory
from agents.workflow_state import WorkflowState
from agents.workflow_context import get_current_case_id, get_current_run_id
from utils.logging_config import get_logger

logger = get_logger('agents.dispute_validator')


def validate_dispute_agent(state: WorkflowState) -> WorkflowState:
    """Validate the dispute"""
    
    # Initialize services
    db = ServiceFactory.get_database_service()
    
    # Get current workflow context from context manager
    current_case_id = get_current_case_id()
    current_run_id = get_current_run_id()
    
    try:
        logger.info(f"Validating dispute for case {current_case_id}")
        
        db.update_workflow_state(current_run_id, {
            'current_step': 'validate_dispute'
        })
        
        case_data = state['salesforce_data']['case']
        
        if not case_data:
            raise ValueError("Case data not found")
        
        dispute_type = case_data.get('Dispute_Type__c', '').lower()
        if 'billing' not in dispute_type and 'charge' not in dispute_type:
            raise ValueError("Not a billing dispute")
        
        amount = float(case_data.get('Amount__c', 0))
        if amount < 0:
            raise ValueError("Invalid dispute amount: negative amounts not allowed")
        
        state.update({
            'current_step': 'validate_dispute'
        })
        
        logger.info(f"Dispute validated for case {current_case_id}")
        return state
        
    except Exception as e:
        logger.error(f"Error validating dispute: {e}")
        state['error_message'] = str(e)
        return state 