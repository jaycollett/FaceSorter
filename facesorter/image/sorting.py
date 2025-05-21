"""Image sorting functionality for FaceSorter"""

import os
import time
import shutil
import face_recognition
import numpy as np
import csv
import datetime
from collections import defaultdict
from tqdm import tqdm
import concurrent.futures

# Import from other modules
from ..config import ENABLE_CACHE, CHILDREN_TOLERANCE, DEFAULT_TOLERANCE, BATCH_SIZE, SIZE_PROGRESSION, CPU_COUNT
from ..utils.file_ops import is_image_file, get_image_hash, compute_file_checksum, generate_unique_filename
from ..utils.logging import log, flush_logs
from .processing import resize_image_for_processing, progressive_resize_and_detect
from ..face_recognition.matching import compare_face_encodings_vectorized

def process_image_batch(batch_data, known_face_encodings, known_face_names, priority_list, 
                       output_dir, use_children_settings=True, model="hog", min_face_size=20,
                       max_image_size=2000, cache_dir=None, move_files=False, person_paths=None, file_ops_writer=None):
    """
    Process a batch of images and copy/move to appropriate person folders if faces are recognized
    
    Args:
        batch_data: List of (image_path, image_array) tuples
        known_face_encodings: Dictionary mapping person to their face encodings
        known_face_names: List of person names
        priority_list: List of person names in priority order
        output_dir: Base directory for sorted images
        use_children_settings: Whether to use settings optimized for children
        model: Face detection model to use ('hog' or 'cnn')
        min_face_size: Minimum face size to consider (pixels)
        max_image_size: Maximum image dimension for processing
        cache_dir: Directory to store face encoding cache (None to disable)
        move_files: Whether to move files instead of copying them (default: False)
        person_paths: Dictionary mapping person names to custom output paths
        
    Returns:
        List of (result, person_name) tuples for each image
    """
    # Set tolerance based on whether we're optimizing for children
    tolerance = CHILDREN_TOLERANCE if use_children_settings else DEFAULT_TOLERANCE
    
    results = []
    
    # Setup face encoding cache if enabled
    encoding_cache = {}
    if ENABLE_CACHE and cache_dir:
        try:
            cache_file = os.path.join(cache_dir, f"face_encodings_cache_{model}.npz")
            if os.path.exists(cache_file):
                cache_data = np.load(cache_file, allow_pickle=True)
                encoding_cache = cache_data['cache'].item()
        except Exception:
            encoding_cache = {}
    
    new_cache_entries = 0
    
    # Detect face locations for all images in batch
    batch_face_locations = []
    valid_images = []
    valid_paths = []
    valid_hashes = []
    
    for img_path, img_array in batch_data:
        # Check cache first if enabled
        img_hash = None
        if ENABLE_CACHE and cache_dir:
            img_hash = get_image_hash(img_path)
            valid_hashes.append(img_hash)
            
            if img_hash in encoding_cache:
                # We have cached results for this image
                cached_result = encoding_cache[img_hash]
                if cached_result is not None:
                    success, person = cached_result
                    results.append((success, person))
                    continue
        else:
            valid_hashes.append(None)
            
        try:
            # Find faces in image using progressive sizing
            face_locations = progressive_resize_and_detect(
                img_array, model=model, 
                min_size=SIZE_PROGRESSION[0], 
                max_size=SIZE_PROGRESSION[-1],
                step=500
            )
            
            # Filter faces by size if needed
            if min_face_size > 0 and face_locations:
                filtered_locations = []
                for location in face_locations:
                    top, right, bottom, left = location
                    face_height = bottom - top
                    face_width = right - left
                    
                    if face_height >= min_face_size and face_width >= min_face_size:
                        filtered_locations.append(location)
                
                if len(filtered_locations) < len(face_locations):
                    print(f"Filtered out {len(face_locations) - len(filtered_locations)} small faces in {os.path.basename(img_path)}")
                    
                face_locations = filtered_locations
            
            if face_locations:
                batch_face_locations.append(face_locations)
                valid_images.append(img_array)
                valid_paths.append(img_path)
            else:
                results.append((False, None))
                
                # Cache negative result
                if ENABLE_CACHE and cache_dir and img_hash:
                    encoding_cache[img_hash] = (False, None)
                    new_cache_entries += 1
                
        except Exception as e:
            results.append((False, None))
    
    # Process face encodings in batch if we have valid faces
    if not valid_images:
        # Update cache if we added entries
        if ENABLE_CACHE and cache_dir and new_cache_entries > 0:
            try:
                cache_file = os.path.join(cache_dir, f"face_encodings_cache_{model}.npz")
                np.savez_compressed(cache_file, cache=encoding_cache)
            except Exception as e:
                log.error(f"Error saving face encodings cache: {e}")
                
        log.debug(f"process_image_batch returning {len(results)} results: {results}")
        return results
        
    # Get face encodings for all valid images
    try:
        batch_face_encodings = []
        for img, face_locs in zip(valid_images, batch_face_locations):
            encodings = face_recognition.face_encodings(img, face_locs)
            batch_face_encodings.append(encodings)
    except Exception as e:
        # Return failure for all remaining images
        log.error(f"Error batch encoding faces: {e}")
        results.extend([(False, None)] * len(valid_paths))
        
        # Update cache if needed
        if ENABLE_CACHE and cache_dir and new_cache_entries > 0:
            try:
                cache_file = os.path.join(cache_dir, f"face_encodings_cache_{model}.npz")
                np.savez_compressed(cache_file, cache=encoding_cache)
            except Exception as e:
                log.error(f"Error saving face encodings cache: {e}")
                
        log.debug(f"process_image_batch returning {len(results)} results: {results}")
        return results
    
    # Process recognition for each valid image
    for idx, (img_path, face_encodings) in enumerate(zip(valid_paths, batch_face_encodings)):
        try:
            # Find matches for each face
            found_persons = []
            
            for face_encoding in face_encodings:
                # Check each known person
                best_match = None
                highest_confidence = -1
                
                for person_name in known_face_names:
                    # Compare with all examples of this person
                    person_encodings = known_face_encodings[person_name]
                    
                    # Find the best match using vectorized comparison
                    matches, face_distances = compare_face_encodings_vectorized(
                        person_encodings, face_encoding, tolerance=tolerance
                    )
                    
                    if any(matches) and face_distances.min() < (1.0 - highest_confidence):
                        best_match = person_name
                        highest_confidence = 1.0 - face_distances.min()
                
                if best_match:
                    found_persons.append((best_match, highest_confidence))
                    
            if not found_persons:
                results.append((False, None))
                
                # Cache negative result
                if ENABLE_CACHE and cache_dir and valid_hashes[idx]:
                    encoding_cache[valid_hashes[idx]] = (False, None)
                    new_cache_entries += 1
                    
                continue
                
            # Sort by confidence
            found_persons.sort(key=lambda x: x[1], reverse=True)
            
            # Apply priority list if provided
            if priority_list:
                # Filter to only keep people in the priority list
                priority_matches = [p for p in found_persons if p[0] in priority_list]
                
                if not priority_matches:
                    results.append((False, None))
                    
                    # Cache negative result (not in priority list)
                    if ENABLE_CACHE and cache_dir and valid_hashes[idx]:
                        encoding_cache[valid_hashes[idx]] = (False, None)
                        new_cache_entries += 1
                        
                    continue
                    
                # Sort by priority
                priority_matches.sort(key=lambda x: priority_list.index(x[0]) if x[0] in priority_list else len(priority_list))
                
                # Take the highest priority match
                best_person = priority_matches[0][0]
                confidence = priority_matches[0][1]
            else:
                # Take the most confident match
                best_person = found_persons[0][0]
                confidence = found_persons[0][1]
            
            # Use direct container path for custom paths
            if person_paths and best_person in person_paths:
                person_dir = person_paths[best_person]
                # Custom paths should already exist, but ensure they do
                os.makedirs(person_dir, exist_ok=True)
            else:
                # Only create a sub-folder in the output directory if no custom path is configured
                person_dir = os.path.join(output_dir, best_person)
                os.makedirs(person_dir, exist_ok=True)
            
            # Copy or move the image to the person's folder
            destination = os.path.join(person_dir, os.path.basename(img_path))
            
            # Generate a unique filename with a numbered suffix if the file already exists
            destination = generate_unique_filename(destination)
            
            if move_files:
                # Enhanced safe move operation with verification
                try:
                    # First verify the source file exists and is readable
                    if not os.path.exists(img_path):
                        raise FileNotFoundError(f"Source file not found: {img_path}")
                    
                    # Check if we have write permission to destination directory
                    if not os.access(os.path.dirname(destination), os.W_OK):
                        raise PermissionError(f"No write permission to destination: {os.path.dirname(destination)}")
                    
                    # Log file operation details
                    log.info(f"Moving file: {os.path.basename(img_path)} to {person_dir}")
                    log.debug(f"Full source path: {img_path}")
                    log.debug(f"Full destination path: {destination}")
                    
                    # Log to CSV file if available
                    if file_ops_writer:                        
                        log_file_operation(
                            file_ops_writer, 
                            "MOVE", 
                            img_path, 
                            destination, 
                            best_person, 
                            confidence=highest_confidence
                        )
                    
                    # Step 1: Compute original file checksum
                    source_checksum = compute_file_checksum(img_path)
                    if not source_checksum:
                        log.error(f"Could not compute checksum for source file {img_path}")
                        results.append((False, None))
                        continue
                    
                    # Step 2: Copy file safely
                    try:
                        shutil.copy2(img_path, destination)
                        
                    except Exception as copy_err:
                        log.error(f"Failed to copy file: {copy_err}")
                        results.append((False, None))
                        continue
                    
                    # Step 3: Verify the file was copied correctly with multiple checks
                    if not os.path.exists(destination):
                        log.error(f"Destination file does not exist after copy: {destination}")
                        results.append((False, None))
                        continue
                        
                    # Check file size
                    if os.path.getsize(destination) != os.path.getsize(img_path):
                        log.error(f"File size mismatch after copy: {destination}")
                        # Try to clean up the incomplete copy
                        try:
                            os.remove(destination)
                        except:
                            pass
                        results.append((False, None))
                        continue
                    
                    # Verify checksum
                    dest_checksum = compute_file_checksum(destination)
                    if not dest_checksum or dest_checksum != source_checksum:
                        log.error(f"Checksum verification failed. Source: {source_checksum}, Destination: {dest_checksum}")
                        # Try to clean up the corrupted copy
                        try:
                            os.remove(destination)
                        except:
                            pass
                        results.append((False, None))
                        continue
                    
                    # Step 4: Only after checksum verification, remove the original
                    try:
                        log.debug(f"File validated, removing original: {img_path}")
                        # Remove the original file after verification
                        os.remove(img_path)
                        log.info(f"Successfully moved {os.path.basename(img_path)} to {best_person} ({destination})")
                        # Mark as success only after the file is actually moved
                        results.append((True, best_person))
                    except Exception as remove_err:
                        log.warning(f"Original file could not be removed: {remove_err}")
                        # Still consider this a success since the file was copied correctly
                        results.append((True, best_person))
                        continue
                        
                except Exception as e:
                    log.error(f"Error in move operation: {e}")
                    # Log failure to CSV file if available
                    if file_ops_writer:
                        log_file_operation(
                            file_ops_writer, 
                            "MOVE", 
                            img_path, 
                            destination, 
                            best_person, 
                            confidence=highest_confidence,
                            status="FAILED"
                        )
                    results.append((False, None))
                    continue
            else:
                # Regular copy operation with improved error handling
                try:
                    log.debug(f"Copying file: {img_path} to {destination}")
                    
                    # Log to CSV file if available
                    if file_ops_writer:
                        log_file_operation(
                            file_ops_writer, 
                            "COPY", 
                            img_path, 
                            destination, 
                            best_person, 
                            confidence=highest_confidence
                        )
                    
                    shutil.copy2(img_path, destination)
                    log.info(f"Copied {os.path.basename(img_path)} to {best_person} ({destination})")
                    # Mark as success only after the file is actually copied
                    results.append((True, best_person))
                except Exception as e:
                    log.error(f"Failed to copy file: {e}")
                    # Log failure to CSV file if available
                    if file_ops_writer:
                        log_file_operation(
                            file_ops_writer, 
                            "COPY", 
                            img_path, 
                            destination, 
                            best_person, 
                            confidence=highest_confidence,
                            status="FAILED"
                        )
                    results.append((False, None))
                    continue
            
            # Cache positive result
            if ENABLE_CACHE and cache_dir and valid_hashes[idx]:
                encoding_cache[valid_hashes[idx]] = (True, best_person)
                new_cache_entries += 1
            
        except Exception as e:
            # Log error but don't display in console
            log.error(f"Error processing {os.path.basename(img_path)}: {e}")
            results.append((False, None))
    
    # Fill in any missing results (should not happen, but just in case)
    while len(results) < len(batch_data):
        results.append((False, None))
    
    # Update cache if we added entries
    if ENABLE_CACHE and cache_dir and new_cache_entries > 0:
        try:
            cache_file = os.path.join(cache_dir, f"face_encodings_cache_{model}.npz")
            np.savez_compressed(cache_file, cache=encoding_cache)
        except Exception as e:
            log.error(f"Error saving cache file: {e}")
    
    log.debug(f"process_image_batch returning {len(results)} results: {results}")
    return results


def create_file_operations_log(log_dir):
    """
    Create a CSV file to log file operations (moves/copies)
    
    Args:
        log_dir: Directory to store log files
        
    Returns:
        Tuple of (csv_file_path, csv_writer, csv_file_handle)
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a timestamped log file name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(log_dir, f"FILE_MOVE_LOG_{timestamp}.csv")
    
    # Create and set up the CSV file
    log_file = open(log_file_path, 'w', newline='')
    csv_writer = csv.writer(log_file)
    
    # Write header row
    csv_writer.writerow([
        "Timestamp", 
        "Operation", 
        "SourcePath", 
        "DestinationPath", 
        "Person", 
        "Confidence", 
        "FileSize", 
        "Checksum", 
        "Status"
    ])
    
    log.info(f"File operations log created at: {log_file_path}")
    return log_file_path, csv_writer, log_file


def log_file_operation(csv_writer, operation, source_path, destination_path, person, confidence=None, checksum=None, status="SUCCESS"):
    """
    Log a file operation to the CSV file
    
    Args:
        csv_writer: CSV writer object
        operation: Type of operation (MOVE or COPY)
        source_path: Source file path
        destination_path: Destination file path
        person: Person name associated with the file
        confidence: Confidence score of the face match (optional)
        checksum: File checksum (optional)
        status: Operation status (SUCCESS, FAILED, etc.)
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_size = os.path.getsize(source_path) if os.path.exists(source_path) else 0
    
    csv_writer.writerow([
        timestamp,
        operation,
        source_path,
        destination_path,
        person if person else "UNKNOWN",
        f"{confidence:.4f}" if confidence is not None else "",
        file_size,
        checksum if checksum else "",
        status
    ])


def sort_images(source_dir, output_dir, known_faces_dir, priority_list=None, use_children_settings=True,
              model="hog", min_face_size=20, max_image_size=2000, move_files=False,
              max_workers=CPU_COUNT, batch_size=BATCH_SIZE, cache_dir=None, person_paths=None, recursive=False):
    """
    Sort images from source directory to output directory based on face recognition
    
    Args:
        source_dir: Directory containing images to sort
        output_dir: Base directory for sorted images
        known_faces_dir: Directory containing known faces
        priority_list: List of person names in priority order
        use_children_settings: Whether to use settings optimized for children
        model: Face detection model to use ('hog' or 'cnn')
        min_face_size: Minimum face size to consider (pixels)
        max_image_size: Maximum image dimension for processing
        cache_dir: Directory to store face encoding cache (None to disable)
        move_files: Whether to move files instead of copying them (default: False)
        person_paths: Dictionary mapping person names to custom output paths
        batch_size: Number of images to process in a batch (default: BATCH_SIZE)
        max_workers: Maximum number of worker threads (default: CPU_COUNT)
        
    Returns:
        Dictionary with statistics about the sorting process
    """
    from ..face_recognition.encoding import load_known_faces
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create cache directory if needed
    if ENABLE_CACHE and cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        
    # Set up file operations logging
    # Use the same log directory as the main application
    log_dir = os.environ.get("LOG_DIR", "/data/logs")
    file_ops_log_path, file_ops_writer, file_ops_file = create_file_operations_log(log_dir)
    
    # Load known faces
    log.info("Loading known faces...")
    known_face_encodings, known_face_names = load_known_faces(
        known_faces_dir, use_children_settings, model, max_image_size, cache_dir
    )
    
    if not known_face_names:
        log.error(f"No known faces found in {known_faces_dir}")
        return {
            "total_images": 0,
            "recognized": 0,
            "unrecognized": 0,
            "errors": 0,
            "person_counts": {}
        }
    
    log.info(f"Loaded {len(known_face_names)} known faces")
    
    # Find all image files in source directory
    image_files = []
    
    if recursive:
        # Recursively walk through all subdirectories
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if is_image_file(file_path):
                    image_files.append(file_path)
    else:
        # Only process files in the specified directory (no recursion)
        for file in os.listdir(source_dir):
            file_path = os.path.join(source_dir, file)
            if os.path.isfile(file_path) and is_image_file(file_path):
                image_files.append(file_path)
                
    # Warn if no recursive flag and there are subdirectories with images
    if not recursive:
        # Check if there are subdirectories with images that will be skipped
        subdirs_with_images = []
        for root, dirs, files in os.walk(source_dir):
            if root != source_dir:  # Skip the top-level directory
                image_count = sum(1 for f in files if is_image_file(os.path.join(root, f)))
                if image_count > 0:
                    rel_path = os.path.relpath(root, source_dir)
                    subdirs_with_images.append((rel_path, image_count))
        
        if subdirs_with_images:
            log.warning("Subdirectories with images found but recursive mode is OFF. These images will be SKIPPED:")
            for subdir, count in subdirs_with_images[:5]:  # Show only first 5 to avoid log spam
                log.warning(f"  - {subdir}: {count} images")
            if len(subdirs_with_images) > 5:
                log.warning(f"  - ... and {len(subdirs_with_images) - 5} more subdirectories")
            log.warning("Use --recursive flag to process all subdirectories")
    
    if not image_files:
        log.error(f"No image files found in {source_dir}")
        return {
            "total_images": 0,
            "recognized": 0,
            "unrecognized": 0,
            "errors": 0,
            "person_counts": {}
        }
    
    log.info(f"Found {len(image_files)} images to process")
    
    # Initialize statistics
    stats = {
        "total_images": len(image_files),
        "recognized": 0,
        "unrecognized": 0,
        "errors": 0,
        "person_counts": defaultdict(int)
    }
    
    # Process images in batches
    num_batches = (len(image_files) + batch_size - 1) // batch_size
    
    log.info(f"Starting to process {len(image_files)} images in {num_batches} batches")
    log.info(f"Using {max_workers} worker threads and batch size of {batch_size}")
    
    # Configure tqdm to be more verbose
    with tqdm(total=len(image_files), desc="Processing images", 
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(image_files))
            batch_files = image_files[start_idx:end_idx]
            
            # Log batch progress
            if batch_idx % max(1, num_batches // 10) == 0 or batch_idx == num_batches - 1:
                log.info(f"Processing batch {batch_idx+1}/{num_batches} ({len(batch_files)} images)")
                # Print current statistics
                if batch_idx > 0:
                    recognized_pct = stats["recognized"] / (stats["recognized"] + stats["unrecognized"] + stats["errors"]) * 100 if stats["recognized"] + stats["unrecognized"] + stats["errors"] > 0 else 0
                    log.info(f"Current stats: {stats['recognized']} recognized ({recognized_pct:.1f}%), {stats['unrecognized']} unrecognized, {stats['errors']} errors")
            
            # Load and resize images
            batch_data = []
            for img_path in batch_files:
                try:
                    img_array = resize_image_for_processing(img_path, max_image_size)
                    if img_array is not None:
                        batch_data.append((img_path, img_array))
                    else:
                        log.error(f"Could not load image: {img_path}")
                        stats["errors"] += 1
                        pbar.update(1)
                except Exception as e:
                    log.error(f"Error loading image {img_path}: {e}")
                    stats["errors"] += 1
                    pbar.update(1)
            
            if not batch_data:
                continue
            
            # Process batch with parallel executor for face detection
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future = executor.submit(
                    process_image_batch,
                    batch_data, known_face_encodings, known_face_names, priority_list,
                    output_dir, use_children_settings, model, min_face_size,
                    max_image_size, cache_dir, move_files, person_paths, file_ops_writer
                )
                
                try:
                    batch_results = future.result()
                    
                    # Update statistics
                    for (success, person), img_path in zip(batch_results, [bd[0] for bd in batch_data]):
                        if success:
                            stats["recognized"] += 1
                            stats["person_counts"][person] += 1
                        else:
                            stats["unrecognized"] += 1
                            
                        pbar.update(1)
                        
                        # Flush logs periodically
                        if (start_idx + len(batch_results)) % 100 == 0:
                            flush_logs()
                            
                except Exception as e:
                    log.error(f"Error processing batch: {e}")
                    stats["errors"] += len(batch_data)
                    pbar.update(len(batch_data))
    
    # Ensure stats add up correctly (bug fix)
    total_processed = stats["recognized"] + stats["unrecognized"] + stats["errors"]
    if total_processed != stats["total_images"]:
        log.warning(f"Statistics mismatch: processed {total_processed} images but total is {stats['total_images']}")
        # Fix the total count to match what was actually processed
        stats["total_images"] = total_processed
    
    # Log summary statistics
    log.info("\n========== SORTING OPERATION SUMMARY ==========")
    log.info(f"Total images processed in this run: {stats['total_images']}")
    log.info(f"Successfully recognized and sorted: {stats['recognized']} ({stats['recognized']/stats['total_images']*100:.1f}%)")
    log.info(f"Not recognized: {stats['unrecognized']} ({stats['unrecognized']/stats['total_images']*100:.1f}%)")
    log.info(f"Errors: {stats['errors']} ({stats['errors']/stats['total_images']*100:.1f}%)")
    
    # Log file operation details
    if move_files:
        log.info(f"Files were MOVED from source to destination folders")
    else:
        log.info(f"Files were COPIED from source to destination folders")
        
    log.info(f"Source directory: {source_dir}")
    log.info(f"Output directory: {output_dir}")
    
    # Log custom person paths if used
    if person_paths:
        log.info("\nCustom person directories used:")
        for person, path in person_paths.items():
            count = stats["person_counts"].get(person, 0)
            log.info(f"  - {person}: {count} images → {path}")
    
    # Log person counts
    if stats["recognized"] > 0:
        log.info("\nImages sorted per person in this run:")
        for person, count in sorted(stats["person_counts"].items(), key=lambda x: x[1], reverse=True):
            log.info(f"  {person}: {count} ({count/stats['recognized']*100:.1f}%)")
        
        log.info("\nNote: The directory statistics shown at the end include ALL images")
        log.info("in the destination directories, not just those sorted in this run.")
        log.info("========== END OF SORTING SUMMARY ==========")
    
    # Close the file operations log file
    if file_ops_file:
        file_ops_file.close()
        log.info(f"File operations log saved to: {file_ops_log_path}")
    
    return stats
