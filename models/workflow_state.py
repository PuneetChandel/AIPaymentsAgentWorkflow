"""
Workflow State Model for PostgreSQL
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class WorkflowState(Base):
    """
    PostgreSQL model for workflow state persistence
    """
    __tablename__ = "workflow_states"
    
    # Primary key
    run_id = Column(String(255), primary_key=True)
    
    # Case information
    case_id = Column(String(255), nullable=False)
    customer_id = Column(String(255), nullable=True)
    
    # Workflow state
    current_step = Column(String(100), nullable=False, default="started")
    status = Column(String(50), nullable=False, default="running")
    
    # Data from external systems
    salesforce_data = Column(JSON, nullable=True)
    zuora_data = Column(JSON, nullable=True)
    stripe_data = Column(JSON, nullable=True)
    
    # Resolution data
    resolution_proposal = Column(JSON, nullable=True)
    human_review_data = Column(JSON, nullable=True)
    final_resolution = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(String(10), default="0")
    
    # Cost tracking
    llm_cost = Column(Numeric(10, 4), nullable=True, default=0.0000, comment="Cost of LLM API calls")
    total_cost = Column(Numeric(10, 4), nullable=True, default=0.0000, comment="Total workflow cost")
    cost_breakdown = Column(JSON, nullable=True, comment="Detailed cost breakdown by service")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "customer_id": self.customer_id,
            "current_step": self.current_step,
            "status": self.status,
            "salesforce_data": self.salesforce_data,
            "zuora_data": self.zuora_data,
            "stripe_data": self.stripe_data,
            "resolution_proposal": self.resolution_proposal,
            "human_review_data": self.human_review_data,
            "final_resolution": self.final_resolution,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "llm_cost": float(self.llm_cost) if self.llm_cost else 0.0,
            "total_cost": float(self.total_cost) if self.total_cost else 0.0,
            "cost_breakdown": self.cost_breakdown
        } 