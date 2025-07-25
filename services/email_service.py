"""
Simple Email Service for Gmail notifications
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

from utils.logging_config import get_logger

logger = get_logger('services.email')

class EmailService:
    """
    Simple email service for sending Gmail notifications
    """
    
    def __init__(self):
        """Initialize email service with Gmail SMTP settings"""
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv('GMAIL_EMAIL')
        self.sender_password = os.getenv('GMAIL_APP_PASSWORD')  # Use app password, not regular password
        self.approver_email = os.getenv('APPROVER_EMAIL', self.sender_email)
        
    def send_approval_request(self, case_data: Dict[str, Any], run_id: str) -> bool:
        """
        Send email to approver with resolution details
        
        Args:
            case_data: Dictionary containing case information
            run_id: Workflow run ID for approval
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.sender_email or not self.sender_password:
                logger.warning("Gmail credentials not configured - skipping email")
                return False
            
            # Extract case details
            case_id = case_data.get('case_id', 'Unknown')
            customer_name = case_data.get('customer_name', 'Unknown Customer')
            dispute_type = case_data.get('dispute_type', 'Unknown')
            amount = case_data.get('amount', 0)
            resolution = case_data.get('resolution', {})
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.approver_email
            msg['Subject'] = f"Dispute Approval Required - Case {case_id}"
            
            # Create email body
            body = f"""
            <html>
            <body>
                <h2>🔍 Dispute Resolution Approval Required</h2>
                
                <h3>Case Details:</h3>
                <ul>
                    <li><strong>Case ID:</strong> {case_id}</li>
                    <li><strong>Customer:</strong> {customer_name}</li>
                    <li><strong>Dispute Type:</strong> {dispute_type}</li>
                    <li><strong>Amount:</strong> ${amount}</li>
                </ul>
                
                <h3>AI Recommended Resolution:</h3>
                <ul>
                    <li><strong>Action:</strong> {resolution.get('action', 'Unknown')}</li>
                    <li><strong>Amount:</strong> ${resolution.get('amount', 0)}</li>
                    <li><strong>Reason:</strong> {resolution.get('reason', 'No reason provided')}</li>
                    <li><strong>Confidence:</strong> {resolution.get('confidence', 0)}%</li>
                </ul>
                
                <h3>📝 Next Steps:</h3>
                <p>Please review and approve/reject this resolution:</p>
                <p><strong>API Endpoint:</strong> http://localhost:8003/human-review/decision</p>
                <p><strong>Run ID:</strong> {run_id}</p>
                
                <hr>
                <p><em>This is an automated notification from the Dispute Resolution System.</em></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"📧 Approval email sent for case {case_id} to {self.approver_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send approval email: {e}")
            return False
    
    def send_resolution_complete(self, case_data: Dict[str, Any], run_id: str, decision: str) -> bool:
        """
        Send email notification when resolution is complete
        
        Args:
            case_data: Dictionary containing case information
            run_id: Workflow run ID
            decision: approved/rejected
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.sender_email or not self.sender_password:
                logger.warning("Gmail credentials not configured - skipping email")
                return False
            
            case_id = case_data.get('case_id', 'Unknown')
            customer_name = case_data.get('customer_name', 'Unknown Customer')
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.approver_email
            msg['Subject'] = f"Dispute Resolution Complete - Case {case_id}"
            
            status_emoji = "✅" if decision == "approved" else "❌"
            status_text = "APPROVED" if decision == "approved" else "REJECTED"
            
            body = f"""
            <html>
            <body>
                <h2>{status_emoji} Dispute Resolution Complete</h2>
                
                <h3>Case Details:</h3>
                <ul>
                    <li><strong>Case ID:</strong> {case_id}</li>
                    <li><strong>Customer:</strong> {customer_name}</li>
                    <li><strong>Status:</strong> {status_text}</li>
                    <li><strong>Run ID:</strong> {run_id}</li>
                </ul>
                
                <p>The dispute resolution workflow has been completed successfully.</p>
                
                <hr>
                <p><em>This is an automated notification from the Dispute Resolution System.</em></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"📧 Completion email sent for case {case_id} to {self.approver_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send completion email: {e}")
            return False 