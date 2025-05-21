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
    
    # Removed known-faces argument as we now use person-specific paths
    
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
        "--person",
        action="append",
        help="Person configuration in format 'name:birthdate:priority:output_path'. Can be specified multiple times. Example: --person 'ana:2010-05-15:1:/path/to/ana/photos'"
    )
    
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively process subdirectories (default: only process specified directory)"
    )
    
    parser.add_argument(
        "--age-based-matching",
        action="store_true",
        help="Enable age-based face matching using birthdates (overrides config file)"
    )
    
    parser.add_argument(
        "--age-tolerance",
        type=int,
        help="Age tolerance in years for age-based matching (overrides config file)"
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
    # Removed known_faces override as we now use person-specific paths
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
        config["behavior"]["recursive_search"] = True
    if args.age_based_matching:
        config["recognition"]["age_based_matching"] = True
    if args.age_tolerance is not None:
        config["recognition"]["age_tolerance"] = args.age_tolerance
    
    # Reconfigure logging with settings from config
    setup_logging(config["logging"]["verbosity"], config["logging"]["log_dir"])
    
    # Get directories from config
    input_dir = os.path.abspath(config["directories"]["input"])
    # Output directory is now optional since we use person-specific output paths
    output_dir = os.path.abspath(config["directories"].get("output", ""))
    cache_dir = os.path.abspath(config["directories"]["cache"]) if "cache" in config["directories"] else None
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        log.error(f"Input directory not found: {input_dir}")
        sys.exit(1)
    
    # Process people configuration to extract priority list, birthdates, and person paths
    people_config = config.get("people", {})
    
    # Override with command-line person configurations if provided
    if args.person:
        if "people" not in config:
            config["people"] = {}
            
        for person_str in args.person:
            parts = person_str.split(":")
            if len(parts) >= 1:
                name = parts[0]
                if name not in config["people"]:
                    config["people"][name] = {}
                
                # Add birthdate if provided
                if len(parts) >= 2 and parts[1]:
                    config["people"][name]["birthdate"] = parts[1]
                
                # Add priority if provided
                if len(parts) >= 3 and parts[2]:
                    try:
                        config["people"][name]["priority"] = int(parts[2])
                    except ValueError:
                        log.warning(f"Invalid priority value for {name}: {parts[2]}")
                
                # Add output path if provided
                if len(parts) >= 4 and parts[3]:
                    config["people"][name]["output_path"] = parts[3]
                    
                # Add faces path if provided
                if len(parts) >= 5 and parts[4]:
                    config["people"][name]["faces_path"] = parts[4]
    
    # Refresh people_config after potential updates
    people_config = config.get("people", {})
    
    # Create priority list based on priority values
    priority_list = sorted(people_config.keys(), 
                           key=lambda name: people_config[name].get("priority", 999))
    
    # Override priority list with command-line argument if provided
    if args.priority:
        priority_list = args.priority
    
    # Create birthdates dictionary
    birthdates = {name: person_data.get("birthdate") 
                 for name, person_data in people_config.items() 
                 if "birthdate" in person_data}
    
    # Create person paths dictionary
    person_paths = {name: person_data.get("output_path") 
                   for name, person_data in people_config.items() 
                   if "output_path" in person_data}
    
    # Sort images
    sort_images(
        input_dir,
        output_dir,
        people_config=people_config,
        priority_list=priority_list,
        use_children_settings=config["recognition"]["use_children_settings"],
        model=config["recognition"]["model"],
        min_face_size=config["recognition"]["min_face_size"],
        max_image_size=config["recognition"]["max_image_size"],
        move_files=config["behavior"]["move_files"],
        max_workers=config["performance"]["workers"],
        batch_size=config["performance"]["batch_size"],
        cache_dir=cache_dir,
        person_paths=person_paths,
        recursive=config["behavior"].get("recursive_search", False),
        age_based_matching=config["recognition"].get("age_based_matching", False),
        age_tolerance=config["recognition"].get("age_tolerance", 5),
        birthdates=birthdates
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
