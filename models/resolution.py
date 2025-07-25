"""
Resolution Model
"""
from typing import Dict, Any

class Resolution:
    """
    Represents a resolution for a dispute case
    """
    
    def __init__(self, case_id: str, action: str, amount: float, reason: str, 
                 confidence: float, requires_human_review: bool = True):
        self.case_id = case_id
        self.action = action  # full_refund, partial_refund, deny_refund, account_credit
        self.amount = amount
        self.reason = reason
        self.confidence = confidence
        self.requires_human_review = requires_human_review
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary
        """
        return {
            'case_id': self.case_id,
            'action': self.action,
            'amount': self.amount,
            'reason': self.reason,
            'confidence': self.confidence,
            'requires_human_review': self.requires_human_review
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Resolution':
        """
        Create from dictionary
        """
        return cls(
            case_id=data['case_id'],
            action=data['action'],
            amount=data['amount'],
            reason=data['reason'],
            confidence=data['confidence'],
            requires_human_review=data.get('requires_human_review', True)
        ) 