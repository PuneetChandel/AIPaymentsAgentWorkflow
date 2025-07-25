"""
Workflow Context Manager - Handles workflow-specific context data
"""
from typing import Optional
from contextvars import ContextVar

# Context variables for workflow-specific data
_current_case_id: ContextVar[Optional[str]] = ContextVar('current_case_id', default=None)
_current_run_id: ContextVar[Optional[str]] = ContextVar('current_run_id', default=None)
_current_customer_id: ContextVar[Optional[str]] = ContextVar('current_customer_id', default=None)


class WorkflowContext:
    """Context manager for workflow-specific data"""
    
    def __init__(self, case_id: str, run_id: str, customer_id: str = None):
        self.case_id = case_id
        self.run_id = run_id
        self.customer_id = customer_id
        
    def __enter__(self):
        self.case_id_token = _current_case_id.set(self.case_id)
        self.run_id_token = _current_run_id.set(self.run_id)
        self.customer_id_token = _current_customer_id.set(self.customer_id)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        _current_case_id.reset(self.case_id_token)
        _current_run_id.reset(self.run_id_token)
        _current_customer_id.reset(self.customer_id_token)


def get_current_case_id() -> Optional[str]:
    """Get the current case ID from context"""
    return _current_case_id.get()


def get_current_run_id() -> Optional[str]:
    """Get the current run ID from context"""
    return _current_run_id.get()


def get_current_customer_id() -> Optional[str]:
    """Get the current customer ID from context"""
    return _current_customer_id.get()


def set_workflow_context(case_id: str, run_id: str, customer_id: str = None):
    """Set workflow context variables (alternative to context manager)"""
    _current_case_id.set(case_id)
    _current_run_id.set(run_id)
    _current_customer_id.set(customer_id) 