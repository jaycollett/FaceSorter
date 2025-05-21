FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# Set noninteractive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    unzip \
    yasm \
    pkg-config \
    libswscale-dev \
    libtbb2 \
    libtbb-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavformat-dev \
    libpq-dev \
    libxine2-dev \
    libglew-dev \
    libtiff5-dev \
    zlib1g-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libpostproc-dev \
    libswscale-dev \
    libeigen3-dev \
    libgtk2.0-dev \
    libopenblas-dev \
    python3-dev \
    python3-pip \
    python3-numpy \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create a working directory
WORKDIR /app

# Create Python venv
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements file
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install -r /app/requirements.txt

# Clone and build dlib with GPU support
RUN git clone https://github.com/davisking/dlib.git /dlib && \
    cd /dlib && \
    mkdir build && \
    cd build && \
    cmake .. -DDLIB_USE_CUDA=1 -DUSE_AVX_INSTRUCTIONS=1 && \
    cmake --build . && \
    cd .. && \
    python setup.py install

# Install face_recognition
RUN pip install face_recognition

# Copy the entire facesorter package and main script
COPY facesorter/ /app/facesorter/
COPY main.py /app/

# Make the script executable
RUN chmod +x /app/main.py

# Create data directory structure
RUN mkdir -p /data/input /data/known_faces /data/output /data/cache /data/logs /data/sorted

# Copy the entrypoint script
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]