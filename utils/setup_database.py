"""
Database setup script for the dispute resolution workflow
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import urlparse

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

from utils.logging_config import init_logging, get_logger, console_print
init_logging()
logger = get_logger('scripts.setup_database')

def setup_database():
    """
    Set up the PostgreSQL database for the dispute resolution workflow
    """
    database_url = os.getenv('POSTGRES_URL')
    
    if not database_url:
        console_print("POSTGRES_URL environment variable not found", "ERROR")
        logger.error("POSTGRES_URL environment variable not found")
        return False
    
    parsed_url = urlparse(database_url)
    database_name = parsed_url.path.lstrip('/')
    
    postgres_url = database_url.replace(f'/{database_name}', '/postgres')
    
    try:
        postgres_engine = create_engine(postgres_url)
        
        with postgres_engine.connect() as conn:
            conn.execute(text("COMMIT"))
            
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{database_name}'"))
            if not result.fetchone():
                logger.info(f"Creating database: {database_name}")
                conn.execute(text(f"CREATE DATABASE {database_name}"))
                logger.info(f"Database {database_name} created successfully")
                console_print(f"Database {database_name} created successfully", "SUCCESS")
            else:
                logger.info(f"Database {database_name} already exists")
                console_print(f"Database {database_name} already exists", "SUCCESS")
        
        postgres_engine.dispose()
        
        target_engine = create_engine(database_url)
        
        with target_engine.connect() as conn:
            logger.info("Creating workflow_states table")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS workflow_states (
                    id SERIAL PRIMARY KEY,
                    run_id VARCHAR(255) UNIQUE NOT NULL,
                    case_id VARCHAR(255) NOT NULL,
                    customer_id VARCHAR(255),
                    current_step VARCHAR(100),
                    status VARCHAR(50),
                    salesforce_data JSONB,
                    zuora_data JSONB,
                    stripe_data JSONB,
                    resolution_proposal JSONB,
                    human_review_data JSONB,
                    final_resolution JSONB,
                    error_message TEXT,
                    llm_cost DECIMAL(10, 4) DEFAULT 0.0,
                    cost_breakdown JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            logger.info("Creating indexes")
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_states_run_id ON workflow_states(run_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_states_case_id ON workflow_states(case_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_states_customer_id ON workflow_states(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_states_status ON workflow_states(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_states_current_step ON workflow_states(current_step)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_states_created_at ON workflow_states(created_at)"))
            
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """))
            
            conn.execute(text("""
                DROP TRIGGER IF EXISTS update_workflow_states_updated_at ON workflow_states;
                CREATE TRIGGER update_workflow_states_updated_at
                    BEFORE UPDATE ON workflow_states
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column()
            """))
            
            logger.info("Adding column comments")
            conn.execute(text("""
                COMMENT ON COLUMN workflow_states.llm_cost IS 'Total cost of LLM API calls for this workflow run';
                COMMENT ON COLUMN workflow_states.cost_breakdown IS 'Detailed breakdown of costs by service';
                COMMENT ON COLUMN workflow_states.salesforce_data IS 'Data fetched from Salesforce';
                COMMENT ON COLUMN workflow_states.zuora_data IS 'Data fetched from Zuora';
                COMMENT ON COLUMN workflow_states.stripe_data IS 'Data fetched from Stripe';
                COMMENT ON COLUMN workflow_states.resolution_proposal IS 'AI-generated resolution proposal';
                COMMENT ON COLUMN workflow_states.human_review_data IS 'Human review decision and comments';
                COMMENT ON COLUMN workflow_states.final_resolution IS 'Final resolution after human approval'
            """))
            
            conn.commit()
            
        target_engine.dispose()
        
        logger.info("Database setup completed successfully")
        console_print("Database setup completed successfully", "SUCCESS")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error setting up database: {e}")
        console_print(f"Error setting up database: {e}", "ERROR")
        return False

def main():
    """
    Main function to set up the database
    """
    console_print("Setting up PostgreSQL database with cost tracking", "SUCCESS")
    logger.info("Setting up PostgreSQL database with cost tracking")
    
    try:
        success = setup_database()
        
        if not success:
            console_print("Database setup failed", "ERROR")
            return
        
        console_print("Database setup completed successfully", "SUCCESS")
        logger.info("Database setup completed successfully")
        
        logger.info("Available features:")
        logger.info("- Workflow state tracking")
        logger.info("- Cost tracking for LLM API calls")
        logger.info("- Comprehensive cost breakdown")
        logger.info("- Database indexes for performance")
        logger.info("Next steps:")
        logger.info("1. Start the application with: python app.py")
        logger.info("2. Monitor costs via API endpoints:")
        logger.info("   - GET /costs/workflow/{run_id}")
        logger.info("   - GET /costs/case/{case_id}")
        
    except Exception as e:
        logger.error(f"Unexpected error during database setup: {e}")
        console_print(f"Unexpected error during database setup: {e}", "ERROR")

if __name__ == "__main__":
    main() 

    