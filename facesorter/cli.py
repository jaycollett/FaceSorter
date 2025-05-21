"""Command-line interface for FaceSorter"""

import argparse
import os
import sys

# Import from other modules
from .config import load_config
from .utils.logging import setup_logging, check_docker_environment, log
from .face_recognition.encoding import load_known_faces
from .image.sorting import sort_images

# We'll use the default logger from the logging module initially
# It will be properly configured in main() with settings from config

def parse_arguments():
    """
    Parse command-line arguments
    
    Returns:
        Parsed arguments object
    """
    parser = argparse.ArgumentParser(description="FaceSorter: Sort images based on face recognition")
    
    parser.add_argument(
        "--config", 
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )
    
    parser.add_argument(
        "--input", 
        help="Directory containing images to sort (overrides config file)"
    )
    
    parser.add_argument(
        "--known-faces", 
        help="Directory containing known face examples (overrides config file)"
    )
    
    parser.add_argument(
        "--output", 
        help="Base output directory for sorted images (overrides config file)"
    )
    
    parser.add_argument(
        "--model", 
        choices=["hog", "cnn"],
        help="Face detection model to use (overrides config file)"
    )
    
    parser.add_argument(
        "--move", 
        action="store_true",
        help="Move files instead of copying them (overrides config file)"
    )
    
    parser.add_argument(
        "--workers", 
        type=int,
        help="Number of worker threads for parallel processing (overrides config file)"
    )
    
    parser.add_argument(
        "--batch-size", 
        type=int,
        help="Number of images to process in a batch for CNN model (overrides config file)"
    )
    
    parser.add_argument(
        "--min-face-size", 
        type=int,
        help="Minimum face size to consider in pixels (overrides config file)"
    )
    
    parser.add_argument(
        "--max-image-size", 
        type=int,
        help="Maximum image dimension for processing (overrides config file)"
    )
    
    parser.add_argument(
        "--children", 
        action="store_true",
        help="Use settings optimized for children (overrides config file)"
    )
    
    parser.add_argument(
        "--log-level", 
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (overrides config file)"
    )
    
    parser.add_argument(
        "--cache-dir",
        help="Directory to store face encoding cache (overrides config file)"
    )
    
    parser.add_argument(
        "--priority",
        nargs="+",
        help="Priority list of person names (overrides config file)"
    )
    
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively process subdirectories (default: only process specified directory)"
    )
    
    return parser.parse_args()

def main():
    """
    Main entry point for FaceSorter CLI
    """
    # Check Docker environment
    check_docker_environment()
    
    # Parse command-line arguments
    args = parse_arguments()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command-line arguments if provided
    if args.input:
        config["directories"]["input"] = args.input
    if args.known_faces:
        config["directories"]["known_faces"] = args.known_faces
    if args.output:
        config["directories"]["output"] = args.output
    if args.cache_dir:
        config["directories"]["cache"] = args.cache_dir
    if args.model:
        config["recognition"]["model"] = args.model
    if args.move:
        config["behavior"]["move_files"] = True
    if args.workers is not None:
        config["performance"]["workers"] = args.workers
    if args.batch_size is not None:
        config["performance"]["batch_size"] = args.batch_size
    if args.min_face_size is not None:
        config["recognition"]["min_face_size"] = args.min_face_size
    if args.max_image_size is not None:
        config["recognition"]["max_image_size"] = args.max_image_size
    if args.children:
        config["recognition"]["use_children_settings"] = True
    if args.log_level:
        config["logging"]["verbosity"] = args.log_level
    if args.priority:
        config["behavior"]["priority"] = args.priority
    if args.recursive:
        config["behavior"]["recursive"] = True
    
    # Reconfigure logging with settings from config
    setup_logging(config["logging"]["verbosity"], config["logging"]["log_dir"])
    
    # Get directories from config
    input_dir = os.path.abspath(config["directories"]["input"])
    known_faces_dir = os.path.abspath(config["directories"]["known_faces"])
    output_dir = os.path.abspath(config["directories"]["output"])
    cache_dir = os.path.abspath(config["directories"]["cache"]) if "cache" in config["directories"] else None
    
    # Check if directories exist
    if not os.path.exists(input_dir):
        log.error(f"Input directory not found: {input_dir}")
        sys.exit(1)
    if not os.path.exists(known_faces_dir):
        log.error(f"Known faces directory not found: {known_faces_dir}")
        sys.exit(1)
    
    # Sort images
    sort_images(
        input_dir,
        output_dir,
        known_faces_dir,
        priority_list=config["behavior"]["priority"],
        use_children_settings=config["recognition"]["use_children_settings"],
        model=config["recognition"]["model"],
        min_face_size=config["recognition"]["min_face_size"],
        max_image_size=config["recognition"]["max_image_size"],
        move_files=config["behavior"]["move_files"],
        max_workers=config["performance"]["workers"],
        batch_size=config["performance"]["batch_size"],
        cache_dir=cache_dir,
        person_paths=config["behavior"]["person_paths"],
        recursive=config["behavior"]["recursive"]
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
