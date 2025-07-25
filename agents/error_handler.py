"""
Error Handler Agent - Handles workflow errors and marks workflow as failed
"""
from services.service_factory import ServiceFactory
from agents.workflow_state import WorkflowState
from agents.workflow_context import get_current_case_id, get_current_run_id
from utils.logging_config import get_logger

logger = get_logger('agents.error_handler')


def handle_error_agent(state: WorkflowState) -> WorkflowState:
    """Handle workflow errors"""
    
    # Initialize services
    db = ServiceFactory.get_database_service()
    
    # Get current workflow context from context manager
    current_case_id = get_current_case_id()
    current_run_id = get_current_run_id()
    
    try:
        logger.error(f"Handling error for case {current_case_id}: {state.get('error_message')}")
        
        # Mark workflow as failed
        db.mark_workflow_failed(current_run_id, state.get('error_message', 'Unknown error'))
        
        # Log cost information even for failed workflows
        try:
            workflow_state = db.get_workflow_state(current_run_id)
            if workflow_state:
                total_cost = workflow_state.get('total_cost', 0.0)
                llm_cost = workflow_state.get('llm_cost', 0.0)
                
                logger.error(f"💰 WORKFLOW FAILED - Cost Summary:")
                logger.error(f"💰 Case ID: {current_case_id}")
                logger.error(f"💰 Run ID: {current_run_id}")
                logger.error(f"💰 Total Cost: ${total_cost:.6f}")
                logger.error(f"💰 LLM Cost: ${llm_cost:.6f}")
                
                if total_cost > 0:
                    cost_in_cents = total_cost * 100
                    logger.error(f"💰 Cost of Failed Workflow: {cost_in_cents:.4f} cents")
                    
        except Exception as cost_error:
            logger.warning(f"Error retrieving cost information for failed workflow: {cost_error}")
        
        state.update({
            'current_step': 'error',
            'status': 'failed'
        })
        
        logger.error(f"❌ WORKFLOW FAILED - Run ID: {current_run_id}")
        return state
        
    except Exception as e:
        logger.error(f"Error in error handler: {e}")
        return state 