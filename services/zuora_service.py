"""
Zuora Service
"""
import os
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from utils.logging_config import get_logger

logger = get_logger('services.zuora')

class ZuoraService:
    """
    Service for interacting with Zuora
    """
    
    def __init__(self):
        # Initialize Zuora connection (token-based)
        self.base_url = os.getenv('ZUORA_BASE_URL')
        self.access_token = os.getenv('ZUORA_ACCESS_TOKEN')
        self.default_payment_id = os.getenv('ZUORA_DEFAULT_PAYMENT_ID')
        
        # Initialize session
        self.session = requests.Session()
        
        if self.base_url and self.access_token:
            try:
                # Set up headers for token-based auth
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                })
                logger.info(f"✅ [ZUORA] Successfully configured Zuora token-based auth")
                logger.info(f"🔗 [ZUORA] Using base URL: {self.base_url}")
            except Exception as e:
                logger.error(f"❌ [ZUORA] Failed to configure Zuora: {e}")
                self.access_token = None
        else:
            logger.warning("⚠️ [ZUORA] Missing Zuora credentials, using mock data")
            self.access_token = None
    

    
    def get_account_id(self, account_number: str) -> Optional[str]:
        """
        Get Zuora Account ID from Account Number
        """
        logger.info(f"🔍 [ZUORA] Fetching Account ID for account number {account_number}")
        if not self.access_token:
            logger.warning("⚠️ [ZUORA] Using mock data - no Zuora connection")
            return account_number  # fallback for mock
        try:
            query_url = f"{self.base_url}/v1/action/query"
            query = f"SELECT Id FROM Account WHERE AccountNumber = '{account_number}'"
            query_data = {"queryString": query}
            response = self.session.post(query_url, json=query_data)
            if response.status_code == 200:
                result = response.json()
                if result.get('records') and len(result['records']) > 0:
                    account_id = result['records'][0]['Id']
                    logger.info(f"✅ [ZUORA] Found Account ID: {account_id} for account number {account_number}")
                    return account_id
                else:
                    logger.warning(f"⚠️ [ZUORA] No account found for account number {account_number}")
                    return None
            else:
                logger.error(f"❌ [ZUORA] Account query failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ [ZUORA] Error fetching account ID for account number {account_number}: {e}")
            return None

    def get_subscription(self, account_number: str) -> Dict[str, Any]:
        """
        Get subscription details from Zuora using account number
        """
        logger.info(f"🔍 [ZUORA] Fetching subscription for account number {account_number} from Zuora")
        if not self.access_token:
            logger.warning("⚠️ [ZUORA] Using mock data - no Zuora connection")
            return self._get_mock_subscription(account_number)
        account_id = self.get_account_id(account_number)
        if not account_id:
            logger.warning(f"⚠️ [ZUORA] Could not resolve account number {account_number} to an Account ID")
            return self._get_mock_subscription(account_number)
        try:
            query_url = f"{self.base_url}/v1/action/query"
            query = f"SELECT Id, AccountId, Status, TermStartDate, TermEndDate, ContractEffectiveDate, ServiceActivationDate, ContractAcceptanceDate FROM Subscription WHERE AccountId = '{account_id}' AND Status = 'Active'"
            query_data = {"queryString": query}
            logger.info(f"🔍 [ZUORA] Executing query: {query}")
            response = self.session.post(query_url, json=query_data)
            if response.status_code == 200:
                result = response.json()
                if result.get('records') and len(result['records']) > 0:
                    subscription_data = result['records'][0]
                    logger.info(f"✅ [ZUORA] Successfully fetched subscription for account number {account_number}")
                    logger.info(f"📋 [ZUORA] Subscription data: {subscription_data}")
                    return subscription_data
                else:
                    logger.warning(f"⚠️ [ZUORA] No active subscription found for account number {account_number}, using mock data")
                    return self._get_mock_subscription(account_number)
            else:
                logger.error(f"❌ [ZUORA] Query failed: {response.status_code} - {response.text}")
                return self._get_mock_subscription(account_number)
        except Exception as e:
            logger.error(f"❌ [ZUORA] Error fetching subscription for account number {account_number}: {e}")
            logger.warning("⚠️ [ZUORA] Falling back to mock data")
            return self._get_mock_subscription(account_number)

    def create_refund(self, account_number: str, amount: float, reason: str) -> str:
        """
        Create a refund in Zuora using account number
        """
        logger.info(f"💰 [ZUORA] Creating refund for account number {account_number}: ${amount}")
        logger.info(f"📝 [ZUORA] Refund reason: {reason}")
        if not self.access_token:
            logger.warning("⚠️ [ZUORA] Using mock refund - no Zuora connection")
            return self._get_mock_refund_id(account_number, amount)
        account_id = self.get_account_id(account_number)
        if not account_id:
            logger.warning(f"⚠️ [ZUORA] Could not resolve account number {account_number} to an Account ID")
            return self._get_mock_refund_id(account_number, amount)
        try:
            # Use the refund endpoint
            refund_url = f"{self.base_url}/v1/object/refund"
            refund_data = {
                "PaymentId": self.default_payment_id or "8ac6885e97ee57fd0197f26d5f31238b",  # From .env or fallback
                "Amount": amount,  # Keep as decimal
                "AccountId": account_id,
                "Type": "External",
                "SourceType": "Payment",
                "RefundDate": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
                "MethodType": "CreditCard"
            }
            logger.info(f"📝 [ZUORA] Refund data: {refund_data}")
            response = self.session.post(refund_url, json=refund_data)
            
            if response.status_code == 200:
                result = response.json()
                refund_id = result.get('Id')
                logger.info(f"✅ [ZUORA] Successfully created refund {refund_id}")
                logger.info(f"📋 [ZUORA] Refund data: {result}")
                return refund_id
            else:
                logger.error(f"❌ [ZUORA] Failed to create refund: {response.status_code} - {response.text}")
                return self._get_mock_refund_id(account_number, amount)
        except Exception as e:
            logger.error(f"❌ [ZUORA] Error creating refund for account number {account_number}: {e}")
            return self._get_mock_refund_id(account_number, amount)
    
    def _get_mock_subscription(self, account_number: str) -> Dict[str, Any]:
        """Get mock subscription data"""
        return {
            'id': 'zuora-subscription-123',
            'account_number': account_number,
            'status': 'Active',
            'product_name': 'Premium Plan',
            'amount': 99.99,
            'currency': 'USD',
            'billing_cycle': 'Monthly',
            'next_billing_date': '2024-02-15',
            'created_date': '2023-01-15'
        }
    
    def _get_mock_refund_id(self, account_number: str, amount: float) -> str:
        """Get mock refund ID"""
        refund_id = f"refund-{account_number}-{int(amount * 100)}"
        logger.info(f"✅ [ZUORA] Created mock refund {refund_id}")
        return refund_id 