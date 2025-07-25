"""
Setup script for the Dispute Resolution Workflow MVP
"""
import os
import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Try to import required modules, install if missing
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    from utils.logging_config import init_logging, get_logger, console_print
    
    # Force console logging for setup
    os.environ['LOG_TO_CONSOLE'] = 'true'
    init_logging()
    logger = get_logger('setup')
    LOGGING_AVAILABLE = True
except ImportError:
    # Dependencies not installed yet, use basic print
    logger = None
    LOGGING_AVAILABLE = False
    
    def console_print(message, level="INFO"):
        if level == "ERROR":
            print(f" ERROR: {message}")
        elif level == "WARNING":
            print(f"  WARNING: {message}")
        elif level == "SUCCESS":
            print(f" SUCCESS: {message}")
        else:
            print(f" INFO: {message}")
    
    def get_logger(name):
        return None

def run_command(command, description):
    """Run a command with proper logging"""
    if logger:
        logger.info(f"Running: {description}")
    console_print(f"Running: {description}", "INFO")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        if logger:
            logger.info(f"{description} completed successfully")
        console_print(f"{description} completed successfully", "SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        if logger:
            logger.error(f"{description} failed: {e}")
            logger.error(f"Error output: {e.stderr}")
        console_print(f"{description} failed: {e}", "ERROR")
        return False

def check_postgresql():
    """Check if PostgreSQL is accessible"""
    try:
        import psycopg2
        database_url = os.getenv('POSTGRES_URL')
        if not database_url:
            console_print("POSTGRES_URL not found in .env file", "ERROR")
            return False
        
        # Try to connect to postgres database first
        postgres_url = database_url.replace(database_url.split('/')[-1], 'postgres')
        conn = psycopg2.connect(postgres_url)
        conn.close()
        console_print("PostgreSQL connection successful", "SUCCESS")
        return True
    except Exception as e:
        console_print(f"PostgreSQL connection failed: {e}", "ERROR")
        console_print("Please ensure PostgreSQL is installed and running", "ERROR")
        return False

def check_prerequisites():
    """Check if all prerequisites are met"""
    if logger:
        logger.info("Checking prerequisites")
    console_print("Checking prerequisites", "INFO")
    
    # Check Python version
    if sys.version_info < (3, 11):
        if logger:
            logger.error("Python 3.11+ is required")
        console_print("Python 3.11+ is required", "ERROR")
        return False
    
    # Check .env file exists
    if not os.path.exists('.env'):
        if logger:
            logger.error(".env file not found. Please create it with your configuration.")
        console_print(".env file not found. Please copy env.example to .env and configure it.", "ERROR")
        return False
    
    # Check virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        if logger:
            logger.error("Virtual environment not activated. Please activate it first.")
        console_print("Virtual environment not activated. Please activate it first.", "ERROR")
        return False
    
    # Check PostgreSQL (only if dependencies are available)
    if LOGGING_AVAILABLE and not check_postgresql():
        return False
    
    if logger:
        logger.info("Prerequisites check passed")
    console_print("Prerequisites check passed", "SUCCESS")
    return True

def setup_project():
    """Set up the project"""
    global logger
    
    if logger:
        logger.info("Setting up Dispute Resolution Workflow ")
    console_print("Setting up Dispute Resolution Workflow ", "SUCCESS")
    
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Re-import modules after installing dependencies
    if not LOGGING_AVAILABLE:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            from utils.logging_config import init_logging, get_logger
            
            # Force console logging for setup
            os.environ['LOG_TO_CONSOLE'] = 'true'
            init_logging()
            logger = get_logger('setup')
            console_print("✅ Dependencies installed, logging now available", "SUCCESS")
        except ImportError:
            console_print("⚠️  Warning: Could not initialize logging after dependency installation", "WARNING")
    
    os.makedirs("logs", exist_ok=True)
    if logger:
        logger.info("Created logs directory")
    
    if not run_command("python utils/setup_database.py", "Setting up PostgreSQL database"):
        return False
    
    if not run_command("python utils/seed_vector_db.py", "Seeding ChromaDB with sample data"):
        return False
    
    if logger:
        logger.info("Setup completed successfully")
    console_print("Setup completed successfully", "SUCCESS")
    
    console_print("Next steps:", "INFO")
    console_print("1. Send test messages: python utils/publish_sqs_message.py", "INFO")
    console_print("2. Start workflow listener: python app.py", "INFO")
    console_print("3. Start human review API: python app.py --api", "INFO")
    console_print("4. Or trigger workflow manually: python app.py SF-2024-001", "INFO")
    
    return True

def test_system():
    """Test the system with a sample message"""
    if logger:
        logger.info("Testing the system")
    console_print("Testing the system", "INFO")
    
    if not run_command("python utils/publish_sqs_message.py", "Sending test SQS message"):
        return False
    
    if logger:
        logger.info("System test completed")
    console_print("System test completed", "SUCCESS")
    console_print("Check the logs to see if the workflow processed the message correctly.", "INFO")
    
    return True

def main():
    """Main setup function"""
    console_print("Dispute Resolution Workflow Setup", "SUCCESS")
    if logger:
        logger.info("Dispute Resolution Workflow Setup")
    
    if not check_prerequisites():
        return False
    
    if not setup_project():
        return False
    
    if not test_system():
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 