"""
Shared workflow state definition for all agents
"""
from typing import Dict, Any, TypedDict


class WorkflowState(TypedDict, total=False):
    """State for the dispute resolution workflow"""
    current_step: str
    status: str
    salesforce_data: Dict[str, Any]
    zuora_data: Dict[str, Any]
    stripe_data: Dict[str, Any]
    resolution_proposal: Dict[str, Any]
    human_review_data: Dict[str, Any]
    final_resolution: Dict[str, Any]
    error_message: str 