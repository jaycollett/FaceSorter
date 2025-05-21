#!/bin/bash
# Script to build and run the FaceSorter Docker container with GPU support

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="facesorter"
# Use a simple name for the container
CONTAINER_NAME="facesorter"
CONFIG_PATH="config.json"
REBUILD=true  # Always rebuild by default to get latest code changes
USE_CONFIG=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --config|-c)
      CONFIG_PATH="$2"
      shift 2
      ;;
    --rebuild|-r)
      REBUILD=true
      shift
      ;;
    # Legacy parameters - will override config file settings if provided
    --batch-size|-b)
      BATCH_SIZE="$2"
      USE_CONFIG=false
      shift 2
      ;;
    --workers|-w)
      WORKERS="$2"
      USE_CONFIG=false
      shift 2
      ;;
    --unsorted|-u)
      UNSORTED_PATH="$2"
      USE_CONFIG=false
      shift 2
      ;;
    --known-faces|-k)
      KNOWN_FACES_PATH="$2"
      USE_CONFIG=false
      shift 2
      ;;
    --sorted|-s)
      SORTED_PATH="$2"
      USE_CONFIG=false
      shift 2
      ;;
    --cache|-C)
      CACHE_PATH="$2"
      USE_CONFIG=false
      shift 2
      ;;
    --priority|-p)
      shift
      PRIORITY=""
      while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^- ]]; do
        PRIORITY="$PRIORITY $1"
        shift
      done
      PRIORITY=${PRIORITY## }
      USE_CONFIG=false
      ;;
    --move|-m)
      MOVE_FILES=true
      USE_CONFIG=false
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  -c, --config PATH       Path to JSON configuration file (default: ./config.json)"
      echo "  -r, --rebuild           Force rebuild of Docker image"
      echo "  -h, --help              Show this help message"
      echo ""
      echo "Legacy options (these will override config file settings):"
      echo "  -b, --batch-size N      Set batch size"
      echo "  -w, --workers N         Set number of workers"
      echo "  -u, --unsorted PATH     Set unsorted images directory"
      echo "  -k, --known-faces PATH  Set known faces directory"
      echo "  -s, --sorted PATH       Set sorted images directory"
      echo "  -C, --cache PATH        Set cache directory"
      echo "  -p, --priority P1...    Set priority list"
      echo "  -m, --move              Move files instead of copying them"
      echo ""
      echo "Using a configuration file is the recommended approach."
      echo "See config.json for an example configuration."
      echo ""
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run with --help for usage information."
      exit 1
      ;;
  esac
done

# Function to convert relative paths to absolute paths
convert_to_absolute() {
  local path="$1"
  if [[ "$path" != /* ]]; then
    echo "$(pwd)/$path"
  else
    echo "$path"
  fi
}

# If using legacy parameters, set up paths
if [ "$USE_CONFIG" = false ]; then
  # Default directory paths (if not set by command line args)
  UNSORTED_PATH=${UNSORTED_PATH:-"$(pwd)/unsorted"}
  KNOWN_FACES_PATH=${KNOWN_FACES_PATH:-"$(pwd)/known_faces"}
  SORTED_PATH=${SORTED_PATH:-"$(pwd)/sorted"}
  CACHE_PATH=${CACHE_PATH:-"$(pwd)/.face_cache"}
  BATCH_SIZE=${BATCH_SIZE:-64}
  WORKERS=${WORKERS:-32}
  PRIORITY=${PRIORITY:-"ana ethan gabe natalie"}
  MOVE_FILES=${MOVE_FILES:-false}
  
  # Convert to absolute paths
  UNSORTED_PATH=$(convert_to_absolute "$UNSORTED_PATH")
  KNOWN_FACES_PATH=$(convert_to_absolute "$KNOWN_FACES_PATH")
  SORTED_PATH=$(convert_to_absolute "$SORTED_PATH")
  CACHE_PATH=$(convert_to_absolute "$CACHE_PATH")
  
  # Build command arguments in legacy mode
  DOCKER_ARGS="--batch-size $BATCH_SIZE --workers $WORKERS"
  
  if [ -n "$PRIORITY" ]; then
    DOCKER_ARGS="$DOCKER_ARGS --priority $PRIORITY"
  fi
  
  if [ "$MOVE_FILES" = true ]; then
    # Add move flag - CRITICAL for debugging
    DOCKER_ARGS="$DOCKER_ARGS --move"
    echo -e "${YELLOW}Running with --move flag (will move files instead of copying)${NC}"
else
    echo -e "${YELLOW}Running WITHOUT --move flag (will copy files)${NC}"
  fi
  
  # Set volume mappings
  VOLUME_ARGS="-v \"$UNSORTED_PATH:/data/input\" \
    -v \"$KNOWN_FACES_PATH:/data/known_faces\" \
    -v \"$SORTED_PATH:/data/output\" \
    -v \"$CACHE_PATH:/data/cache\""
else
  # Using config file
  CONFIG_PATH=$(convert_to_absolute "$CONFIG_PATH")
  
  # Check if config file exists
  if [ ! -f "$CONFIG_PATH" ]; then
    echo -e "${RED}Error: Configuration file not found: $CONFIG_PATH${NC}"
    echo "Create a config file or use legacy parameters."
    exit 1
  fi
  
  # Pass the config file to the Docker container
  DOCKER_ARGS="--config /app/config.json"
  VOLUME_ARGS="-v \"$CONFIG_PATH:/app/config.json\""
  
  # We need to parse the config file to determine the volume mounts
  # This requires jq, so let's check if it's installed
  if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq not found. Please install jq or use legacy parameters.${NC}"
    echo "Run: sudo apt install jq"
    exit 1
  fi
  
  # Parse directories from the config file
  INPUT_DIR=$(jq -r '.directories.input' "$CONFIG_PATH")
  KNOWN_FACES_DIR=$(jq -r '.directories.known_faces' "$CONFIG_PATH")
  OUTPUT_DIR=$(jq -r '.directories.output' "$CONFIG_PATH")
  CACHE_DIR=$(jq -r '.directories.cache' "$CONFIG_PATH")
  LOG_DIR=$(jq -r '.logging.log_dir' "$CONFIG_PATH")
  
  # Convert to absolute paths
  UNSORTED_PATH=$(convert_to_absolute "$INPUT_DIR")
  KNOWN_FACES_PATH=$(convert_to_absolute "$KNOWN_FACES_DIR")
  SORTED_PATH=$(convert_to_absolute "$OUTPUT_DIR")
  CACHE_PATH=$(convert_to_absolute "$CACHE_DIR")
  LOG_PATH=$(convert_to_absolute "$LOG_DIR")
  
  # Create an array to store all person paths
  declare -A PERSON_PATHS
  
  # Add volume mappings to mount the directories
  VOLUME_ARGS="-v \"$UNSORTED_PATH:/data/input\" \
    -v \"$KNOWN_FACES_PATH:/data/known_faces\" \
    -v \"$SORTED_PATH:/data/output\" \
    -v \"$SORTED_PATH:/data/sorted\" \
    -v \"$CACHE_PATH:/data/cache\" \
    -v \"$CONFIG_PATH:/app/config.json\" \
    -v \"$LOG_PATH:/data/logs\""
  
  # Extract and store all person paths from config.json
  for person in $(jq -r '.behavior.priority[]' "$CONFIG_PATH" 2>/dev/null); do
    # Check if person has a custom path configured
    custom_path=$(jq -r ".behavior.person_paths.\"$person\"" "$CONFIG_PATH" 2>/dev/null)
    if [ -n "$custom_path" ] && [ "$custom_path" != "null" ]; then
      # Convert to absolute path
      PERSON_PATHS[$person]=$(convert_to_absolute "$custom_path")
      # Add volume mapping for this person
      VOLUME_ARGS="$VOLUME_ARGS \
    -v \"${PERSON_PATHS[$person]}:/data/sorted/$person\""
    fi
  done
fi

# Check if nvidia-smi is available (required for Docker GPU support)
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}Error: nvidia-smi not found. NVIDIA drivers may not be installed.${NC}"
    echo "Please install the NVIDIA drivers and CUDA toolkit."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not found. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if nvidia-docker is available
if ! docker info | grep -q "Runtimes.*nvidia"; then
    echo -e "${YELLOW}Warning: NVIDIA Docker runtime not detected.${NC}"
    echo "Installing NVIDIA Container Toolkit..."
    
    # Detect the Linux distribution
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
        sudo apt-get update
        sudo apt-get install -y nvidia-docker2
        sudo systemctl restart docker
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.repo | sudo tee /etc/yum.repos.d/nvidia-docker.repo
        sudo yum install -y nvidia-docker2
        sudo systemctl restart docker
    else
        echo -e "${RED}Unsupported Linux distribution for automatic NVIDIA Docker setup.${NC}"
        echo "Please install nvidia-docker manually:"
        echo "https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        exit 1
    fi
fi

# Check if the image already exists
if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" || "$REBUILD" == "true" ]]; then
    echo -e "${YELLOW}Building Docker image...${NC}"
    # Use the Dockerfile
    docker build -t $IMAGE_NAME -f Dockerfile .
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to build Docker image.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Using existing Docker image.${NC}"
fi

# Test CUDA support inside the container
echo -e "${YELLOW}Testing CUDA support in the container...${NC}"
docker run --rm --gpus all $IMAGE_NAME --test

# Check if the required directories exist
if [ ! -d "$UNSORTED_PATH" ]; then
    echo -e "${RED}Error: Unsorted images directory not found: $UNSORTED_PATH${NC}"
    exit 1
fi

if [ ! -d "$KNOWN_FACES_PATH" ]; then
    echo -e "${RED}Error: Known faces directory not found: $KNOWN_FACES_PATH${NC}"
    exit 1
fi

# Create sorted directory if it doesn't exist
mkdir -p "$SORTED_PATH"

# Create cache directory if it doesn't exist
mkdir -p "$CACHE_PATH"

# Run the container with directory mapping
echo -e "${GREEN}Starting FaceSorter with GPU support...${NC}"
echo -e "${YELLOW}Configuration: $CONFIG_PATH${NC}"
echo -e "${YELLOW}Unsorted images: $UNSORTED_PATH${NC}"
echo -e "${YELLOW}Known faces: $KNOWN_FACES_PATH${NC}"
echo -e "${YELLOW}Sorted output: $SORTED_PATH${NC}"
echo -e "${YELLOW}Cache directory: $CACHE_PATH${NC}"

# Create logs directory for the Python application
mkdir -p "$LOG_PATH"
echo -e "${YELLOW}Created logs directory: $LOG_PATH${NC}"

# Note: Person path mappings are now set up earlier in the script

# Debug: Show environment variables and paths
echo "========== ENVIRONMENT AND PATHS =========="
echo "Working directory: $(pwd)"
echo "CONFIG_PATH: $CONFIG_PATH"
echo "UNSORTED_PATH: $UNSORTED_PATH"
echo "KNOWN_FACES_PATH: $KNOWN_FACES_PATH"
echo "SORTED_PATH: $SORTED_PATH"
echo "CACHE_PATH: $CACHE_PATH"
echo "DOCKER_ARGS: $DOCKER_ARGS"
echo ""

# Debug: Verify volume mounts
echo "========== VOLUME MOUNT CHECK =========="
echo "1. Checking if mount sources exist:"
for dir in "$UNSORTED_PATH" "$KNOWN_FACES_PATH" "$SORTED_PATH" "$CACHE_PATH"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir exists"
    else
        echo "  ✗ $dir does not exist"
    fi
done

echo "2. Checking if docker can access these directories:"
for dir in "$UNSORTED_PATH" "$KNOWN_FACES_PATH" "$SORTED_PATH" "$CACHE_PATH"; do
    if [ -d "$dir" ]; then
        perm=$(ls -ld "$dir" | awk '{print $1 " " $3 ":" $4}')
        echo "  $dir permissions: $perm"
    fi
done

# Debug: Show config file contents
echo "========== CONFIG CONTENTS =========="
if [ -f "$CONFIG_PATH" ]; then
    echo "Config file contents:"
    cat "$CONFIG_PATH"
    echo ""
    
    # Debug: Specifically check person_paths in config.json
    echo "Person paths from config:"
    jq -r '.behavior.person_paths | to_entries[] | "\(.key): \(.value)"' "$CONFIG_PATH"
    echo ""
fi

# Ensure we have a local fallback sorted directory (safety measure)
LOCAL_SORTED_DIR="$(pwd)/sorted"
mkdir -p "$LOCAL_SORTED_DIR"
echo -e "${YELLOW}Created local fallback directory: $LOCAL_SORTED_DIR${NC}"

# We'll track which persons are mapped to custom paths
MAPPED_PERSONS=()


# Run the container with custom directory mapping
echo "========== STARTING DOCKER CONTAINER =========="

# First build an array of docker arguments
DOCKER_ARGS_ARRAY=()
DOCKER_ARGS_ARRAY+=("--rm" "--gpus" "all" "--name" "$CONTAINER_NAME")

# We need to properly handle the volume arguments with spaces
# Instead of parsing the string, we'll build the array directly

# Add standard volume mappings
DOCKER_ARGS_ARRAY+=("-v" "$UNSORTED_PATH:/data/input")
DOCKER_ARGS_ARRAY+=("-v" "$KNOWN_FACES_PATH:/data/known_faces")
DOCKER_ARGS_ARRAY+=("-v" "$SORTED_PATH:/data/output")
DOCKER_ARGS_ARRAY+=("-v" "$SORTED_PATH:/data/sorted")
DOCKER_ARGS_ARRAY+=("-v" "$CACHE_PATH:/data/cache")
DOCKER_ARGS_ARRAY+=("-v" "$CONFIG_PATH:/app/config.json")
DOCKER_ARGS_ARRAY+=("-v" "$LOG_PATH:/data/logs")

# Add person-specific volume mappings
for person in "${!PERSON_PATHS[@]}"; do
    DOCKER_ARGS_ARRAY+=("-v" "${PERSON_PATHS[$person]}:/data/sorted/$person")
done

# Log the person-specific path mappings we've already set up
echo -e "${YELLOW}Person-specific path mappings:${NC}"
for person in "${!PERSON_PATHS[@]}"; do
    echo -e "  - Mapping ${YELLOW}$person${NC} to ${YELLOW}${PERSON_PATHS[$person]}${NC} → /data/sorted/$person"
    
    # Create the directory if it doesn't exist
    mkdir -p "${PERSON_PATHS[$person]}"
    
    # Add to tracked persons
    MAPPED_PERSONS+=("$person")
done

# Create directories for persons in known_faces
if [ -d "$KNOWN_FACES_PATH" ]; then
    echo -e "${YELLOW}Ensuring directories exist for all known persons:${NC}"
    for person_dir in "$KNOWN_FACES_PATH"/*; do
        if [ -d "$person_dir" ]; then
            person=$(basename "$person_dir")
            
            # Check if this person already has a custom mapping
            if [[ ! " ${MAPPED_PERSONS[*]} " =~ " ${person} " ]]; then
                # Create a directory in the output path for this person
                person_output_dir="$SORTED_PATH/$person"
                mkdir -p "$person_output_dir"
                
                echo -e "  - Person ${YELLOW}$person${NC} will use default output directory: ${YELLOW}$person_output_dir${NC}"
            fi
        fi
    done
fi

# Display container name for easy reference
echo -e "${GREEN}Running container with name: ${YELLOW}${CONTAINER_NAME}${NC}"

# Add the image name
DOCKER_ARGS_ARRAY+=("$IMAGE_NAME")

# Add any additional args
for arg in $DOCKER_ARGS; do
    DOCKER_ARGS_ARRAY+=("$arg")
done

# Debug: show the command on a single line
echo -n "Docker command: docker run "
for ((i=0; i<${#DOCKER_ARGS_ARRAY[@]}; i++)); do
    # Add quotes around arguments with spaces
    if [[ "${DOCKER_ARGS_ARRAY[$i]}" == *" "* ]]; then
        echo -n "\"${DOCKER_ARGS_ARRAY[$i]}\" "
    else
        echo -n "${DOCKER_ARGS_ARRAY[$i]} "
    fi
done
echo ""

# Run the container
docker run "${DOCKER_ARGS_ARRAY[@]}" 2>&1

# Capture docker exit status
DOCKER_EXIT_CODE=${PIPESTATUS[0]}

# Record exit code in debug log only (not displayed to user)
echo "Container exit code: $DOCKER_EXIT_CODE"

# Verify files were moved by checking source and destination directories
echo "========== POST-PROCESSING DIRECTORY CHECK =========="

# Count files in source directory
SOURCE_FILE_COUNT=$(find "$UNSORTED_PATH" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \) | wc -l)
echo "Files remaining in source directory: $SOURCE_FILE_COUNT"

# Count files in sorted directory
SORTED_FILE_COUNT=$(find "$SORTED_PATH" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \) | wc -l)
echo "Total files in sorted directory: $SORTED_FILE_COUNT"

# Count files in each person directory
echo "Contents by person:"
for person in $(jq -r '.behavior.priority[]' "$CONFIG_PATH" 2>/dev/null); do
    # Check if person has a custom path configured
    if [ -f "$CONFIG_PATH" ] && command -v jq &> /dev/null; then
        custom_path=$(jq -r ".behavior.person_paths.\"$person\"" "$CONFIG_PATH" 2>/dev/null)
        if [ -n "$custom_path" ] && [ "$custom_path" != "null" ]; then
            # Person has a custom path, so use that instead of default
            if [ -d "$custom_path" ]; then
                count=$(find "$custom_path" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \) | wc -l)
                echo "$person (custom path: $custom_path): $count"
            else
                echo "$person (custom path: $custom_path): directory not found"
            fi
        else
            # No custom path, check default location
            default_dir="$SORTED_PATH/$person"
            if [ -d "$default_dir" ]; then
                count=$(find "$default_dir" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" | wc -l)
                echo "$person: $count files"
            else
                echo "$person: no directory found"
            fi
        fi
    else
        # No config file or jq available, check default location
        default_dir="$SORTED_PATH/$person"
        if [ -d "$default_dir" ]; then
            count=$(find "$default_dir" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" | wc -l)
            echo "$person: $count files"
        else
            echo "$person: no directory found"
        fi
    fi
done

# Debug: Check directory contents after processing
echo "========== POST-PROCESSING DIRECTORY STATISTICS =========="
echo "Source directory: $UNSORTED_PATH"
# Count image files only
FILES_REMAINING=$(find "$UNSORTED_PATH" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" | wc -l)
echo "Images remaining in source directory: $FILES_REMAINING"

echo "Custom person directories:"
TOTAL_SORTED=0

for person in $(jq -r '.behavior.priority[]' "$CONFIG_PATH" 2>/dev/null); do
    # Check if person has a custom path configured
    custom_path=$(jq -r ".behavior.person_paths.\"$person\"" "$CONFIG_PATH" 2>/dev/null)
    if [ -n "$custom_path" ] && [ "$custom_path" != "null" ]; then
        # Person has a custom path
        if [ -d "$custom_path" ]; then
            COUNT=$(find "$custom_path" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" | wc -l)
            TOTAL_SORTED=$((TOTAL_SORTED + COUNT))
            echo "- $person: $COUNT images → $custom_path"
        else
            echo "- $person: 0 images (directory not found: $custom_path)"
        fi
    else
        # No custom path, check default location
        if [ -d "$SORTED_PATH/$person" ]; then
            COUNT=$(find "$SORTED_PATH/$person" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" | wc -l)
            TOTAL_SORTED=$((TOTAL_SORTED + COUNT))
            echo "- $person: $COUNT images → $SORTED_PATH/$person"
        else
            echo "- $person: 0 images (no directory found)"
        fi
    fi
done

# Count files in unknown directory if it exists
UNKNOWN_DIR="$SORTED_PATH/unknown"
if [ -d "$UNKNOWN_DIR" ]; then
    UNKNOWN_COUNT=$(find "$UNKNOWN_DIR" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" | wc -l)
    TOTAL_SORTED=$((TOTAL_SORTED + UNKNOWN_COUNT))
    echo "- unknown faces: $UNKNOWN_COUNT images → $UNKNOWN_DIR"
else 
    # Check if output directory is configured as unknown
    OUTPUT_DIR=$(jq -r '.directories.output' "$CONFIG_PATH" 2>/dev/null)
    if [ -d "$OUTPUT_DIR" ]; then
        UNKNOWN_COUNT=$(find "$OUTPUT_DIR" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" | wc -l)
        TOTAL_SORTED=$((TOTAL_SORTED + UNKNOWN_COUNT))
        echo "- unknown faces: $UNKNOWN_COUNT images → $OUTPUT_DIR"
    else
        echo "- unknown faces: 0 images (no directory found)"
    fi
fi

echo "Total images in destination directories: $TOTAL_SORTED"
echo "========== END OF STATISTICS =========="

echo -e "\n${GREEN}✓ Processing complete!${NC}"

# Show simple summary instead of table
echo -e "\n${GREEN}==== DIRECTORY SUMMARY ====${NC}"

# Show stats for each person
for person in $(jq -r '.behavior.priority[]' "$CONFIG_PATH" 2>/dev/null); do
    # Get person count
    custom_path=$(jq -r ".behavior.person_paths.\"$person\"" "$CONFIG_PATH" 2>/dev/null)
    if [ -n "$custom_path" ] && [ "$custom_path" != "null" ]; then
        # Person has a custom path
        if [ -d "$custom_path" ]; then
            count=$(find "$custom_path" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" | wc -l)
            echo -e "${YELLOW}$person:${NC} $count images in $custom_path"
        fi
    else
        # Default path
        default_dir="$SORTED_PATH/$person"
        if [ -d "$default_dir" ]; then
            count=$(find "$default_dir" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" | wc -l)
            echo -e "${YELLOW}$person:${NC} $count images in $default_dir"
        fi
    fi
done

# Show unknown directory
OUTPUT_DIR=$(jq -r '.directories.output' "$CONFIG_PATH" 2>/dev/null)
if [ -d "$OUTPUT_DIR" ]; then
    count=$(find "$OUTPUT_DIR" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" | wc -l)
    echo -e "${YELLOW}unknown:${NC} $count images in $OUTPUT_DIR"
fi

# Show input directory and remaining files
SOURCE_COUNT=$(find "$UNSORTED_PATH" -type f -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" | wc -l)
echo -e "\n${YELLOW}Input directory:${NC} $UNSORTED_PATH"
echo -e "${YELLOW}Files remaining:${NC} $SOURCE_COUNT"
echo -e "${YELLOW}Log file:${NC} $DEBUG_LOG"
echo