#!/bin/bash
# FaceSorter installation script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}FaceSorter Installation${NC}"
echo "This script will check for required dependencies and prepare FaceSorter for use."
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed.${NC}"
    echo "Would you like to install Docker? (y/n)"
    read answer
    if [ "$answer" != "${answer#[Yy]}" ]; then
        echo -e "${YELLOW}Installing Docker...${NC}"
        
        # Detect OS for Docker installation
        if [ -f /etc/debian_version ]; then
            # Debian/Ubuntu
            sudo apt-get update
            sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt-get update
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io
            
            # Add user to docker group
            sudo usermod -aG docker $USER
            echo -e "${YELLOW}Added user to docker group. You may need to log out and back in for this to take effect.${NC}"
        elif [ -f /etc/redhat-release ]; then
            # RHEL/CentOS/Fedora
            sudo yum install -y yum-utils
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            sudo yum install -y docker-ce docker-ce-cli containerd.io
            sudo systemctl start docker
            sudo systemctl enable docker
            
            # Add user to docker group
            sudo usermod -aG docker $USER
            echo -e "${YELLOW}Added user to docker group. You may need to log out and back in for this to take effect.${NC}"
        else
            echo -e "${RED}Automatic Docker installation not supported for your OS.${NC}"
            echo "Please install Docker manually: https://docs.docker.com/engine/install/"
            exit 1
        fi
    else
        echo "Please install Docker manually: https://docs.docker.com/engine/install/"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Docker is installed${NC}"
fi

# Check for NVIDIA drivers
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${YELLOW}NVIDIA drivers not detected.${NC}"
    echo "FaceSorter can run without GPU acceleration, but it will be slower."
    echo "You can install NVIDIA drivers later if you have a compatible GPU."
else
    echo -e "${GREEN}✓ NVIDIA drivers detected${NC}"
    
    # Check for NVIDIA Docker runtime
    if ! docker info | grep -q "Runtimes.*nvidia"; then
        echo -e "${YELLOW}NVIDIA Docker runtime not detected.${NC}"
        echo "Would you like to install NVIDIA Docker runtime? (y/n)"
        read answer
        if [ "$answer" != "${answer#[Yy]}" ]; then
            echo -e "${YELLOW}Installing NVIDIA Docker runtime...${NC}"
            
            # Detect OS for NVIDIA Docker installation
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
                echo -e "${RED}Automatic NVIDIA Docker installation not supported for your OS.${NC}"
                echo "Please install nvidia-docker manually:"
                echo "https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
            fi
        else
            echo "FaceSorter will run without GPU acceleration. It will be slower but still functional."
        fi
    else
        echo -e "${GREEN}✓ NVIDIA Docker runtime detected${NC}"
    fi
fi

# Make scripts executable
chmod +x run_facesorter.sh

# Build Docker image
echo -e "${YELLOW}Building FaceSorter Docker image...${NC}"
./run_facesorter.sh --rebuild --test

echo
echo -e "${GREEN}Installation complete!${NC}"
echo -e "To use FaceSorter, run: ${YELLOW}./run_facesorter.sh${NC}"
echo
echo "Example: ./run_facesorter.sh --batch-size 64 --workers 16"
echo
echo "Directory structure:"
echo "- known_faces/     Place reference photos here (one subfolder per person)"
echo "- unsorted/        Place unsorted photos here"
echo "- sorted/          Sorted photos will appear here"