"""
Database Service for PostgreSQL operations
"""
import os
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from models.workflow_state import Base, WorkflowState
from utils.logging_config import get_logger

logger = get_logger('services.database')

class DatabaseService:
    """
    Service for PostgreSQL database operations with connection pooling
    """
    
    _instance = None
    _engine = None
    
    def __new__(cls):
        """Singleton pattern to reuse database connections"""
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._engine is None:
            self.database_url = os.getenv('POSTGRES_URL')
            if not self.database_url:
                raise ValueError("POSTGRES_URL environment variable is required")
            
            self._engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self._engine
            )
            
            Base.metadata.create_all(bind=self._engine)
            logger.info("Database service initialized with connection pooling")
    

    
    def save_workflow_state(self, run_id: str, case_id: str, customer_id: str = None) -> bool:
        """Save initial workflow state"""
        try:
            with self.SessionLocal() as session:
                workflow_state = WorkflowState(
                    run_id=run_id,
                    case_id=case_id,
                    customer_id=customer_id,
                    current_step='started',
                    status='running'
                )
                session.add(workflow_state)
                session.commit()
                logger.info(f"Saved workflow state for run {run_id}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error saving workflow state: {e}")
            return False
    
    def get_workflow_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow state by run ID"""
        try:
            with self.SessionLocal() as session:
                workflow_state = session.query(WorkflowState).filter(
                    WorkflowState.run_id == run_id
                ).first()
                
                if not workflow_state:
                    logger.error(f"Workflow state not found for run {run_id}")
                    return None
                
                return workflow_state.to_dict()
        except SQLAlchemyError as e:
            logger.error(f"Error getting workflow state: {e}")
            return None
    
    def update_workflow_state(self, run_id: str, updates: Dict[str, Any]) -> bool:
        """Update workflow state"""
        try:
            with self.SessionLocal() as session:
                workflow_state = session.query(WorkflowState).filter(
                    WorkflowState.run_id == run_id
                ).first()
                
                if workflow_state:
                    for key, value in updates.items():
                        setattr(workflow_state, key, value)
                    
                    session.commit()
                    logger.info(f"Updated workflow state for run {run_id}")
                    return True
                else:
                    logger.error(f"Workflow state not found for run {run_id}")
                    return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating workflow state: {e}")
            return False
    
    def get_workflows_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        """Get all workflows for a case"""
        try:
            with self.SessionLocal() as session:
                workflows = session.query(WorkflowState).filter(
                    WorkflowState.case_id == case_id
                ).all()
                
                return [workflow.to_dict() for workflow in workflows]
        except SQLAlchemyError as e:
            logger.error(f"Error getting workflows by case: {e}")
            return []
    
    def mark_workflow_completed(self, run_id: str, final_resolution: Dict[str, Any]) -> bool:
        """Mark workflow as completed"""
        try:
            with self.SessionLocal() as session:
                workflow_state = session.query(WorkflowState).filter(
                    WorkflowState.run_id == run_id
                ).first()
                
                if workflow_state:
                    workflow_state.status = 'completed'
                    workflow_state.final_resolution = final_resolution
                    session.commit()
                    logger.info(f"Marked workflow {run_id} as completed")
                    return True
                else:
                    logger.error(f"Workflow state not found for run {run_id}")
                    return False
        except SQLAlchemyError as e:
            logger.error(f"Error marking workflow completed: {e}")
            return False
    
    def mark_workflow_failed(self, run_id: str, error_message: str) -> bool:
        """Mark workflow as failed"""
        try:
            with self.SessionLocal() as session:
                workflow_state = session.query(WorkflowState).filter(
                    WorkflowState.run_id == run_id
                ).first()
                
                if workflow_state:
                    workflow_state.status = 'failed'
                    workflow_state.error_message = error_message
                    session.commit()
                    logger.info(f"Marked workflow {run_id} as failed")
                    return True
                else:
                    logger.error(f"Workflow state not found for run {run_id}")
                    return False
        except SQLAlchemyError as e:
            logger.error(f"Error marking workflow failed: {e}")
            return False 