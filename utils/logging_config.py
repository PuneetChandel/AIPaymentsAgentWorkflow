"""
Centralized Logging Configuration for PaymentsAgentWorkflow
"""
import os
import logging
import logging.handlers
from pathlib import Path

def setup_logging() -> logging.Logger:
    """
    Setup centralized logging configuration from environment variables
    """
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_to_file = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    log_to_console = os.getenv('LOG_TO_CONSOLE', 'false').lower() == 'true'
    log_file_path = os.getenv('LOG_FILE_PATH', 'logs/workflow.log')
    log_file_max_size = int(os.getenv('LOG_FILE_MAX_SIZE', '10485760'))
    log_file_backup_count = int(os.getenv('LOG_FILE_BACKUP_COUNT', '5'))
    log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    formatter = logging.Formatter(log_format)
    handlers = []
    
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        handlers.append(console_handler)
    
    if log_to_file:
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=log_file_max_size,
            backupCount=log_file_backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)
    
    if not handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        handlers.append(console_handler)
    
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True
    )
    
    logger = logging.getLogger('paymentsagent')
    logger.info("Centralized logging configured")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Console logging: {'enabled' if log_to_console else 'disabled'}")
    
    if log_to_file:
        logger.info("File logging enabled")
        logger.info(f"Log file: {log_path}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    """
    return logging.getLogger(f'paymentsagent.{name}')

def console_print(message: str, level: str = 'INFO'):
    """
    Print essential messages to console
    """
    if level.upper() == 'ERROR':
        print(f"ERROR: {message}")
    elif level.upper() == 'WARNING':
        print(f"WARNING: {message}")
    elif level.upper() == 'SUCCESS':
        print(f"SUCCESS: {message}")
    else:
        print(f"INFO: {message}")

_root_logger = None

def init_logging():
    """Initialize logging configuration once"""
    global _root_logger
    if _root_logger is None:
        _root_logger = setup_logging()
    return _root_logger 