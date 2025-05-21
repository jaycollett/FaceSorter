"""Configuration handling for FaceSorter"""

import os
import json
import multiprocessing

# Constants for face recognition
FACE_ENCODING_MODELS = {
    "hog": "HOG (faster, less accurate)",
    "cnn": "CNN (slower, more accurate, GPU optimized)"
}
DEFAULT_MODEL = "hog"
DEFAULT_TOLERANCE = 0.6  # Standard tolerance
CHILDREN_TOLERANCE = 0.5  # Stricter tolerance for better child face discrimination

# Determine CPU core count for better default parallelism
CPU_COUNT = multiprocessing.cpu_count()

# Optimization settings
BATCH_SIZE = 16  # Default batch size for CNN model
BATCH_SIZE_SMALL = 4   # Smaller batch size for high-res images

# Optional caching of face encodings to avoid redundant processing
ENABLE_CACHE = True

# Size progression for multi-scale detection (for better performance)
SIZE_PROGRESSION = [500, 1000, 2000]  # Try smaller sizes first, gradually increase if needed

# Default configuration file path
DEFAULT_CONFIG_PATH = "config.json"

# Container path constants
CONTAINER_DATA_DIR = "/data"

def ensure_container_directories(config):
    """
    Ensure all necessary directories exist in the container
    
    Args:
        config: Configuration dictionary
    """
    # Check if we're running in Docker
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1"
    
    if not in_docker:
        # If not in Docker, no need to create container directories
        return
    
    # Create standard directories
    os.makedirs(f"{CONTAINER_DATA_DIR}/input", exist_ok=True)
    os.makedirs(f"{CONTAINER_DATA_DIR}/known_faces", exist_ok=True)
    os.makedirs(f"{CONTAINER_DATA_DIR}/output", exist_ok=True)
    os.makedirs(f"{CONTAINER_DATA_DIR}/cache", exist_ok=True)
    os.makedirs(f"{CONTAINER_DATA_DIR}/logs", exist_ok=True)
    os.makedirs(f"{CONTAINER_DATA_DIR}/sorted", exist_ok=True)
    
    # Create person-specific directories under /data/sorted only for people without custom paths
    for person in config["behavior"]["priority"]:
        # Only create a directory if the person doesn't have a custom path
        if person not in config["behavior"]["person_paths"]:
            person_dir = os.path.join(f"{CONTAINER_DATA_DIR}/sorted", person)
            os.makedirs(person_dir, exist_ok=True)

def load_config(config_path=DEFAULT_CONFIG_PATH):
    """
    Load configuration from a JSON file
    
    Args:
        config_path: Path to the configuration file (default: "config.json")
        
    Returns:
        Dictionary containing configuration values
    """
    # Default configuration
    default_config = {
        "directories": {
            "input": "unsorted",
            "known_faces": "known_faces",
            "output": "sorted",
            "cache": ".face_cache"
        },
        "recognition": {
            "model": "hog",
            "use_children_settings": True,
            "min_face_size": 20,
            "max_image_size": 2000
        },
        "performance": {
            "workers": None,
            "batch_size": None
            # Cache is now automatically controlled based on move_files setting
        },
        "behavior": {
            "priority": ["ana", "ethan", "gabe", "natalie"],
            "move_files": False,
            "recursive": False,  # Default to non-recursive processing
            "person_paths": {}  # Person-specific output paths
        },
        "logging": {
            "log_dir": f"{CONTAINER_DATA_DIR}/logs",
            "verbosity": "info"
        }
    }
    
    # Load config file if it exists
    config = default_config
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                
            # Update default config with file values
            def update_dict(d, u):
                for k, v in u.items():
                    if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                        d[k] = update_dict(d[k], v)
                    else:
                        d[k] = v
                return d
                
            config = update_dict(default_config, file_config)
            # No logging here - log isn't initialized yet
        except Exception as e:
            # Can't log here yet, just use print for critical errors
            print(f"Error loading configuration from {config_path}: {e}")
            print("Using default configuration")
    else:
        print(f"Configuration file {config_path} not found. Using default configuration.")
    
    # If running in Docker, use the container paths
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1"
    if in_docker:
        # Override with container paths
        config["directories"]["input"] = f"{CONTAINER_DATA_DIR}/input"
        config["directories"]["known_faces"] = f"{CONTAINER_DATA_DIR}/known_faces"
        config["directories"]["output"] = f"{CONTAINER_DATA_DIR}/output"
        config["directories"]["cache"] = f"{CONTAINER_DATA_DIR}/cache"
        config["logging"]["log_dir"] = f"{CONTAINER_DATA_DIR}/logs"
        
        # Create all necessary directories
        ensure_container_directories(config)
        
        # Map person-specific paths to /data/sorted/person_name
        for person in config["behavior"]["person_paths"]:
            config["behavior"]["person_paths"][person] = f"{CONTAINER_DATA_DIR}/sorted/{person}"
    
    return config
