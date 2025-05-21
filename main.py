#!/usr/bin/env python3
"""
FaceSorter Turbo: A high-performance tool to sort images into folders based on recognized faces
- Uses face_recognition library with advanced optimizations
- Optimized for recognizing children's faces with adjustable parameters
- Supports priority handling when multiple faces are detected
- Enhanced performance with vectorized operations and caching
- Supports copying or safely moving files from source to destination
- Uses JSON configuration file for settings
"""

import os
import sys

# Add the parent directory to the Python path so we can import the facesorter package
# This is necessary when running in Docker or when the package is not installed
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now we can import from the facesorter package
try:
    from facesorter.utils.logging import check_docker_environment
    from facesorter.cli import main
except ImportError as e:
    print(f"Error importing facesorter modules: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Script directory: {parent_dir}")
    sys.exit(1)

if __name__ == "__main__":
    # Check Docker environment before anything else
    check_docker_environment()
    
    # Run the main CLI function
    sys.exit(main())
