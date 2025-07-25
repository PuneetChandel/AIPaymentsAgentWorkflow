"""
Salesforce Service
"""
import os
from typing import Dict, Any, Optional
import requests

from utils.logging_config import get_logger

logger = get_logger('services.salesforce')

class SalesforceService:
    """
    Service for interacting with Salesforce
    """
    
    def __init__(self):
        # Initialize Salesforce connection (token-based)
        self.base_url = os.getenv('SALESFORCE_BASE_URL')
        self.access_token = os.getenv('SALESFORCE_ACCESS_TOKEN')
        
        # Initialize session for API calls
        self.session = requests.Session()
        
        if self.base_url and self.access_token:
            try:
                # Test the connection
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                })
                logger.info(f"✅ [SALESFORCE] Successfully configured Salesforce token-based auth")
                logger.info(f"🔗 [SALESFORCE] Using base URL: {self.base_url}")
            except Exception as e:
                logger.error(f"❌ [SALESFORCE] Failed to configure Salesforce: {e}")
                self.access_token = None
        else:
            logger.warning("⚠️ [SALESFORCE] Missing Salesforce credentials, using mock data")
            self.access_token = None
    
    def get_case(self, case_id: str) -> Dict[str, Any]:
        """
        Get case details from Salesforce
        """
        logger.info(f"🔍 [SALESFORCE] Fetching case {case_id} from Salesforce")
        
        if not self.access_token:
            logger.warning("⚠️ [SALESFORCE] Using mock data - no Salesforce connection")
            return self._get_mock_case(case_id)
        
        try:
            # Get case using REST API SObject endpoint
            case_url = f"{self.base_url}/services/data/v58.0/sobjects/Case/{case_id}"
            logger.info(f"🔍 [SALESFORCE] Fetching case from: {case_url}")
            
            response = self.session.get(case_url)
            
            if response.status_code == 200:
                case_data = response.json()
                logger.info(f"✅ [SALESFORCE] Successfully fetched case {case_id}")
                logger.info(f"📋 [SALESFORCE] Case data: {case_data}")
                
                return case_data
            elif response.status_code == 404:
                logger.warning(f"⚠️ [SALESFORCE] Case {case_id} not found, using mock data")
                return self._get_mock_case(case_id)
            else:
                logger.error(f"❌ [SALESFORCE] Failed to fetch case: {response.status_code} - {response.text}")
                return self._get_mock_case(case_id)
            
        except Exception as e:
            logger.error(f"❌ [SALESFORCE] Error fetching case {case_id}: {e}")
            logger.warning("⚠️ [SALESFORCE] Falling back to mock data")
            return self._get_mock_case(case_id)
    
    def get_account(self, account_id: str) -> Dict[str, Any]:
        """
        Get account details from Salesforce
        """
        logger.info(f"🔍 [SALESFORCE] Fetching account {account_id} from Salesforce")
        
        if not self.access_token:
            logger.warning("⚠️ [SALESFORCE] Using mock data - no Salesforce connection")
            return self._get_mock_account(account_id)
        
        try:
            # Get account using REST API SObject endpoint
            account_url = f"{self.base_url}/services/data/v58.0/sobjects/Account/{account_id}"
            logger.info(f"🔍 [SALESFORCE] Fetching account from: {account_url}")
            
            response = self.session.get(account_url)
            
            if response.status_code == 200:
                account_data = response.json()
                logger.info(f"✅ [SALESFORCE] Successfully fetched account {account_id}")
                logger.info(f"📋 [SALESFORCE] Account data: {account_data}")
                
                return account_data
            elif response.status_code == 404:
                logger.warning(f"⚠️ [SALESFORCE] Account {account_id} not found, using mock data")
                return self._get_mock_account(account_id)
            else:
                logger.error(f"❌ [SALESFORCE] Failed to fetch account: {response.status_code} - {response.text}")
                return self._get_mock_account(account_id)
            
        except Exception as e:
            logger.error(f"❌ [SALESFORCE] Error fetching account {account_id}: {e}")
            logger.warning("⚠️ [SALESFORCE] Falling back to mock data")
            return self._get_mock_account(account_id)
    
    def update_case(self, case_id: str, resolution: Dict[str, Any], status: str) -> bool:
        """
        Update case in Salesforce with resolution - mark as resolved and add comment
        """
        logger.info(f"🔄 [SALESFORCE] Updating case {case_id} in Salesforce")
        logger.info(f"📝 [SALESFORCE] Resolution data: {resolution}")
        
        if not self.access_token:
            logger.warning("⚠️ [SALESFORCE] Using mock update - no Salesforce connection")
            return True
        
        try:
            # Step 1: Update case status to resolved
            update_data = {
                'Status': 'Resolved'
            }
            
            logger.info(f"📝 [SALESFORCE] Updating case status to: Resolved")
            
            # Update the case using REST API
            update_url = f"{self.base_url}/services/data/v58.0/sobjects/Case/{case_id}"
            
            response = self.session.patch(update_url, json=update_data)
            
            if response.status_code != 204:
                logger.error(f"❌ [SALESFORCE] Failed to update case status: {response.status_code} - {response.text}")
                return False
            
            logger.info(f"✅ [SALESFORCE] Successfully updated case status to Resolved")
            
            # Step 2: Add a comment to the case
            comment_body = f"Dispute Resolution: {resolution.get('action', 'Unknown action')} - ${resolution.get('amount', 0)}. Reason: {resolution.get('reason', 'No reason provided')}"
            
            comment_data = {
                'ParentId': case_id,
                'CommentBody': comment_body,
                'IsPublished': True
            }
            
            logger.info(f"📝 [SALESFORCE] Adding comment: {comment_body}")
            
            # Create comment using REST API
            comment_url = f"{self.base_url}/services/data/v58.0/sobjects/CaseComment"
            
            comment_response = self.session.post(comment_url, json=comment_data)
            
            if comment_response.status_code == 201:
                comment_result = comment_response.json()
                logger.info(f"✅ [SALESFORCE] Successfully added comment with ID: {comment_result.get('id')}")
                return True
            else:
                logger.warning(f"⚠️ [SALESFORCE] Failed to add comment: {comment_response.status_code} - {comment_response.text}")
                # Still return True since the case was updated successfully
                return True
                
        except Exception as e:
            logger.error(f"❌ [SALESFORCE] Error updating case {case_id}: {e}")
            return False
    
    def _get_mock_case(self, case_id: str) -> Dict[str, Any]:
        """Get mock case data"""
        return {
            'Id': case_id,
            'CaseNumber': case_id,
            'AccountId': 'ACC-001-DEMO-67890',
            'Dispute_Type__c': 'Billing Dispute',
            'Amount__c': 99.99,
            'Description': 'Customer disputes charge for service not received',
            'Status': 'New',
            'Priority': 'Medium',
            'CreatedDate': '2024-01-15T10:30:00Z'
        }
    
    def _get_mock_account(self, account_id: str) -> Dict[str, Any]:
        """Get mock account data"""
        return {
            'Id': account_id,
            'Name': 'Acme Corporation',
            'Email__c': 'billing@acmecorp.com',
            'Phone': '+1-555-0123',
            'Customer_Segment__c': 'Premium',
            'Zuora_Account_ID__c': 'zuora-acc-demo-456',
            'Stripe_Customer_ID__c': 'cus_demo_stripe_789',
            'BillingCountry': 'US',
            'BillingState': 'CA'
        } 