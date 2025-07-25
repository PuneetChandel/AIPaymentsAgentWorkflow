"""
Dispute Case Model
"""
from typing import Dict, Any, Optional

class DisputeCase:
    """
    Represents a dispute case with data from all systems
    """
    
    def __init__(self, case_id: str, case_data: Dict[str, Any], 
                 account_data: Dict[str, Any], subscription_data: Dict[str, Any], 
                 charge_data: Dict[str, Any]):
        self.case_id = case_id
        self.case_data = case_data or {}
        self.account_data = account_data or {}
        self.subscription_data = subscription_data or {}
        self.charge_data = charge_data or {}
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the case for human review
        """
        return {
            'case_id': self.case_id,
            'customer_name': self.account_data.get('Name', 'Unknown'),
            'dispute_type': self.case_data.get('Dispute_Type__c', 'Unknown'),
            'amount': self.case_data.get('Amount__c', 0),
            'description': self.case_data.get('Description', ''),
            'customer_segment': self.account_data.get('Customer_Segment__c', 'Standard'),
            'subscription_status': self.subscription_data.get('status', 'Unknown'),
            'charges_count': len(self.charge_data.get('charges', []))
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary
        """
        return {
            'case_id': self.case_id,
            'case_data': self.case_data,
            'account_data': self.account_data,
            'subscription_data': self.subscription_data,
            'charge_data': self.charge_data
        } 