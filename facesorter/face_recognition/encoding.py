"""Face encoding functionality for FaceSorter"""

import os
import time
import face_recognition
import numpy as np

# Import from other modules
from ..config import ENABLE_CACHE, CHILDREN_TOLERANCE, DEFAULT_TOLERANCE, BATCH_SIZE, SIZE_PROGRESSION
from ..utils.file_ops import is_image_file, get_image_hash
from ..utils.logging import log
from ..image.processing import resize_image_for_processing, progressive_resize_and_detect

def load_known_faces(known_faces_dir, use_children_settings=True, model="hog", max_image_size=2000, cache_dir=None):
    """
    Load known face encodings from a directory structure
    
    Args:
        known_faces_dir: Directory containing subdirectories of person images
        use_children_settings: Whether to use settings optimized for children
        model: Face detection model to use ('hog' or 'cnn')
        max_image_size: Maximum image dimension for processing
        cache_dir: Directory to store face encoding cache (None to disable)
        
    Returns:
        Tuple of (known_face_encodings, known_face_names)
    """
    known_face_encodings = {}
    known_face_names = []
    
    # Tolerance setting based on whether we're optimizing for children
    tolerance = CHILDREN_TOLERANCE if use_children_settings else DEFAULT_TOLERANCE
    
    log.info(f"Loading known faces with {model} model and {'children-optimized' if use_children_settings else 'standard'} settings...")
    log.info(f"Tolerance setting: {tolerance}")
    if ENABLE_CACHE and cache_dir:
        log.info(f"Using cache directory: {cache_dir}")
    
    # Setup cache if enabled
    cache = {}
    cache_file = None
    if ENABLE_CACHE and cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"known_faces_cache_{model}.npz")
        try:
            if os.path.exists(cache_file):
                cache_data = np.load(cache_file, allow_pickle=True)
                cache = cache_data['cache'].item()
        except Exception:
            cache = {}
    
    start_time = time.time()
    new_cache_entries = 0
    
    # List all subdirectories in the known_faces_dir
    for person_dir in os.listdir(known_faces_dir):
        person_path = os.path.join(known_faces_dir, person_dir)
        
        if not os.path.isdir(person_path):
            continue
            
        person_name = person_dir
        person_encodings = []
        person_image_count = 0
        
        # Collect images for batch processing if using CNN
        image_paths = []
        for image_file in os.listdir(person_path):
            image_path = os.path.join(person_path, image_file)
            if is_image_file(image_file):
                image_paths.append(image_path)
                person_image_count += 1
        
        if not image_paths:
            continue
        
        # Process images, use batching for CNN model
        if model == "cnn" and len(image_paths) > 1:
            # Batch processing for CNN
            batch_size = BATCH_SIZE
            for i in range(0, len(image_paths), batch_size):
                batch_paths = image_paths[i:i + batch_size]
                batch_images = []
                batch_hashes = []
                cached_encodings = []
                
                # Try to load from cache first
                for img_path in batch_paths:
                    if ENABLE_CACHE and cache_dir:
                        img_hash = get_image_hash(img_path)
                        batch_hashes.append(img_hash)
                        
                        if img_hash in cache:
                            # We have a cached encoding
                            encoding = cache[img_hash]
                            if encoding is not None:
                                person_encodings.append(encoding)
                                cached_encodings.append(True)
                                continue
                    else:
                        batch_hashes.append(None)
                    
                    # Not in cache or cache disabled, need to load image
                    try:
                        img = face_recognition.load_image_file(img_path)
                        # Resize large images
                        img = resize_image_for_processing(img, max_size=max_image_size)
                        batch_images.append((img_path, img, len(cached_encodings)))
                        cached_encodings.append(False)
                    except Exception as e:
                        # Log error but keep processing
                        log.error(f"Error loading image: {e}")
                        cached_encodings.append(False)
                
                if not batch_images:
                    continue
                    
                # Process face detection in batch for all non-cached images
                batch_face_locations = []
                for _, img, _ in batch_images:
                    try:
                        # Use progressive sizing strategy for faster detection
                        face_locs = progressive_resize_and_detect(
                            img, model=model, 
                            min_size=SIZE_PROGRESSION[0], 
                            max_size=SIZE_PROGRESSION[-1],
                            step=500
                        )
                        batch_face_locations.append(face_locs)
                    except Exception as e:
                        batch_face_locations.append([])
                        log.error(f"Error detecting faces: {e}")
                
                # Process face encodings for each image
                for idx, ((img_path, img, cache_idx), face_locs) in enumerate(zip(batch_images, batch_face_locations)):
                    if not face_locs:
                        # No faces found
                        if ENABLE_CACHE and cache_dir and batch_hashes[cache_idx]:
                            # Cache negative result
                            cache[batch_hashes[cache_idx]] = None
                            new_cache_entries += 1
                        continue
                    
                    # Get face encodings
                    try:
                        # Use only the first face found (assuming one person per image)
                        face_encoding = face_recognition.face_encodings(img, [face_locs[0]])[0]
                        person_encodings.append(face_encoding)
                        
                        # Cache the encoding
                        if ENABLE_CACHE and cache_dir and batch_hashes[cache_idx]:
                            cache[batch_hashes[cache_idx]] = face_encoding
                            new_cache_entries += 1
                    except Exception as e:
                        log.error(f"Error encoding face: {e}")
        else:
            # Process images individually (HOG model or single image)
            for img_path in image_paths:
                # Try to load from cache first
                if ENABLE_CACHE and cache_dir:
                    img_hash = get_image_hash(img_path)
                    if img_hash in cache:
                        # We have a cached encoding
                        encoding = cache[img_hash]
                        if encoding is not None:
                            person_encodings.append(encoding)
                            continue
                
                # Not in cache or cache disabled, process the image
                try:
                    # Load image
                    img = face_recognition.load_image_file(img_path)
                    # Resize large images
                    img = resize_image_for_processing(img, max_size=max_image_size)
                    
                    # Detect face locations
                    face_locations = progressive_resize_and_detect(
                        img, model=model, 
                        min_size=SIZE_PROGRESSION[0], 
                        max_size=SIZE_PROGRESSION[-1],
                        step=500
                    )
                    
                    if not face_locations:
                        # No faces found
                        if ENABLE_CACHE and cache_dir:
                            # Cache negative result
                            cache[img_hash] = None
                            new_cache_entries += 1
                        continue
                    
                    # Get face encodings (use only the first face)
                    face_encoding = face_recognition.face_encodings(img, [face_locations[0]])[0]
                    person_encodings.append(face_encoding)
                    
                    # Cache the encoding
                    if ENABLE_CACHE and cache_dir:
                        cache[img_hash] = face_encoding
                        new_cache_entries += 1
                except Exception as e:
                    log.error(f"Error processing {os.path.basename(img_path)}: {e}")
        
        # Add person to known faces if we found any valid encodings
        if person_encodings:
            known_face_encodings[person_name] = np.array(person_encodings)
            known_face_names.append(person_name)
            log.info(f"Loaded {len(person_encodings)}/{person_image_count} images for {person_name}")
    
    # Save updated cache if we added new entries
    if ENABLE_CACHE and cache_dir and new_cache_entries > 0 and cache_file:
        try:
            np.savez_compressed(cache_file, cache=cache)
            log.info(f"Saved {new_cache_entries} new entries to face encoding cache")
        except Exception as e:
            log.error(f"Error saving face encoding cache: {e}")
    
    elapsed_time = time.time() - start_time
    log.info(f"Loaded {len(known_face_names)} people with {sum(len(encs) for encs in known_face_encodings.values())} face encodings in {elapsed_time:.2f} seconds")
    
    return known_face_encodings, known_face_names
