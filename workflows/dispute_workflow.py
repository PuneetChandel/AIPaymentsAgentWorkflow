"""
LangGraph Workflow for Dispute Resolution using Individual Agents
"""
from typing import Dict, Any
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents import (
    WorkflowState,
    WorkflowContext,
    set_workflow_context,
    fetch_data_agent,
    validate_dispute_agent,
    generate_resolution_agent,
    send_human_review_agent,
    wait_human_review_agent,
    check_human_review_agent,
    execute_resolution_agent,
    store_results_agent,
    handle_error_agent
)
from services.service_factory import ServiceFactory
from utils.logging_config import get_logger

logger = get_logger('workflows.dispute')


class DisputeWorkflow:
    """
    LangGraph workflow for dispute resolution using individual agents
    """
    
    def __init__(self):
        self.db = ServiceFactory.get_database_service()
        self.workflow = self._create_workflow()
        
        # These will be set when starting a workflow
        self.current_run_id = None
        self.current_case_id = None
        self.current_customer_id = None
    
    def _create_workflow(self) -> StateGraph:
        """
        Create the LangGraph workflow using individual agents
        """
        workflow = StateGraph(WorkflowState)
        
        # Add agent nodes
        workflow.add_node("fetch_data", fetch_data_agent)
        workflow.add_node("validate_dispute", validate_dispute_agent)
        workflow.add_node("generate_resolution", generate_resolution_agent)
        workflow.add_node("send_human_review", send_human_review_agent)
        workflow.add_node("wait_human_review", wait_human_review_agent)
        workflow.add_node("execute_resolution", execute_resolution_agent)
        workflow.add_node("store_results", store_results_agent)
        workflow.add_node("handle_error", handle_error_agent)
        
        # Add edges
        workflow.add_edge("fetch_data", "validate_dispute")
        workflow.add_edge("validate_dispute", "generate_resolution")
        workflow.add_edge("generate_resolution", "send_human_review")
        workflow.add_edge("send_human_review", "wait_human_review")
        workflow.add_edge("execute_resolution", "store_results")
        workflow.add_edge("store_results", END)
        
        # Add conditional edges for human review
        workflow.add_conditional_edges(
            "wait_human_review",
            check_human_review_agent,
            {
                "approved": "execute_resolution",
                "rejected": "handle_error",
                "pending": END
            }
        )
        
        workflow.set_entry_point("fetch_data")
        
        return workflow.compile(checkpointer=MemorySaver())
    
    def start_workflow(self, case_id: str, customer_id: str = None) -> str:
        """Start the dispute resolution workflow"""
        run_id = str(uuid.uuid4())
        self.current_run_id = run_id
        self.current_case_id = case_id
        self.current_customer_id = customer_id
        
        # Set workflow context
        set_workflow_context(case_id, run_id, customer_id)
        
        # Initialize state
        initial_state = WorkflowState(
            current_step="started",
            status="running",
            salesforce_data={},
            zuora_data={},
            stripe_data={},
            resolution_proposal={},
            human_review_data={},
            final_resolution={},
            error_message=""
        )
        
        # Save initial state to database
        self.db.save_workflow_state(run_id, case_id, customer_id)
        
        # Start the workflow
        logger.info(f"Starting workflow for case {case_id} with run_id {run_id}")
        
        try:
            # Use proper LangGraph invocation with config
            config = {"configurable": {"thread_id": run_id}}
            
            # Use WorkflowContext to ensure proper context setting
            with WorkflowContext(case_id, run_id, customer_id):
                result = self.workflow.invoke(initial_state, config=config)
                
            logger.info(f"Workflow completed for run {run_id}")
            return run_id
            
        except Exception as e:
            logger.error(f"Workflow failed for run {run_id}: {e}")
            self.db.mark_workflow_failed(run_id, str(e))
            raise
    
    def resume_workflow(self, run_id: str) -> bool:
        """Resume a paused workflow after human review decision"""
        try:
            logger.info(f"Resuming workflow for run_id {run_id}")
            
            # Get current workflow state
            workflow_state = self.db.get_workflow_state(run_id)
            if not workflow_state:
                logger.error(f"No workflow state found for run_id {run_id}")
                return False
            
            # Check if workflow is in human review state
            if workflow_state.get('current_step') != 'wait_human_review':
                logger.error(f"Workflow {run_id} is not in human review state")
                return False
            
            # Check if human decision is available
            human_review_data = workflow_state.get('human_review_data', {})
            if human_review_data.get('status') not in ['approved', 'rejected']:
                logger.error(f"No human decision available for workflow {run_id}")
                return False
            
            # Set current context for this workflow
            self.current_run_id = run_id
            self.current_case_id = workflow_state.get('case_id')
            self.current_customer_id = workflow_state.get('customer_id')
            
            logger.info(f"Resuming with human decision: {human_review_data.get('status')}")
            
            # Reconstruct the workflow state
            state = WorkflowState(
                current_step="wait_human_review",
                status="running",
                human_review_data=human_review_data,
                salesforce_data=workflow_state.get('salesforce_data', {}),
                zuora_data=workflow_state.get('zuora_data', {}),
                stripe_data=workflow_state.get('stripe_data', {}),
                resolution_proposal=workflow_state.get('resolution_proposal', {}),
                final_resolution={},
                error_message=""
            )
            
            # Use WorkflowContext to ensure proper context setting
            with WorkflowContext(self.current_case_id, run_id, self.current_customer_id):
                if human_review_data.get('status') == 'approved':
                    logger.info("Human approved - executing resolution")
                    state = execute_resolution_agent(state)
                    state = store_results_agent(state)
                elif human_review_data.get('status') == 'rejected':
                    logger.info("Human rejected - handling error")
                    state['error_message'] = f"Human rejected: {human_review_data.get('comments', 'No reason provided')}"
                    state = handle_error_agent(state)
            
            logger.info(f"Successfully resumed workflow {run_id}")
            logger.info(f"Final step: {state.get('current_step', 'unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error resuming workflow: {e}")
            return False 