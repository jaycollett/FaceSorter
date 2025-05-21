"""File operation utilities for FaceSorter"""

import os
import hashlib
import re

# Import logger from logging module
from .logging import log

def is_image_file(filename):
    """Check if a file is a recognized image format"""
    return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))


def get_image_hash(image_path):
    """Generate a hash for an image to use in caching"""
    if not os.path.exists(image_path):
        return None
    try:
        # Use file modification time and size for quick hash
        # This is faster than computing a full hash of the file content
        stats = os.stat(image_path)
        file_hash = f"{image_path}_{stats.st_size}_{stats.st_mtime}"
        return hashlib.md5(file_hash.encode()).hexdigest()
    except Exception:
        # If hashing fails, use a unique string based on the path
        return hashlib.md5(image_path.encode()).hexdigest()


def compute_file_checksum(file_path, block_size=65536):
    """
    Compute MD5 checksum of a file for verification purposes
    
    Args:
        file_path: The path to the file
        block_size: The block size for reading the file in chunks (default: 64KB)
        
    Returns:
        The MD5 checksum of the file as a hexadecimal string, or None if the file doesn't exist
    """
    if not os.path.exists(file_path):
        return None
        
    try:
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                md5.update(block)
        return md5.hexdigest()
    except Exception as e:
        if log:
            log.error(f"Error computing checksum for {file_path}: {e}")
        return None


def generate_unique_filename(destination_path):
    """
    Generate a unique filename by adding a numbered suffix if the file already exists.
    
    Args:
        destination_path: The target file path to check for existence
        
    Returns:
        A unique file path that doesn't exist yet
    """
    if not os.path.exists(destination_path):
        return destination_path
        
    directory = os.path.dirname(destination_path)
    filename = os.path.basename(destination_path)
    base_name, extension = os.path.splitext(filename)
    
    # Check if the filename already has a numeric suffix pattern like "_1", "_2", etc.
    suffix_match = re.search(r'_([0-9]+)$', base_name)
    
    # Start with suffix 1 or increment existing suffix
    if suffix_match:
        # Remove the existing suffix for clean numbering
        base_name = base_name[:suffix_match.start()]
        start_suffix = int(suffix_match.group(1)) + 1
    else:
        start_suffix = 1
    
    # Try incremental suffixes until we find an unused filename
    counter = start_suffix
    while True:
        new_filename = f"{base_name}_{counter}{extension}"
        new_path = os.path.join(directory, new_filename)
        
        if not os.path.exists(new_path):
            if log:
                log.debug(f"Generated unique filename: {new_filename}")
            return new_path
            
        counter += 1
        
        # Safety check to avoid infinite loops
        if counter > 10000:
            # If we somehow reach this point, use timestamp as fallback
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            new_filename = f"{base_name}_{timestamp}{extension}"
            new_path = os.path.join(directory, new_filename)
            if log:
                log.warning(f"Reached maximum suffix attempts, using timestamp instead: {new_filename}")
            return new_path
