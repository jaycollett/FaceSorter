# FaceSorter Project Documentation

This document provides technical details about the FaceSorter application architecture, implementation, and design decisions. It's intended for developers who need to understand or modify the codebase.

## Project Overview

FaceSorter is a facial recognition tool that sorts images into person-specific folders. It's designed for high performance with a focus on accuracy, especially for children's faces. The application has been reorganized from a monolithic structure into a modular package design.

## Architecture

### Package Structure

```
FaceSorter/
├── facesorter/                 # Main package directory
│   ├── __init__.py             # Package initialization
│   ├── config.py               # Configuration handling
│   ├── cli.py                  # Command-line interface
│   ├── face_recognition/       # Face recognition module
│   │   ├── __init__.py
│   │   ├── detection.py        # Face detection functionality
│   │   ├── encoding.py         # Face encoding functionality
│   │   └── matching.py         # Face matching functionality
│   ├── image/                  # Image processing module
│   │   ├── __init__.py
│   │   ├── processing.py       # Image processing utilities
│   │   └── sorting.py          # Image sorting functionality
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── file_ops.py         # File operations
│       ├── logging.py          # Logging setup
│       └── caching.py          # Caching functionality
├── main.py                     # Entry point
├── Dockerfile                  # Docker container definition
├── entrypoint.sh               # Docker container entrypoint
├── run_facesorter.sh           # Helper script to run the application
├── install.sh                  # Installation script
└── requirements.txt            # Python dependencies
```

### Module Responsibilities

1. **config.py**: Handles loading and parsing configuration from JSON files or defaults
2. **cli.py**: Processes command-line arguments and initializes the application
3. **face_recognition/**:
   - **detection.py**: Detects faces in images
   - **encoding.py**: Generates face encodings and loads known faces
   - **matching.py**: Compares face encodings to find matches
4. **image/**:
   - **processing.py**: Image preprocessing and manipulation
   - **sorting.py**: Core logic for sorting images based on face recognition
5. **utils/**:
   - **file_ops.py**: File system operations and safety checks
   - **logging.py**: Logging configuration and utilities
   - **caching.py**: Caching mechanisms for face encodings

## Key Components

### Configuration System

The configuration system uses a layered approach:
1. Default values defined in `config.py`
2. Values from configuration file (JSON)
3. Command-line arguments (highest priority)

Configuration options include:
- Directory paths
- Recognition settings
- Performance tuning
- Behavior options
- Logging configuration

### Face Recognition Pipeline

1. **Loading Known Faces**:
   - Each person has a directory with example face images
   - Face encodings are extracted from these images
   - Encodings are cached for performance

2. **Image Processing**:
   - Images are resized for optimal processing
   - Progressive resizing is used to improve performance
   - Face detection uses either HOG (CPU) or CNN (GPU) models

3. **Face Matching**:
   - Vectorized face comparison for performance
   - Tolerance settings optimized for children's faces
   - Priority handling for multiple faces

4. **Image Sorting**:
   - Batch processing for performance
   - Multi-threading for parallel execution
   - Safe file operations with checksum verification

### Performance Optimizations

1. **Batch Processing**: Images are processed in batches to optimize GPU utilization
2. **Multi-threading**: Parallel processing of image batches
3. **Caching**: Face encodings are cached to avoid redundant processing
4. **Progressive Resizing**: Images are processed at increasing resolutions until faces are found
5. **Vectorized Operations**: NumPy vectorization for faster face comparisons

### Docker Integration

The application is designed to run in a Docker container with:
1. CUDA support for GPU acceleration
2. Volume mapping for data directories
3. Configurable resource allocation
4. Path translation between host and container

## Implementation Details

### Face Detection and Recognition

The application uses the `face_recognition` library, which is built on dlib. Two detection models are supported:
- **HOG**: Faster but less accurate, suitable for CPU-only systems
- **CNN**: More accurate but requires GPU for reasonable performance

Face matching uses a distance-based approach with adjustable tolerance:
- Standard tolerance: 0.6
- Children's faces tolerance: 0.5 (stricter for better discrimination)

### Image Sorting Logic

The core sorting algorithm in `sort_images()`:
1. Loads known face encodings for all people
2. Finds all image files in the input directory
3. Processes images in batches using multiple threads
4. For each image:
   - Detects faces and generates encodings
   - Compares with known face encodings
   - Determines the best match based on confidence
   - Applies priority rules for multiple matches
   - Copies or moves the image to the appropriate person folder
5. Tracks statistics for reporting

### File Safety Mechanisms

When moving files (`move_files: true`), extra safety measures are implemented:
1. **Checksum Verification**: MD5 checksums ensure file integrity
2. **Copy-Verify-Delete**: Files are only deleted after successful verification
3. **Error Recovery**: Failed operations preserve the original file

### Caching System

The caching system improves performance by:
1. Storing face encodings for known faces
2. Caching results for previously processed images
3. Using file hashes as cache keys
4. Automatically disabling caching when moving files

## Configuration Reference

### directories

```json
"directories": {
  "input": "unsorted",
  "known_faces": "known_faces",
  "output": "sorted",
  "cache": ".face_cache"
}
```

### recognition

```json
"recognition": {
  "model": "hog",
  "use_children_settings": true,
  "min_face_size": 20,
  "max_image_size": 2000
}
```

### performance

```json
"performance": {
  "workers": null,
  "batch_size": null
}
```

### behavior

```json
"behavior": {
  "priority": ["ana", "ethan", "gabe", "natalie"],
  "move_files": false,
  "recursive": false,
  "person_paths": {
    "ana": "/custom/path/for/ana",
    "ethan": "/different/path/for/ethan"
  }
}
```

### logging

```json
"logging": {
  "log_dir": "logs",
  "verbosity": "info"
}
```

## Docker Container

The Docker container is built with:
- Ubuntu 22.04 base
- CUDA 11.8 and cuDNN 8
- Python 3 with virtual environment
- Dlib compiled with CUDA support
- Face recognition libraries

The entrypoint script (`entrypoint.sh`) handles:
- Testing GPU support
- Parsing command-line arguments
- Setting up environment variables
- Path mapping between host and container

## Recent Changes

The application was recently reorganized from a monolithic structure into a modular package design:

1. **Modularization**: Split into logical components with clear responsibilities
2. **Bug Fixes**: Fixed statistics tracking in the `sort_images` function
3. **Verification**: Added scripts to test the reorganization
4. **Docker Updates**: Updated Docker configuration for the new structure
5. **Logging Improvements**: Fixed logging initialization to ensure log objects are always available

These changes have improved:
- Code maintainability
- Readability
- Extensibility
- Error handling

## Development Guidelines

When modifying the codebase:

1. **Maintain Modularity**: Keep functionality in appropriate modules
2. **Update Documentation**: Keep this document and README.md in sync with code changes
3. **Test Thoroughly**: Verify changes with the verification scripts
4. **Consider Docker**: Ensure changes work within the Docker container
5. **Preserve Safety**: Maintain file safety mechanisms, especially for move operations

## Troubleshooting for Developers

### Common Issues

1. **Import Errors**: Check the module structure and ensure `__init__.py` files are present
2. **Docker GPU Issues**: Verify NVIDIA drivers and Docker runtime configuration
3. **Path Problems**: Check path handling between host and container
4. **Performance Issues**: Review batch size and worker count settings

### Debugging

- Use the `--log-level debug` flag for detailed logging
- Check log files in the configured log directory
- Use the verification scripts to test specific components

## Future Improvements

Potential areas for enhancement:

1. **Age Detection**: Add age detection to improve child face recognition
2. **Web Interface**: Create a web-based UI for easier configuration
3. **Incremental Processing**: Only process new files since last run
4. **Face Quality Assessment**: Filter out low-quality face images
5. **Emotion Detection**: Sort by facial expressions or emotions
6. **Multi-GPU Support**: Distribute processing across multiple GPUs
7. **Cloud Integration**: Add support for cloud storage services
