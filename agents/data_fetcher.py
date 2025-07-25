"""
Data Fetcher Agent - Handles fetching data from all external systems
"""
import asyncio
from typing import Dict, Any

from services.service_factory import ServiceFactory
from agents.workflow_state import WorkflowState
from agents.workflow_context import get_current_case_id, get_current_run_id, get_current_customer_id
from utils.logging_config import get_logger

logger = get_logger('agents.data_fetcher')


def fetch_data_agent(state: WorkflowState) -> WorkflowState:
    """Fetch data from all systems using async parallel calls"""
    
    # Initialize services
    async_data = ServiceFactory.get_async_data_service()
    db = ServiceFactory.get_database_service()
    
    # Set up async data service with other services
    salesforce = ServiceFactory.get_salesforce_service()
    zuora = ServiceFactory.get_zuora_service()
    stripe = ServiceFactory.get_stripe_service()
    async_data.set_services(salesforce, zuora, stripe)
    
    # Get current workflow context from context manager
    current_case_id = get_current_case_id()
    current_customer_id = get_current_customer_id()
    current_run_id = get_current_run_id()
    
    try:
        logger.info(f"Starting parallel data fetch for case {current_case_id}")
        
        db.update_workflow_state(current_run_id, {
            'current_step': 'fetch_data',
            'status': 'running'
        })
        
        async def fetch_data():
            return await async_data.fetch_all_data(
                current_case_id,
                current_customer_id
            )
        
        data = asyncio.run(fetch_data())
        
        state.update({
            'current_step': 'fetch_data',
            'salesforce_data': data['salesforce_data'],
            'zuora_data': data['zuora_data'],
            'stripe_data': data['stripe_data']
        })
        
        db.update_workflow_state(current_run_id, {
            'salesforce_data': state['salesforce_data'],
            'zuora_data': state['zuora_data'],
            'stripe_data': state['stripe_data'],
            'case_id': current_case_id,
            'customer_id': current_customer_id
        })
        
        logger.info(f"Parallel data fetch completed for case {current_case_id}")
        return state
        
    except Exception as e:
        logger.error(f"Error in parallel data fetch: {e}")
        state['error_message'] = str(e)
        return state 