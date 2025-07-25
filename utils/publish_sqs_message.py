"""
Send test messages to SQS for dispute resolution workflow testing
"""
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.service_factory import ServiceFactory
from utils.logging_config import init_logging, get_logger, console_print

load_dotenv()

init_logging()
logger = get_logger('scripts.publish_sqs_message')

def send_test_message():
    """
    Send a test message to SQS to trigger the dispute resolution workflow
    """
    aws_service = ServiceFactory.get_aws_service()
    
    # Create test event data
    case_id = "CASE-001-TEST-12345" 
    event_type = "billing_dispute"
    event_data = {
        "dispute_type": "billing_dispute", 
        "amount": 145678, 
        "customer_id": "ACC-001-DEMO-67890"
    }
    
    # Send message using AWS service
    message_id = aws_service.send_dispute_event(case_id, event_type, event_data)
    
    if message_id:
        logger.info("Message sent successfully")
        logger.info(f"Case ID: {case_id}")
        logger.info(f"Type: {event_data['dispute_type']}")
        logger.info(f"Amount: ${event_data['amount']}")
        logger.info(f"Message ID: {message_id}")
        
        console_print("Message sent successfully", "SUCCESS")
        console_print(f"Case ID: {case_id}", "SUCCESS")
        console_print(f"Type: {event_data['dispute_type']}", "SUCCESS")
        console_print(f"Amount: ${event_data['amount']}", "SUCCESS")
        console_print(f"Message ID: {message_id}", "SUCCESS")
    else:
        logger.error("Failed to send message")
        console_print("Failed to send message", "ERROR")

if __name__ == "__main__":
    console_print("Sending test message to SQS", "SUCCESS")
    logger.info("Sending test message to SQS")
    
    send_test_message()
    
    console_print("Test message sending completed", "SUCCESS")
    logger.info("Test message sending completed")
    
    console_print("Now you can run the workflow to process these messages:", "SUCCESS")
    console_print("python app.py", "SUCCESS")
    logger.info("Now you can run the workflow to process these messages:")
    logger.info("python app.py") 