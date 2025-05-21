"""Face matching functionality for FaceSorter"""

import numpy as np
import face_recognition
import datetime

from ..utils.date_utils import calculate_age, is_within_age_tolerance, extract_date_from_image

def compare_face_encodings_vectorized(known_encodings, unknown_encoding, tolerance=0.6):
    """
    Vectorized comparison of face encodings for better performance
    
    Args:
        known_encodings: List or array of known face encodings
        unknown_encoding: A single face encoding to compare against
        tolerance: Maximum face distance to consider a match (lower is stricter)
    
    Returns:
        Tuple of (matches, face_distances)
    """
    if len(known_encodings) == 0:
        return [], []
    
    # Stack all known encodings into a single numpy array
    if not isinstance(known_encodings, np.ndarray):
        known_encodings_array = np.array(known_encodings)
    else:
        known_encodings_array = known_encodings
    
    # Calculate distances all at once (vectorized)
    face_distances = face_recognition.face_distance(known_encodings_array, unknown_encoding)
    
    # Generate matches based on tolerance
    matches = list(face_distances <= tolerance)
    
    return matches, face_distances

def find_best_match(face_encoding, known_face_encodings, known_face_names, tolerance=0.6, priority_list=None,
                age_based_matching=False, image_path=None, birthdates=None, age_tolerance=5):
    """
    Find the best matching person for a face encoding
    
    Args:
        face_encoding: The face encoding to match
        known_face_encodings: Dictionary mapping person names to their face encodings
        known_face_names: List of known person names
        tolerance: Maximum face distance to consider a match (lower is stricter)
        priority_list: Optional list of person names in priority order
        age_based_matching: Whether to use age-based matching with birthdates
        image_path: Path to the image being analyzed (for extracting date)
        birthdates: Dictionary mapping person names to birthdates (format: 'YYYY-MM-DD')
        age_tolerance: Age tolerance in years for age-based matching
        
    Returns:
        Tuple of (best_match, confidence) or (None, 0) if no match found
    """
    found_persons = []
    
    # Extract photo date if using age-based matching
    photo_date = None
    if age_based_matching and image_path and birthdates:
        photo_date = extract_date_from_image(image_path)
    
    # Check each known person
    for person_name in known_face_names:
        # Compare with all examples of this person
        person_encodings = known_face_encodings[person_name]
        
        # Find the best match using vectorized comparison
        matches, face_distances = compare_face_encodings_vectorized(
            person_encodings, face_encoding, tolerance=tolerance
        )
        
        # If any match found, record the best one
        if any(matches):
            confidence = 1.0 - face_distances.min()
            
            # Apply age-based matching if enabled
            if age_based_matching and photo_date and birthdates and person_name in birthdates:
                birthdate = birthdates.get(person_name)
                if birthdate:
                    # Calculate person's age at the time the photo was taken
                    person_age = calculate_age(birthdate, photo_date)
                    
                    # Adjust confidence based on age match
                    if person_age is not None:
                        # If the person's age at photo time is very young (< 10), be more lenient
                        # as facial features change more rapidly in children
                        effective_tolerance = age_tolerance
                        if person_age < 10:
                            effective_tolerance += 2
                        
                        # Check if the estimated age from the photo is within tolerance
                        # If not within tolerance, reduce confidence significantly
                        # This helps filter out false positives where the face matches but age doesn't
                        
                        # For simplicity, we're using a binary approach here
                        # A more sophisticated approach could use a sliding scale
                        
                        # Get all possible ages within tolerance range
                        valid_ages = range(max(0, person_age - effective_tolerance), 
                                           person_age + effective_tolerance + 1)
                        
                        # If the person's age is within tolerance, keep high confidence
                        # Otherwise, reduce confidence significantly
                        if person_age not in valid_ages:
                            confidence *= 0.5  # Reduce confidence by 50%
            
            found_persons.append((person_name, confidence))
    
    if not found_persons:
        return None, 0
    
    # Sort by confidence
    found_persons.sort(key=lambda x: x[1], reverse=True)
    
    # Apply priority list if provided
    if priority_list:
        # Filter to only keep people in the priority list
        priority_matches = [p for p in found_persons if p[0] in priority_list]
        
        if not priority_matches:
            return None, 0
        
        # Sort by priority
        priority_matches.sort(key=lambda x: priority_list.index(x[0]) if x[0] in priority_list else len(priority_list))
        
        # Take the highest priority match
        return priority_matches[0]
    else:
        # Take the most confident match
        return found_persons[0]
