"""
FastAPI Application for Dispute Resolution Workflow
"""
import os
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from services.service_factory import ServiceFactory
from workflows.dispute_workflow import DisputeWorkflow
from utils.logging_config import init_logging, get_logger

# Load environment variables
load_dotenv()

# Initialize centralized logging
init_logging()
logger = get_logger('api.main')

# Initialize FastAPI app
app = FastAPI(
    title="Dispute Resolution Workflow API",
    description="API for managing dispute resolution workflows and human reviews",
    version="1.0.0"
)

# Initialize services using factory (singleton pattern)
db_service = ServiceFactory.get_database_service()
workflow = DisputeWorkflow()

# Pydantic models
class HumanReviewDecision(BaseModel):
    run_id: str
    case_id: str
    decision: str  # "approved" or "rejected"
    comments: Optional[str] = None
    reviewer_name: Optional[str] = None
    modified_resolution: Optional[Dict[str, Any]] = None

class WorkflowStatus(BaseModel):
    run_id: str
    case_id: str
    status: str
    current_step: str
    human_review_data: Optional[Dict[str, Any]] = None

class DisputeEvent(BaseModel):
    case_id: str
    customer_id: Optional[str] = None
    event_type: str
    event_data: Dict[str, Any]

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Dispute Resolution Workflow API", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected",
            "workflow": "ready"
        }
    }

@app.post("/workflow/start")
async def start_workflow(dispute_event: DisputeEvent):
    """Start a new dispute resolution workflow"""
    try:
        logger.info(f"🚀 [API] Starting workflow for case: {dispute_event.case_id}")
        
        run_id = workflow.start_workflow(
            case_id=dispute_event.case_id,
            customer_id=dispute_event.customer_id
        )
        
        logger.info(f"✅ [API] Workflow started with run_id: {run_id}")
        
        return {
            "status": "success",
            "run_id": run_id,
            "case_id": dispute_event.case_id,
            "message": "Workflow started successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ [API] Error starting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflow/{run_id}/status")
async def get_workflow_status(run_id: str):
    """Get workflow status by run_id"""
    try:
        workflow_state = db_service.get_workflow_state(run_id)
        
        if not workflow_state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "run_id": run_id,
            "case_id": workflow_state.get('case_id'),
            "status": workflow_state.get('status'),
            "current_step": workflow_state.get('current_step'),
            "human_review_data": workflow_state.get('human_review_data'),
            "salesforce_data": workflow_state.get('salesforce_data'),
            "zuora_data": workflow_state.get('zuora_data'),
            "stripe_data": workflow_state.get('stripe_data'),
            "resolution_proposal": workflow_state.get('resolution_proposal'),
            "created_at": workflow_state.get('created_at'),
            "updated_at": workflow_state.get('updated_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error getting workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflow/case/{case_id}")
async def get_workflows_by_case(case_id: str):
    """Get all workflows for a specific case"""
    try:
        workflows = db_service.get_workflows_by_case(case_id)
        
        return {
            "case_id": case_id,
            "workflows": workflows,
            "count": len(workflows)
        }
        
    except Exception as e:
        logger.error(f"❌ [API] Error getting workflows for case: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/human-review/decision")
async def submit_human_review_decision(decision: HumanReviewDecision):
    """Submit human review decision and automatically continue workflow"""
    try:
        logger.info(f"👤 [API] Processing human review decision for run_id: {decision.run_id}")
        logger.info(f"📋 [API] Decision: {decision.decision}")
        
        # Validate decision
        if decision.decision not in ['approved', 'rejected']:
            raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")
        
        # Get current workflow state
        workflow_state = db_service.get_workflow_state(decision.run_id)
        
        if not workflow_state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if workflow_state.get('current_step') != 'wait_human_review':
            raise HTTPException(status_code=400, detail="Workflow is not waiting for human review")
        
        # Prepare human review data
        human_review_data = {
            'status': decision.decision,
            'comments': decision.comments,
            'reviewer_name': decision.reviewer_name,
            'reviewed_at': datetime.utcnow().isoformat(),
            'decision': decision.modified_resolution if decision.modified_resolution else workflow_state.get('resolution_proposal')
        }
        
        # Update workflow state with human review decision
        success = db_service.update_workflow_state(decision.run_id, {
            'human_review_data': human_review_data
        })
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update workflow state")
        
        logger.info(f"✅ [API] Human review decision recorded for run_id: {decision.run_id}")
        
        # Automatically continue the workflow
        logger.info(f"🔄 [API] Auto-continuing workflow after human decision for run_id: {decision.run_id}")
        
        try:
            workflow_resume_success = workflow.resume_workflow(decision.run_id)
            
            if workflow_resume_success:
                logger.info(f"✅ [API] Workflow automatically resumed for run_id: {decision.run_id}")
                
                # Get updated workflow state
                updated_workflow_state = db_service.get_workflow_state(decision.run_id)
                
                return {
                    "status": "success",
                    "run_id": decision.run_id,
                    "case_id": decision.case_id,
                    "decision": decision.decision,
                    "workflow_status": updated_workflow_state.get('status'),
                    "current_step": updated_workflow_state.get('current_step'),
                    "message": f"Human review decision recorded and workflow automatically continued"
                }
            else:
                logger.warning(f"⚠️ [API] Failed to auto-resume workflow for run_id: {decision.run_id}")
                return {
                    "status": "partial_success",
                    "run_id": decision.run_id,
                    "case_id": decision.case_id,
                    "decision": decision.decision,
                    "message": "Human review decision recorded but workflow continuation failed"
                }
                
        except Exception as workflow_error:
            logger.error(f"❌ [API] Error auto-continuing workflow: {workflow_error}")
            return {
                "status": "partial_success",
                "run_id": decision.run_id,
                "case_id": decision.case_id,
                "decision": decision.decision,
                "message": f"Human review decision recorded but workflow continuation failed: {str(workflow_error)}"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error processing human review decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/human-review/pending")
async def get_pending_reviews():
    """Get all workflows waiting for human review"""
    try:
        # This would query the database for workflows in 'wait_human_review' state
        # For now, return a placeholder
        return {
            "pending_reviews": [],
            "count": 0,
            "message": "No pending reviews found"
        }
        
    except Exception as e:
        logger.error(f"❌ [API] Error getting pending reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflow/{run_id}/continue")
async def continue_workflow(run_id: str):
    """Continue a workflow from its current state (for manual triggering)"""
    try:
        logger.info(f"🔄 [API] Continuing workflow for run_id: {run_id}")
        
        # Get current workflow state
        workflow_state = db_service.get_workflow_state(run_id)
        
        if not workflow_state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Resume the workflow using the resume_workflow function
        success = workflow.resume_workflow(run_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to resume workflow")
        
        # Get updated workflow state
        updated_workflow_state = db_service.get_workflow_state(run_id)
        
        return {
            "status": "success",
            "run_id": run_id,
            "current_step": updated_workflow_state.get('current_step'),
            "workflow_status": updated_workflow_state.get('status'),
            "message": "Workflow resumed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error continuing workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/llm/metrics")
async def get_llm_metrics():
    """Get LLM service metrics for monitoring"""
    try:
        llm_service = workflow.llm
        metrics = llm_service.get_metrics()
        
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [API] Error getting LLM metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/llm/health")
async def get_llm_health():
    """Get LLM service health status"""
    try:
        llm_service = workflow.llm
        health_status = llm_service.health_check()
        
        return health_status
        
    except Exception as e:
        logger.error(f"❌ [API] Error getting LLM health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/llm/cache/clear")
async def clear_llm_cache():
    """Clear LLM cache (for testing/debugging)"""
    try:
        llm_service = workflow.llm
        llm_service.clear_cache()
        
        return {
            "status": "success",
            "message": "LLM cache cleared successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [API] Error clearing LLM cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/services/health")
async def get_all_services_health():
    """Get health status of all services"""
    try:
        # Get LLM service health
        llm_service = workflow.llm
        llm_health = llm_service.health_check()
        
        # Get database connectivity
        db_health = {"service": "DatabaseService", "status": "healthy"}
        try:
            db_service.get_session()
        except Exception as e:
            db_health["status"] = "unhealthy"
            db_health["error"] = str(e)
        
        # Get vector service health
        vector_health = {"service": "VectorService", "status": "healthy"}
        try:
            workflow.vector_db.health_check()
        except Exception as e:
            vector_health["status"] = "unhealthy"
            vector_health["error"] = str(e)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "llm": llm_health,
                "database": db_health,
                "vector": vector_health
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [API] Error getting services health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/costs/workflow/{run_id}")
async def get_workflow_costs(run_id: str):
    """Get cost information for a specific workflow"""
    try:
        workflow_state = db_service.get_workflow_state(run_id)
        
        if not workflow_state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "status": "success",
            "run_id": run_id,
            "case_id": workflow_state.get('case_id'),
            "costs": {
                "llm_cost": workflow_state.get('llm_cost', 0.0),
                "total_cost": workflow_state.get('total_cost', 0.0),
                "cost_breakdown": workflow_state.get('cost_breakdown', {})
            },
            "workflow_status": workflow_state.get('status'),
            "created_at": workflow_state.get('created_at'),
            "completed_at": workflow_state.get('completed_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error getting workflow costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/costs/case/{case_id}")
async def get_case_costs(case_id: str):
    """Get total cost information for all workflows of a specific case"""
    try:
        workflows = db_service.get_workflows_by_case(case_id)
        
        if not workflows:
            raise HTTPException(status_code=404, detail="No workflows found for case")
        
        total_llm_cost = 0.0
        total_cost = 0.0
        workflow_costs = []
        
        for workflow in workflows:
            llm_cost = workflow.get('llm_cost', 0.0)
            total_workflow_cost = workflow.get('total_cost', 0.0)
            
            total_llm_cost += llm_cost
            total_cost += total_workflow_cost
            
            workflow_costs.append({
                "run_id": workflow.get('run_id'),
                "llm_cost": llm_cost,
                "total_cost": total_workflow_cost,
                "status": workflow.get('status'),
                "created_at": workflow.get('created_at')
            })
        
        return {
            "status": "success",
            "case_id": case_id,
            "summary": {
                "total_llm_cost": total_llm_cost,
                "total_cost": total_cost,
                "workflow_count": len(workflows)
            },
            "workflows": workflow_costs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error getting case costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/costs/summary")
async def get_cost_summary(limit: int = 100):
    """Get cost summary across all workflows"""
    try:
        # This would require a new database method to get cost aggregations
        # For now, return a placeholder structure
        return {
            "status": "success",
            "message": "Cost summary endpoint - requires database aggregation implementation",
            "note": "This endpoint needs a new database method to aggregate costs across all workflows",
            "suggested_implementation": {
                "total_workflows": "COUNT(*)",
                "total_llm_cost": "SUM(llm_cost)",
                "total_cost": "SUM(total_cost)",
                "average_cost_per_workflow": "AVG(total_cost)",
                "cost_by_date": "GROUP BY DATE(created_at)",
                "most_expensive_workflows": "ORDER BY total_cost DESC LIMIT 10"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [API] Error getting cost summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/costs/metrics")
async def get_cost_metrics():
    """Get cost metrics including LLM service metrics"""
    try:
        # Get LLM metrics
        llm_service = workflow.llm
        llm_metrics = llm_service.get_metrics()
        
        # Calculate cost efficiency metrics
        total_calls = llm_metrics.get('calls_made', 0)
        cache_hits = llm_metrics.get('cache_hits', 0)
        fallback_used = llm_metrics.get('fallback_used', 0)
        
        cost_savings_from_cache = cache_hits * 0.001  # Estimated savings per cached call
        cost_avoidance_from_fallback = fallback_used * 0.001  # Estimated cost avoidance
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "llm_metrics": llm_metrics,
            "cost_efficiency": {
                "cache_hit_rate": cache_hits / max(total_calls, 1),
                "estimated_cache_savings": cost_savings_from_cache,
                "fallback_rate": fallback_used / max(total_calls, 1),
                "estimated_cost_avoidance": cost_avoidance_from_fallback,
                "total_estimated_savings": cost_savings_from_cache + cost_avoidance_from_fallback
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [API] Error getting cost metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 