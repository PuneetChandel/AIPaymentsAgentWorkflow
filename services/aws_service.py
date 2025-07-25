"""
AWS Service for handling SQS operations
"""
import os
import json
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

from utils.logging_config import get_logger

logger = get_logger('services.aws')

class AWSService:
    """
    Service for AWS operations, primarily SQS messaging
    """
    
    def __init__(self):
        """Initialize AWS service with SQS client"""
        self.sqs = boto3.client('sqs')
        self.dispute_events_queue_url = os.getenv('DISPUTE_EVENTS_QUEUE_URL')
        self.human_review_notifications_queue_url = os.getenv('HUMAN_REVIEW_NOTIFICATIONS_QUEUE_URL')
        
        logger.info("AWS Service initialized")
        
        if not self.dispute_events_queue_url:
            logger.warning("DISPUTE_EVENTS_QUEUE_URL not configured")
        if not self.human_review_notifications_queue_url:
            logger.warning("HUMAN_REVIEW_NOTIFICATIONS_QUEUE_URL not configured")
    
    def send_message(self, queue_url: str, message_body: Dict[str, Any]) -> Optional[str]:
        """
        Send a message to an SQS queue
        
        Args:
            queue_url: The URL of the SQS queue
            message_body: The message body as a dictionary
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            response = self.sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message_body)
            )
            
            message_id = response['MessageId']
            logger.info(f"Message sent to SQS queue: {message_id}")
            return message_id
            
        except ClientError as e:
            logger.error(f"Error sending message to SQS: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending message to SQS: {e}")
            return None
    
    def send_human_review_notification(self, review_request: Dict[str, Any]) -> Optional[str]:
        """
        Send a human review notification to the human review queue
        
        Args:
            review_request: The review request data
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.human_review_notifications_queue_url:
            logger.error("Human review notifications queue URL not configured")
            return None
        
        message_id = self.send_message(
            self.human_review_notifications_queue_url,
            review_request
        )
        
        if message_id:
            logger.info(f"Human review notification sent: {message_id}")
            logger.info(f"Case ID: {review_request.get('case_id')}")
            logger.info(f"Customer: {review_request.get('case_summary', {}).get('customer_name', 'Unknown')}")
        
        return message_id
    
    def send_dispute_event(self, case_id: str, event_type: str, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Send a dispute event to the dispute events queue
        
        Args:
            case_id: The case ID
            event_type: Type of event (e.g., 'billing_dispute')
            event_data: Additional event data
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.dispute_events_queue_url:
            logger.error("Dispute events queue URL not configured")
            return None
        
        message_body = {
            "case_id": case_id,
            "event_type": event_type,
            "event_data": event_data
        }
        
        message_id = self.send_message(
            self.dispute_events_queue_url,
            message_body
        )
        
        if message_id:
            logger.info(f"Dispute event sent: {message_id}")
            logger.info(f"Case ID: {case_id}")
            logger.info(f"Event Type: {event_type}")
        
        return message_id
    
    def receive_messages(self, queue_url: str, max_messages: int = 1, wait_time: int = 5) -> list:
        """
        Receive messages from an SQS queue
        
        Args:
            queue_url: The URL of the SQS queue
            max_messages: Maximum number of messages to receive (1-10)
            wait_time: Long polling wait time in seconds
            
        Returns:
            List of messages
        """
        try:
            response = self.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time
            )
            
            messages = response.get('Messages', [])
            logger.debug(f"Received {len(messages)} messages from queue")
            return messages
            
        except ClientError as e:
            logger.error(f"Error receiving messages from SQS: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error receiving messages from SQS: {e}")
            return []
    
    def delete_message(self, queue_url: str, receipt_handle: str) -> bool:
        """
        Delete a message from an SQS queue
        
        Args:
            queue_url: The URL of the SQS queue
            receipt_handle: The receipt handle of the message to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info("Message deleted from queue")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting message from SQS: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting message from SQS: {e}")
            return False
    
 