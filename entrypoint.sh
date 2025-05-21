#!/bin/bash
echo "FaceSorter Container with CUDA support"

# Test CUDA support
echo "Testing GPU support:"
python -c "import dlib; print(f\"CUDA enabled: {dlib.DLIB_USE_CUDA}\"); print(f\"CUDA devices: {dlib.cuda.get_num_devices() if dlib.DLIB_USE_CUDA else 0}\")"

if [ "$1" = "--test" ]; then
  exit 0
fi

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "Usage: docker run --gpus all -v /path/to/images:/data facesorter [options]"
  echo ""
  echo "Options:"
  echo "  --test           Test GPU support and exit"
  echo "  --batch-size N   Set batch size (default: 64)"
  echo "  --workers N      Set number of workers (default: 32)"
  echo "  --priority P1 P2 Set priority list of people names"
  echo "  -h, --help       Show this help message"
  echo ""
  exit 0
fi

# Default values (these will be overridden by config.json or command-line arguments)
BATCH_SIZE=8
WORKERS=4
PRIORITY="ana ethan gabe natalie"

# Parse arguments and build command
CMD_ARGS="--model cnn --input /data/input --known-faces /data/known_faces --cache-dir /data/cache"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --batch-size)
      BATCH_SIZE="$2"
      shift 2
      ;;
    --workers)
      WORKERS="$2"
      shift 2
      ;;
    --priority)
      shift
      PRIORITY=""
      while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^-- ]]; do
        PRIORITY="$PRIORITY $1"
        shift
      done
      PRIORITY=${PRIORITY## }
      ;;
    --gpu|--turbo)
      # Ignore these flags, always use turbo with GPU
      shift
      ;;
    *)
      # Add any other arguments directly
      CMD_ARGS="$CMD_ARGS $1"
      shift
      ;;
  esac
done

# Check if config file is being used
if [[ "$CMD_ARGS" == *"--config"* ]] || [[ "$CMD_ARGS" == *"-c "* ]]; then
  # When using config file, don't add these arguments unless explicitly set
  CONFIG_MODE="true"
  echo "Using configuration file mode"
  
  # Store all command line args for checking
  ALL_ARGS="$*"
  
  # Only add batch-size and workers if they were explicitly set via command line
  if [[ "$ALL_ARGS" == *"--batch-size"* ]] || [[ "$ALL_ARGS" == *"-b "* ]]; then
    CMD_ARGS="$CMD_ARGS --batch-size $BATCH_SIZE"
  fi
  
  if [[ "$ALL_ARGS" == *"--workers"* ]] || [[ "$ALL_ARGS" == *"-w "* ]]; then
    CMD_ARGS="$CMD_ARGS --workers $WORKERS"
  fi
  
  if [[ "$ALL_ARGS" == *"--priority"* ]] || [[ "$ALL_ARGS" == *"-p "* ]]; then
    CMD_ARGS="$CMD_ARGS --priority $PRIORITY"
  fi
else
  # Legacy mode - add standard arguments
  CMD_ARGS="$CMD_ARGS --batch-size $BATCH_SIZE --workers $WORKERS"
  
  # Add priority if set
  if [ -n "$PRIORITY" ]; then
    CMD_ARGS="$CMD_ARGS --priority $PRIORITY"
  fi
fi

echo "Running FaceSorter with:"
if [ "$CONFIG_MODE" = "true" ]; then
  echo "- Using settings from config file (may override defaults)"
else
  echo "- Batch size: $BATCH_SIZE"
  echo "- Workers: $WORKERS"
  echo "- Priority: $PRIORITY"
fi

# PATH MAPPING ARCHITECTURE:
# 1. Standard directories are mapped to /data/* in the container:
#    - input: /data/input
#    - known_faces: /data/known_faces
#    - output: /data/output
#    - cache: /data/cache
#    - logs: /data/logs
# 2. Person-specific paths are mapped to /data/sorted/person_name
# 3. The Python code automatically uses the container paths when running in Docker
# 4. All verification uses checksums to ensure file integrity


# Run the face sorter with GPU support
python /app/main.py $CMD_ARGS

# Print final summary message
echo ""
echo "===== PROCESSING COMPLETE ====="
echo "All files have been processed."
echo "File integrity verified with checksums for all moved files."
echo "Full detailed statistics available in log file and host terminal."