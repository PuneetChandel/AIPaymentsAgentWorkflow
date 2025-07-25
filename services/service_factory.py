"""
Service Factory for managing singleton service instances
"""
from typing import Dict, Any

from services.database_service import DatabaseService
from services.vector_service_optimized import VectorServiceOptimized
from services.salesforce_service import SalesforceService
from services.zuora_service import ZuoraService
from services.stripe_service import StripeService
from services.llm_service import LLMService
from services.async_data_service import AsyncDataService
from services.aws_service import AWSService
from services.email_service import EmailService
from utils.logging_config import get_logger

logger = get_logger('services.factory')

class ServiceFactory:
    """
    Factory class to manage singleton service instances
    """
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def get_database_service(cls) -> DatabaseService:
        """Get singleton database service instance"""
        if 'database' not in cls._instances:
            cls._instances['database'] = DatabaseService()
            logger.info("Created singleton DatabaseService instance")
        return cls._instances['database']
    
    @classmethod
    def get_vector_service(cls) -> VectorServiceOptimized:
        """Get singleton optimized vector service instance"""
        if 'vector' not in cls._instances:
            cls._instances['vector'] = VectorServiceOptimized()
            logger.info("Created singleton VectorServiceOptimized instance")
        return cls._instances['vector']
    
    @classmethod
    def get_salesforce_service(cls) -> SalesforceService:
        """Get singleton salesforce service instance"""
        if 'salesforce' not in cls._instances:
            cls._instances['salesforce'] = SalesforceService()
            logger.info("Created singleton SalesforceService instance")
        return cls._instances['salesforce']
    
    @classmethod
    def get_zuora_service(cls) -> ZuoraService:
        """Get singleton zuora service instance"""
        if 'zuora' not in cls._instances:
            cls._instances['zuora'] = ZuoraService()
            logger.info("Created singleton ZuoraService instance")
        return cls._instances['zuora']
    
    @classmethod
    def get_stripe_service(cls) -> StripeService:
        """Get singleton stripe service instance"""
        if 'stripe' not in cls._instances:
            cls._instances['stripe'] = StripeService()
            logger.info("Created singleton StripeService instance")
        return cls._instances['stripe']
    
    @classmethod
    def get_llm_service(cls) -> LLMService:
        """Get singleton LLM service instance"""
        if 'llm' not in cls._instances:
            cls._instances['llm'] = LLMService()
            logger.info("Created singleton LLMService instance")
        return cls._instances['llm']
    
    @classmethod
    def get_async_data_service(cls) -> AsyncDataService:
        """Get singleton async data service instance"""
        if 'async_data' not in cls._instances:
            cls._instances['async_data'] = AsyncDataService()
            logger.info("Created singleton AsyncDataService instance")
        return cls._instances['async_data']
    
    @classmethod
    def get_aws_service(cls) -> AWSService:
        """Get singleton AWS service instance"""
        if 'aws' not in cls._instances:
            cls._instances['aws'] = AWSService()
            logger.info("Created singleton AWSService instance")
        return cls._instances['aws']
    
    @classmethod
    def get_email_service(cls) -> EmailService:
        """Get singleton email service instance"""
        if 'email' not in cls._instances:
            cls._instances['email'] = EmailService()
            logger.info("Created singleton EmailService instance")
        return cls._instances['email']
 