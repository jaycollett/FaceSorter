"""Caching utilities for FaceSorter"""

import os
import numpy as np

# Import from other modules
from .logging import log
from .file_ops import get_image_hash

def load_cache(cache_file, default=None):
    """
    Load cache from a file
    
    Args:
        cache_file: Path to the cache file
        default: Default value to return if cache file doesn't exist
        
    Returns:
        Cache dictionary or default value
    """
    if default is None:
        default = {}
        
    if not os.path.exists(cache_file):
        return default
        
    try:
        cache_data = np.load(cache_file, allow_pickle=True)
        return cache_data['cache'].item()
    except Exception as e:
        log.error(f"Error loading cache file {cache_file}: {e}")
        return default

def save_cache(cache_file, cache):
    """
    Save cache to a file
    
    Args:
        cache_file: Path to the cache file
        cache: Cache dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        # Save cache
        np.savez_compressed(cache_file, cache=cache)
        return True
    except Exception as e:
        log.error(f"Error saving cache file {cache_file}: {e}")
        return False

def update_cache(cache, img_path, data, img_hash=None):
    """
    Update cache with new data
    
    Args:
        cache: Cache dictionary to update
        img_path: Path to the image
        data: Data to store in cache
        img_hash: Optional pre-computed image hash
        
    Returns:
        Updated cache dictionary
    """
    if img_hash is None:
        img_hash = get_image_hash(img_path)
        
    if img_hash:
        cache[img_hash] = data
        
    return cache
