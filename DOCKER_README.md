# FaceSorter Docker Container

This Docker container provides GPU-accelerated face recognition and sorting without affecting your system's CUDA installation.

## File Safety Features

FaceSorter includes robust safety mechanisms to ensure your files are never lost:

1. **Checksum Verification**: When moving files, a complete checksum verification confirms file integrity before deleting originals
2. **Safe Path Handling**: Consistent path mapping between host and container prevents files from being misplaced
3. **Permission Verification**: Directory write permissions are tested before any file operations
4. **Detailed Logging**: Comprehensive logs track every file operation for debugging

## Prerequisites

- Docker installed
- NVIDIA GPU with drivers installed
- NVIDIA Docker runtime (will be installed automatically if missing)

## Quick Start

The easiest way to run FaceSorter is using the provided script:

```bash
./run_docker.sh
```

This will:
1. Build the Docker image with CUDA support if needed
2. Test GPU availability
3. Run the container with your current directory mounted

## Command Line Options

```bash
./run_docker.sh [options]
```

Options:
- `-b, --batch-size N`: Set batch size (default: 64)
- `-w, --workers N`: Set number of workers (default: 32)
- `-d, --data-dir PATH`: Set data directory (default: current directory)
- `-g, --gpu`: Use explicit GPU version
- `-t, --turbo`: Use turbo version (default)
- `-r, --rebuild`: Force rebuild of Docker image
- `-h, --help`: Show help message

## Directory Structure

The script expects the following directory structure:

```
/your/data/directory/
├── unsorted/           # Directory containing unsorted images
├── known_faces/        # Directory containing reference faces
│   ├── person1/        # One directory per person
│   ├── person2/
│   └── ...
├── sorted/             # Output directory (created automatically)
└── .face_cache/        # Cache directory (created automatically)
```

### Custom Person Paths

You can configure custom output directories for specific people in the `config.json` file:

```json
{
  "behavior": {
    "person_paths": {
      "ana": "/path/to/ana/photos",
      "ethan": "/path/to/ethan/photos"
    }
  }
}
```

The FaceSorter will:
1. Create proper Docker volume mappings for each custom path
2. Safely translate between host and container paths
3. Ensure file moves to custom locations are verified with checksums
4. Log all path mappings for debugging purposes

The `.face_cache` directory stores face encodings and processing results, which significantly speeds up subsequent runs. This cache persists even if you remove the container, so you won't have to reprocess the same images again.

## Examples

Process images with larger batch size (for systems with more RAM):
```bash
./run_docker.sh --batch-size 128 --workers 32
```

Use a different data directory:
```bash
./run_docker.sh --data-dir /path/to/your/photos
```

Force rebuild of the Docker image:
```bash
./run_docker.sh --rebuild
```

## Manual Docker Commands

If you prefer to run Docker commands directly:

```bash
# Build the image
docker build -t facesorter .

# Run with GPU support
docker run --rm --gpus all \
  -v /path/to/your/photos:/data \
  facesorter \
  --batch-size 64 --workers 32
```

## Safe Move Operations

When using `move_files: true` in your config (or `--move` flag), FaceSorter performs extra safety checks:

1. **Disable Caching**: Caching is automatically disabled to prevent stale cache entries
2. **Copy-Verify-Delete**: Files are first copied, then verified, and only deleted after successful verification
3. **MD5 Checksum**: Full file content verification with MD5 checksums
4. **Error Recovery**: If verification fails, the destination file is deleted and the original is preserved

The safety algorithm:
```
1. Compute MD5 checksum of source file
2. Copy file to destination
3. Check destination file exists
4. Verify destination file size matches source
5. Compute MD5 checksum of destination file
6. Compare source and destination checksums
7. Only if all checks pass, delete the source file
```

This multi-layered approach ensures no files are ever lost during move operations.

## Troubleshooting

If you encounter GPU-related errors:

1. Check NVIDIA driver installation:
```bash
nvidia-smi
```

2. Verify NVIDIA Docker runtime:
```bash
docker info | grep -i runtime
```

3. Test CUDA in the container:
```bash
docker run --rm --gpus all facesorter --test
```

## Benefits of Using Docker

- Completely isolated environment with its own CUDA libraries
- Won't interfere with your system's CUDA 9 installation
- Includes all dependencies pre-configured
- Portable across different systems
- Easy version management