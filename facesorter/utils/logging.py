"""Logging utilities for FaceSorter"""

import os
import sys
import logging
from datetime import datetime

# --- DOCKER ENVIRONMENT CHECK ---
def check_docker_environment():
    """Ensure this script is ONLY run inside the Docker container"""
    # Check if running in Docker
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1"
    
    # Set environment variable for other parts of the application
    if in_docker and os.environ.get("IN_DOCKER") != "1":
        os.environ["IN_DOCKER"] = "1"
    
    # If we're not in Docker, check if we're being run directly
    # This prevents log files from being created in unexpected places
    if not in_docker:
        # Check if we're being run via the run_facesorter.sh script
        # The script sets up proper Docker environment
        script_run = False
        
        # Check if we're being run from the run_facesorter.sh script
        # by checking if the parent process is bash and running run_facesorter.sh
        try:
            import psutil
            current_process = psutil.Process()
            parent = current_process.parent()
            if parent and 'bash' in parent.name().lower():
                script_run = True
        except (ImportError, psutil.Error):
            # If psutil is not available, we can't check the parent process
            # Just assume we're not being run from the script
            pass
        
        if not script_run:
            sys.stderr.write("\nERROR: FaceSorter must be run inside the Docker container.\n"
                            "Do NOT run main.py directly on the host.\n"
                            "Run the FaceSorter via the run_facesorter.sh script.\n\n")
            sys.exit(2)
    
    return in_docker

# Global flag to track if logging has been initialized
_logging_initialized = False

# Create a logger with a NullHandler to prevent logs from going to the root logger
# This temporary logger will be properly configured in setup_logging
log = logging.getLogger("facesorter")
log.addHandler(logging.NullHandler())
log.propagate = False  # Prevent propagation to root logger

# Disable the root logger to prevent any logs from appearing in unexpected places
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger().addHandler(logging.NullHandler())

def setup_logging(log_level="INFO", log_dir="/data/logs"):
    """Set up logging to file and console
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files (in Docker, always use /data/logs)
        
    Returns:
        Configured logger
    """
    global log, _logging_initialized
    
    # If logging has already been initialized, just return the existing logger
    # but update the log level if it has changed
    if _logging_initialized:
        # Set numeric log level if it has changed
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.INFO
            
        if log.level != numeric_level:
            log.setLevel(numeric_level)
            log.debug(f"Updated log level to {log_level}")
        else:
            log.debug("Logging already initialized, reusing existing logger")
        return log
    
    # In Docker environment, always use /data/logs regardless of config
    # This is because the Docker container maps the host log directory to /data/logs
    if os.environ.get("IN_DOCKER") == "1":
        log_dir = "/data/logs"
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Set up logging to file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"facesorter_{timestamp}.log")
    
    # Configure logging
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Add a header to the log file if it's new or empty
    if not os.path.exists(log_file) or os.path.getsize(log_file) == 0:
        with open(log_file, 'a') as f:
            f.write(f"===== FaceSorter Log Started at {datetime.now().strftime(date_format)} =====\n\n")
    
    # Set numeric log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    # Get the existing logger
    logger = logging.getLogger("facesorter")
    
    # Remove all existing handlers
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)
    
    # Set log level
    logger.setLevel(numeric_level)
    
    # Set the global log variable
    log = logger
    
    # Mark logging as initialized
    _logging_initialized = True
    
    # Log initialization
    log.info(f"Logging initialized at level {log_level}")
    log.info(f"Log file: {log_file}")
    
    return log

def flush_logs():
    """Force logger to write to disk"""
    for handler in logging.getLogger("facesorter").handlers:
        if isinstance(handler, logging.FileHandler):
            handler.flush()
