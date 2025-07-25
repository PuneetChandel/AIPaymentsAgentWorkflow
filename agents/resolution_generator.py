"""
Resolution Generator Agent - Generates AI-powered resolution proposals using LLM and vector DB
"""
from services.service_factory import ServiceFactory
from agents.workflow_state import WorkflowState
from agents.workflow_context import get_current_case_id, get_current_run_id
from models.dispute_case import DisputeCase
from models.resolution import Resolution
from utils.logging_config import get_logger

logger = get_logger('agents.resolution_generator')


def generate_resolution_agent(state: WorkflowState) -> WorkflowState:
    """Generate resolution proposal using LLM and vector DB"""
    
    # Initialize services
    vector_db = ServiceFactory.get_vector_service()
    llm = ServiceFactory.get_llm_service()
    db = ServiceFactory.get_database_service()
    
    # Get current workflow context from context manager
    current_case_id = get_current_case_id()
    current_run_id = get_current_run_id()
    
    try:
        logger.info(f"Generating resolution for case {current_case_id}")
        logger.info(f"📝 [WORKFLOW] PROPOSAL GENERATION - No refunds created at this stage")
        
        # Update workflow state
        db.update_workflow_state(current_run_id, {
            'current_step': 'generate_resolution'
        })
        
        # Create case object
        case = DisputeCase(
            case_id=current_case_id,
            case_data=state['salesforce_data']['case'],
            account_data=state['salesforce_data']['account'],
            subscription_data=state['zuora_data'],
            charge_data=state['stripe_data']
        )
        
        # Get similar cases and policies
        similar_cases = vector_db.get_similar_cases(case)
        policies = vector_db.get_relevant_policies(case)
        
        # Build context for LLM
        context = {
            'case': case.case_data,
            'account': case.account_data,
            'subscription': case.subscription_data,
            'charges': case.charge_data,
            'similar_cases': similar_cases,
            'policies': policies
        }
        
        # Generate resolution PROPOSAL (no actual refunds created)
        resolution_data = llm.generate_resolution(context)
        
        # Extract cost information
        cost_info = resolution_data.pop('cost_info', {'total_cost': 0.0})
        llm_cost = cost_info['total_cost']
        
        # Create resolution object
        resolution = Resolution(
            case_id=current_case_id,
            action=resolution_data['action'],
            amount=resolution_data['amount'],
            reason=resolution_data['reason'],
            confidence=resolution_data['confidence'],
            requires_human_review=True  # Always require human review for MVP
        )
        
        # Prepare cost breakdown
        cost_breakdown = {
            'llm': cost_info,
            'external_apis': {'total_cost': 0.0},  # Placeholder for future API costs
            'total_cost': llm_cost
        }
        
        # Update state
        state.update({
            'current_step': 'generate_resolution',
            'resolution_proposal': resolution.to_dict()
        })
        
        # Update database with cost information
        db.update_workflow_state(current_run_id, {
            'resolution_proposal': state['resolution_proposal'],
            'llm_cost': llm_cost,
            'total_cost': llm_cost,
            'cost_breakdown': cost_breakdown
        })
        
        logger.info(f"Resolution generated for case {current_case_id}")
        logger.info("Resolution proposal created - refunds will only be created after human approval")
        return state
        
    except Exception as e:
        logger.error(f"Error generating resolution: {e}")
        state['error_message'] = str(e)
        return state 