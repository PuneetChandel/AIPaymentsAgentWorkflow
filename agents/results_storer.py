"""
Results Storer Agent - Stores results in vector DB and marks workflow complete
"""
from services.service_factory import ServiceFactory
from agents.workflow_state import WorkflowState
from agents.workflow_context import get_current_case_id, get_current_run_id
from models.dispute_case import DisputeCase
from models.resolution import Resolution
from utils.logging_config import get_logger

logger = get_logger('agents.results_storer')


def store_results_agent(state: WorkflowState) -> WorkflowState:
    """Store results in vector DB and mark workflow complete"""
    
    # Initialize services
    db = ServiceFactory.get_database_service()
    vector_db = ServiceFactory.get_vector_service()
    email = ServiceFactory.get_email_service()
    
    # Get current workflow context from context manager
    current_case_id = get_current_case_id()
    current_run_id = get_current_run_id()
    
    try:
        logger.info(f"Storing results for case {current_case_id}")
        
        # Update workflow state
        db.update_workflow_state(current_run_id, {
            'current_step': 'store_results'
        })
        
        # Create case and resolution objects for storage
        case = DisputeCase(
            case_id=current_case_id,
            case_data=state['salesforce_data']['case'],
            account_data=state['salesforce_data']['account'],
            subscription_data=state['zuora_data'],
            charge_data=state['stripe_data']
        )
        
        resolution = Resolution.from_dict(state['final_resolution'])
        
        # Store in vector DB
        vector_db.store_resolution(case, resolution)
        
        # Mark workflow as completed
        db.mark_workflow_completed(current_run_id, state['final_resolution'])
        
        # Send completion email notification
        try:
            email_data = {
                'case_id': current_case_id,
                'customer_name': state['salesforce_data']['account'].get('Name', 'Unknown'),
            }
            
            # Get the decision from human review data
            human_review_data = state.get('human_review_data', {})
            decision = 'approved' if human_review_data.get('status') == 'approved' else 'rejected'
            
            email_sent = email.send_resolution_complete(email_data, current_run_id, decision)
            if email_sent:
                logger.info(f"📧 Completion email sent for case {current_case_id}")
            else:
                logger.warning(f"📧 Failed to send completion email for case {current_case_id}")
                
        except Exception as email_error:
            logger.warning(f"Error sending completion email: {email_error}")
        
        # Get final cost information and log it
        try:
            workflow_state = db.get_workflow_state(current_run_id)
            if workflow_state:
                total_cost = workflow_state.get('total_cost', 0.0)
                llm_cost = workflow_state.get('llm_cost', 0.0)
                cost_breakdown = workflow_state.get('cost_breakdown', {})
                
                # Log final cost summary
                logger.info(f"💰 WORKFLOW COMPLETED - Final Cost Summary:")
                logger.info(f"💰 Case ID: {current_case_id}")
                logger.info(f"💰 Run ID: {current_run_id}")
                logger.info(f"💰 Total Cost: ${total_cost:.6f}")
                logger.info(f"💰 LLM Cost: ${llm_cost:.6f}")
                
                # Log detailed cost breakdown if available
                if cost_breakdown:
                    llm_breakdown = cost_breakdown.get('llm', {})
                    if llm_breakdown:
                        input_tokens = llm_breakdown.get('input_tokens', 0)
                        output_tokens = llm_breakdown.get('output_tokens', 0)
                        input_cost = llm_breakdown.get('input_cost', 0.0)
                        output_cost = llm_breakdown.get('output_cost', 0.0)
                        
                        logger.info(f"💰 Token Usage - Input: {input_tokens} tokens (${input_cost:.6f}), Output: {output_tokens} tokens (${output_cost:.6f})")
                        logger.info(f"💰 Total Tokens: {input_tokens + output_tokens}")
                    
                    external_cost = cost_breakdown.get('external_apis', {}).get('total_cost', 0.0)
                    logger.info(f"💰 External API Cost: ${external_cost:.6f}")
                
                # Log cost efficiency metrics
                if total_cost > 0:
                    cost_in_cents = total_cost * 100
                    logger.info(f"💰 Cost Efficiency: {cost_in_cents:.4f} cents per dispute resolution")
                
            else:
                logger.warning("Could not retrieve cost information from database")
                
        except Exception as cost_error:
            logger.warning(f"Error retrieving cost information: {cost_error}")
        
        state.update({
            'current_step': 'store_results',
            'status': 'completed'
        })
        
        logger.info(f"Results stored for case {current_case_id}")
        logger.info(f"✅ WORKFLOW COMPLETED SUCCESSFULLY - Run ID: {current_run_id}")
        return state
        
    except Exception as e:
        logger.error(f"Error storing results: {e}")
        state['error_message'] = str(e)
        return state 