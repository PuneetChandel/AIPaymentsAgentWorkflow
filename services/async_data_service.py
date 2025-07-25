"""
Async Data Service for parallel API calls
"""
import asyncio
from typing import Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

from utils.logging_config import get_logger

logger = get_logger('services.async_data')

class AsyncDataService:
    """
    Service for fetching data from multiple sources in parallel
    """
    
    def __init__(self, salesforce_service=None, zuora_service=None, stripe_service=None):
        self.executor = ThreadPoolExecutor(max_workers=4)
        # Services will be set by ServiceFactory to avoid circular imports
        self.salesforce = salesforce_service
        self.zuora = zuora_service
        self.stripe = stripe_service
    
    def set_services(self, salesforce_service, zuora_service, stripe_service):
        """Set services after initialization to avoid circular imports"""
        self.salesforce = salesforce_service
        self.zuora = zuora_service
        self.stripe = stripe_service

    async def fetch_all_data(self, case_id: str, customer_id: str) -> Dict[str, Any]:
        """
        Fetch data from all external systems in parallel
        
        Args:
            case_id: Salesforce case ID
            customer_id: Customer ID for Zuora/Stripe
            
        Returns:
            Dict containing all fetched data
        """
        if not all([self.salesforce, self.zuora, self.stripe]):
            raise RuntimeError("Services not initialized. Call set_services() first.")
        
        logger.info(f"🚀 [ASYNC] Starting parallel data fetch for case {case_id}")
        
        # Get event loop
        loop = asyncio.get_event_loop()
        
        # Create tasks for parallel execution
        tasks = [
            # Salesforce case data
            loop.run_in_executor(
                self.executor,
                self._fetch_salesforce_case,
                case_id
            ),
            # Zuora subscription data
            loop.run_in_executor(
                self.executor,
                self._fetch_zuora_data,
                customer_id
            ),
            # Stripe charges data
            loop.run_in_executor(
                self.executor,
                self._fetch_stripe_data,
                customer_id
            )
        ]
        
        # Execute all tasks in parallel
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            salesforce_data = results[0] if not isinstance(results[0], Exception) else None
            zuora_data = results[1] if not isinstance(results[1], Exception) else None
            stripe_data = results[2] if not isinstance(results[2], Exception) else None
            
            # Check for errors
            errors = []
            if isinstance(results[0], Exception):
                errors.append(f"Salesforce: {results[0]}")
            if isinstance(results[1], Exception):
                errors.append(f"Zuora: {results[1]}")
            if isinstance(results[2], Exception):
                errors.append(f"Stripe: {results[2]}")
            
            if errors:
                logger.error(f"❌ [ASYNC] Some API calls failed: {'; '.join(errors)}")
                # Don't fail completely if some data is available
                if not salesforce_data:
                    raise Exception(f"Critical error - Salesforce data unavailable: {errors}")
            
            # If we have Salesforce data, fetch account data
            account_data = None
            if salesforce_data and salesforce_data.get('AccountId'):
                account_data = await loop.run_in_executor(
                    self.executor,
                    self._fetch_salesforce_account,
                    salesforce_data['AccountId']
                )
            
            logger.info(f"✅ [ASYNC] Parallel data fetch completed for case {case_id}")
            
            return {
                'salesforce_data': {
                    'case': salesforce_data or {},
                    'account': account_data or {}
                },
                'zuora_data': zuora_data or {},
                'stripe_data': stripe_data or {}
            }
            
        except Exception as e:
            logger.error(f"❌ [ASYNC] Error in parallel data fetch: {e}")
            raise
    
    def _fetch_salesforce_case(self, case_id: str) -> Dict[str, Any]:
        """Fetch Salesforce case data"""
        try:
            logger.info(f"📞 [ASYNC] Fetching Salesforce case {case_id}")
            return self.salesforce.get_case(case_id)
        except Exception as e:
            logger.error(f"❌ [ASYNC] Salesforce case fetch failed: {e}")
            raise
    
    def _fetch_salesforce_account(self, account_id: str) -> Dict[str, Any]:
        """Fetch Salesforce account data"""
        try:
            logger.info(f"📞 [ASYNC] Fetching Salesforce account {account_id}")
            return self.salesforce.get_account(account_id)
        except Exception as e:
            logger.error(f"❌ [ASYNC] Salesforce account fetch failed: {e}")
            raise
    
    def _fetch_zuora_data(self, customer_id: str) -> Dict[str, Any]:
        """Fetch Zuora subscription data"""
        try:
            logger.info(f"📞 [ASYNC] Fetching Zuora data for {customer_id}")
            return self.zuora.get_subscription(customer_id)
        except Exception as e:
            logger.error(f"❌ [ASYNC] Zuora fetch failed: {e}")
            raise
    
    def _fetch_stripe_data(self, customer_id: str) -> Dict[str, Any]:
        """Fetch Stripe charges data"""
        try:
            logger.info(f"📞 [ASYNC] Fetching Stripe data for {customer_id}")
            return self.stripe.get_charges(customer_id)
        except Exception as e:
            logger.error(f"❌ [ASYNC] Stripe fetch failed: {e}")
            raise
    
    def __del__(self):
        """Clean up executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False) 