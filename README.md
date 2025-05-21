# FaceSorter

A high-performance facial recognition tool that sorts family photos into person-specific folders with optimized support for children's faces.

## Overview

FaceSorter is designed to automatically organize your photo collection by recognizing faces and sorting images into person-specific folders. It features:

- **Advanced Face Recognition**: Uses the face_recognition library with optimizations for accuracy
- **Child Face Optimization**: Special settings for better recognition of children's faces
- **Priority Handling**: Specify which person gets priority when multiple faces are detected
- **High Performance**: Multi-threading and GPU acceleration for processing large collections
- **Smart Caching**: Avoids reprocessing previously analyzed images
- **Docker Integration**: GPU acceleration without affecting your system's CUDA setup

## Code Structure

FaceSorter uses a modular package structure for better maintainability, readability, and extensibility:

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

## Installation

Run the installation script to set up dependencies and prepare the system:

```bash
./install.sh
```

This script will:
- Check if Docker is installed (and help install it if needed)
- Check for NVIDIA drivers for GPU acceleration
- Set up NVIDIA Docker runtime if available
- Build the Docker image

## Quick Start with Docker (Recommended)

The easiest way to use FaceSorter is with Docker, which provides GPU acceleration without affecting your system:

```bash
./run_facesorter.sh
```

For better performance with large image collections:

```bash
./run_facesorter.sh --batch-size 128 --workers 24
```

## Directory Setup

The Docker container uses a consistent `/data` directory structure:

```
/data/
├── input/              # Input images to process
├── known_faces/        # Reference photos organized by person
│   ├── person1/        # One directory per person
│   │   └── *.jpg       # Multiple photos of person1
│   ├── person2/
│   │   └── *.jpg       # Multiple photos of person2
│   └── ...
├── output/             # Default output directory
├── cache/              # Cache for face encodings
├── logs/               # Log files
├── sorted/             # Base directory for person-specific paths
│   ├── person1/        # Person-specific output directory
│   ├── person2/        # Person-specific output directory
│   └── ...
└── sorted/[PERSONNAME] # Person-specific output directories
```

For each person you want to recognize, create a folder with their name in the `known_faces` directory and add several clear photos of their face.

## Configuration File

FaceSorter can be configured using a JSON configuration file instead of command-line arguments. The default configuration file is `config.json` in the current directory.

### Setting Up Your Configuration

1. A sample configuration file `config.sample.json` is provided as a template
2. Copy this file and rename it to `config.json`:
   ```bash
   cp config.sample.json config.json
   ```
3. Edit the `config.json` file with your specific settings

> **Note:** The actual `config.json` file is excluded from version control via `.gitignore` to prevent committing personal settings. Always use the sample as a starting point.

### Configuration Structure

The configuration file uses the following structure:

```json
{
  "directories": {
    "input": "/path/to/input/images",
    "cache": "/path/to/cache/directory"
  },
  "recognition": {
    "model": "cnn",
    "use_children_settings": true,
    "min_face_size": 20,
    "max_image_size": 1900,
    "age_based_matching": true,
    "age_tolerance": 5
  },
  "performance": {
    "workers": 28,
    "batch_size": 16
  },
  "behavior": {
    "move_files": true,
    "recursive_search": true
  },
  "people": {
    "person1": {
      "priority": 1,
      "birthdate": "2010-01-01",
      "output_path": "/path/to/person1/photos",
      "faces_path": "/path/to/known_faces/person1"
    },
    "person2": {
      "priority": 2,
      "birthdate": "2000-01-01",
      "output_path": "/path/to/person2/photos",
      "faces_path": "/path/to/known_faces/person2"
    }
  },
  "logging": {
    "log_dir": "/path/to/logs",
    "verbosity": "info"
  }
}
```

### Age-Based Matching

The configuration now supports age-based face matching to improve accuracy:

- `age_based_matching`: Enable/disable age-based matching (default: true)
- `age_tolerance`: Age tolerance in years (default: 5)
- Each person requires a `birthdate` in YYYY-MM-DD format

This feature helps improve accuracy by comparing the person's age at the time a photo was taken with their actual age based on birthdate.

### Using a Custom Configuration File

```bash
./run_facesorter.sh --config /path/to/your/config.json
```

All paths in the configuration file will be properly mapped to the Docker container's `/data` directory structure.

## ⚠️ Important: Do NOT Run main.py Directly

**FaceSorter must be run inside the Docker container via the `run_facesorter.sh` script.**

- Running `main.py` directly on your host machine will cause errors and may create unwanted log files in your root or project directory.
- Always use the provided shell script to start the application. This ensures all paths and volumes are correctly set up.
- The script handles paths with spaces in Docker volume mappings and ensures consistent directory structure in the container.

## Logging

FaceSorter writes log files to the directory specified in your configuration. The `run_facesorter.sh` script automatically mounts your configured `log_dir` to `/data/logs` in the container.

**Example:**
- If your `config.json` contains:
  ```json
  "logging": {
    "log_dir": "/home/jay/SourceCode/FaceSorter/logs",
    "verbosity": "info"
  }
  ```
- Then all log files will appear in `/home/jay/SourceCode/FaceSorter/logs` on your host system.

**Note:** If you change `log_dir` in your config, make sure the directory exists and is writable by Docker, or the script will attempt to create it for you. The application now uses a single log file approach to avoid duplicate logging issues.

## Key Features

- **High Performance**: Optimized for speed with multi-threading and GPU acceleration
- **Child-Optimized**: Special settings for better recognition of children's faces
- **Priority Handling**: Specify which person gets priority when multiple faces are found
- **Smart Caching**: Avoids reprocessing previously analyzed images
- **Container Isolation**: GPU acceleration without affecting your system's CUDA setup
- **Configuration File**: All settings can be defined in a JSON configuration file
- **File Safety**: Checksum verification ensures file integrity when moving files
- **Recursive Processing**: Option to process subdirectories recursively

## Command Options

```bash
./run_facesorter.sh [options]
```

Main options:
- `-c, --config PATH`: Path to JSON configuration file (default: ./config.json)
- `-r, --rebuild`: Force rebuild of Docker image
- `-h, --help`: Show help message

Legacy command-line options (these will override config file settings):
- `-b, --batch-size N`: Set batch size
- `-w, --workers N`: Set number of worker threads
- `-u, --unsorted PATH`: Set unsorted images directory
- `-k, --known-faces PATH`: Set known faces directory
- `-s, --sorted PATH`: Set sorted images directory
- `-C, --cache PATH`: Set cache directory
- `-p, --priority P1...`: Set priority list
- `-m, --move`: Move files instead of copying them

Using a configuration file is the recommended approach as it provides more options and better path handling, especially for paths with spaces.

## Configuration Options

### Directories

- `input`: Directory containing images to sort (default: mapped to `/data/input` in container)
- `known_faces`: Directory containing known face examples (default: mapped to `/data/known_faces` in container)
- `output`: Output directory for sorted images (default: mapped to `/data/output` in container)
- `cache`: Cache directory for face encodings (default: mapped to `/data/cache` in container)
- `logs`: Directory for log files (default: mapped to `/data/logs` in container)
- `sorted`: Base directory for person-specific paths (default: mapped to `/data/sorted` in container)

### Recognition

- `model`: Face detection model to use - "hog" (faster) or "cnn" (more accurate, GPU optimized) (default: "hog")
- `use_children_settings`: Whether to use settings optimized for children's faces (default: true)
- `min_face_size`: Minimum face size to consider in pixels (default: 20)
- `max_image_size`: Maximum image dimension for processing (default: 2000)

### Performance

- `workers`: Number of worker threads (default: null, which uses CPU count)
- `batch_size`: Number of images to process in a batch (default: null, which uses 16 for CNN model)

### Behavior

- `priority`: List of person names in priority order (default: ["ana", "ethan", "gabe", "natalie"])
- `move_files`: Whether to move files instead of copying them (default: false). Note: When true, caching is automatically disabled for safety.
- `recursive`: Whether to process subdirectories recursively (default: false)
- `person_paths`: Dictionary mapping person names to custom output directories (default: {})

### Logging

- `log_dir`: Directory for log files (default: "logs")
- `verbosity`: Logging level (default: "info", options: "debug", "info", "warning", "error", "critical")

## Advanced Usage

### Customizing Priority List

Use the priority list to set which people get precedence when multiple faces are detected in a photo:

```json
{
  "behavior": {
    "priority": ["natalie", "ana", "gabe", "ethan"]
  }
}
```

In this example, Natalie will get highest priority, followed by Ana, Gabe, and Ethan.

### Person-Specific Output Paths

You can configure custom output directories for each person:

```json
{
  "behavior": {
    "person_paths": {
      "ana": "/mnt/photos/family/Ana",
      "ethan": "/mnt/external/Ethan",
      "gabe": "/mnt/photos/family/Gabriel",
      "natalie": "/mnt/network/Natalie/photos"
    }
  }
}
```

This allows you to:
- Store photos in person-specific locations independent of the base output directory
- Organize photos across different storage devices or network locations
- Maintain separate photo collections per person

### Recursive Processing

To process subdirectories within your input directory:

```json
{
  "behavior": {
    "recursive": true
  }
}
```

Or use the command-line flag:

```bash
./run_facesorter.sh --recursive
```

### Testing GPU Support

The script automatically tests GPU support when building or running the container. It will install the NVIDIA Container Toolkit if it's not already installed and verify CUDA support inside the container.

### Performance Tips

1. For systems with lots of RAM, use larger batch sizes (64-128)
2. Adjust worker count based on your CPU cores (usually CPU cores minus 2)
3. The Docker container automatically uses GPU acceleration when available
4. Use the CNN model for better accuracy when GPU acceleration is available
5. Caching is automatically enabled when copying files and disabled when moving files for safety

#### About Caching

- When copying files (default), FaceSorter uses caching to avoid reprocessing images
- When moving files (`move_files: true`), caching is automatically disabled for safety
- The cache directory stores face encodings to speed up processing

## Files Included

- `main.py`: Entry point for the application
- `facesorter/`: Main package directory with modular code organization
- `run_facesorter.sh`: Helper script to run the container (handles paths with spaces in Docker volume mappings)
- `install.sh`: Installation script for dependencies
- `config.json`: Default configuration file
- `Dockerfile`: Defines the container with CUDA support
- `entrypoint.sh`: Docker container entrypoint script
- `requirements.txt`: Python dependencies
- `DOCKER_README.md`: Detailed Docker information
- `PROJECT_DOCUMENTATION.md`: Technical documentation for developers

## File Safety Features

FaceSorter includes robust safety mechanisms to ensure your files are never lost:

1. **Checksum Verification**: When moving files, checksums verify file integrity before deleting originals
2. **Safe Path Handling**: Consistent path mapping between host and container prevents misplaced files
3. **Permission Verification**: Directory write permissions are tested before any file operations
4. **Detailed Logging**: Comprehensive logs track every file operation

## Troubleshooting

If you encounter issues:

1. Make sure the NVIDIA drivers are installed: `nvidia-smi`
2. Ensure Docker is installed and has NVIDIA runtime support
3. Try rebuilding the container: `./run_facesorter.sh --rebuild`
4. Check the CUDA version in the container matches your drivers
5. Verify your configuration file is valid JSON
6. Check the log files for detailed error messages

## Version Information

FaceSorter has been reorganized into a modular package structure for better maintainability, readability, and extensibility. The current version includes improvements to the logging system (single log file approach), statistics tracking, and Docker configuration with a consistent `/data` directory structure for all paths.