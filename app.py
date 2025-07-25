"""
Main application for dispute resolution workflow
"""
import os
import time
import socket
import sys
from pathlib import Path
from dotenv import load_dotenv

from workflows.dispute_workflow import DisputeWorkflow
from services.service_factory import ServiceFactory
from utils.logging_config import init_logging, get_logger, console_print

load_dotenv()

init_logging()
logger = get_logger('app')

def is_port_in_use(port: int, host: str = '127.0.0.1') -> bool:
    """
    Check if a port is already in use
    
    Args:
        port: Port number to check
        host: Host to check (default: 127.0.0.1)
        
    Returns:
        True if port is in use, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

def start_api_server():
    """
    Start the FastAPI server for human review API
    """
    import uvicorn
    
    console_print("Starting Dispute Resolution Workflow API Server", "SUCCESS")
    logger.info("Starting Dispute Resolution Workflow API Server")
    
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 8003))
    
    # Check if API is already running
    if is_port_in_use(port):
        console_print(f"API server is already running on port {port}", "WARNING")
        logger.warning(f"API server is already running on port {port}")
        return
    
    logger.info(f"Using port {port} from environment")
    logger.info("Available endpoints:")
    logger.info("   GET  / - Health check")
    logger.info("   GET  /health - Detailed health check")
    logger.info("   POST /workflow/start - Start new workflow")
    logger.info("   GET  /workflow/{run_id}/status - Get workflow status")
    logger.info("   GET  /workflow/case/{case_id} - Get workflows by case")
    logger.info("   POST /human-review/decision - Submit human review decision")
    logger.info("   GET  /human-review/pending - Get pending reviews")
    logger.info("   POST /workflow/{run_id}/continue - Continue workflow")
    
    console_print(f"Server will start on: http://{host}:{port}", "SUCCESS")
    console_print(f"API Documentation: http://{host}:{port}/docs", "SUCCESS")
    console_print(f"Interactive API: http://{host}:{port}/redoc", "SUCCESS")
    
    logger.info(f"Server starting on: http://{host}:{port}")
    logger.info(f"API Documentation: http://{host}:{port}/docs")
    logger.info(f"Interactive API: http://{host}:{port}/redoc")
    
    try:
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
            reload_dirs=["."]
        )
    except Exception as e:
        logger.error(f"Error starting API server: {e}")
        console_print(f"Error starting API server: {e}", "ERROR")

def main():
    """
    Main function to run the dispute resolution workflow
    """
    queue_url = os.getenv('DISPUTE_EVENTS_QUEUE_URL')
    
    if not queue_url:
        console_print("DISPUTE_EVENTS_QUEUE_URL environment variable not found", "ERROR")
        logger.error("DISPUTE_EVENTS_QUEUE_URL environment variable not found")
        return
    
    console_print("Starting dispute resolution workflow", "SUCCESS")
    logger.info("Starting dispute resolution workflow")
    logger.info(f"Queue URL: {queue_url}")
    
    # Get services from factory
    aws_service = ServiceFactory.get_aws_service()
    workflow = DisputeWorkflow()
    db_service = ServiceFactory.get_database_service()
    
    try:
        while True:
            try:
                # Receive messages using AWS service
                messages = aws_service.receive_messages(
                    queue_url=queue_url,
                    max_messages=1,
                    wait_time=5
                )
                
                if messages:
                    for message in messages:
                        event_data = eval(message['Body'])
                        
                        logger.info(f"Processing message: {message['MessageId']}")
                        logger.info(f"Case ID: {event_data.get('case_id')}")
                        logger.info(f"Event Type: {event_data.get('event_type')}")
                        
                        case_id = event_data.get('case_id')
                        # Customer ID is nested in event_data
                        customer_id = event_data.get('event_data', {}).get('customer_id')
                        
                        try:
                            run_id = workflow.start_workflow(case_id, customer_id)
                            logger.info(f"Workflow started with run_id: {run_id}")
                            
                            result = db_service.get_workflow_state(run_id)
                            
                            if result:
                                logger.info("Workflow executed successfully")
                                logger.info(f"Current step: {result.get('current_step', 'unknown')}")
                            else:
                                logger.warning(f"Workflow state not found for run_id: {run_id}")
                                
                        except Exception as workflow_error:
                            logger.error(f"Workflow execution error: {workflow_error}")
                            
                        # Delete message using AWS service
                        if aws_service.delete_message(queue_url, message['ReceiptHandle']):
                            logger.info("Message processed and deleted")
                        else:
                            logger.error("Failed to delete message")
                            
                    continue
                else:
                    logger.debug("No messages received")
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                time.sleep(5)
                
    except KeyboardInterrupt:
        console_print("Workflow stopped by user", "WARNING")
        logger.info("Workflow stopped by user")
        
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        console_print(f"Workflow error: {e}", "ERROR")

def run_single_workflow(case_id: str, customer_id: str = None):
    """
    Run a single workflow for testing purposes
    """
    console_print(f"Starting workflow for case: {case_id}", "SUCCESS")
    logger.info(f"Starting workflow for case: {case_id}")
    
    workflow = DisputeWorkflow()
    
    try:
        run_id = workflow.start_workflow(case_id, customer_id)
        logger.info("Workflow started successfully")
        logger.info(f"Run ID: {run_id}")
        logger.info(f"Case ID: {case_id}")
        
        console_print(f"Workflow completed successfully! Run ID: {run_id}", "SUCCESS")
        return run_id
        
    except Exception as e:
        logger.error(f"Error starting workflow: {e}")
        console_print(f"Error starting workflow: {e}", "ERROR")
        return None

def print_usage():
    """
    Print usage information
    """
    console_print("Usage:", "INFO")
    console_print("  python app.py                    - Start SQS message processing workflow", "INFO")
    console_print("  python app.py --api              - Start FastAPI server", "INFO")
    console_print("  python app.py --server           - Start FastAPI server (alias)", "INFO")
    console_print("  python app.py <case_id>          - Run single workflow", "INFO")
    console_print("  python app.py <case_id> <cust_id> - Run single workflow with customer ID", "INFO")
    console_print("  python app.py --help             - Show this help message", "INFO")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - run main workflow
        main()
    elif sys.argv[1] in ['--help', '-h']:
        # Help
        print_usage()
    elif sys.argv[1] in ['--api', '--server']:
        # Start API server
        start_api_server()
    else:
        # Run single workflow
        case_id = sys.argv[1]
        customer_id = sys.argv[2] if len(sys.argv) > 2 else None
        run_single_workflow(case_id, customer_id) 