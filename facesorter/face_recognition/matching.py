"""Face matching functionality for FaceSorter"""

import numpy as np
import face_recognition

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

def find_best_match(face_encoding, known_face_encodings, known_face_names, tolerance=0.6, priority_list=None):
    """
    Find the best matching person for a face encoding
    
    Args:
        face_encoding: The face encoding to match
        known_face_encodings: Dictionary mapping person names to their face encodings
        known_face_names: List of known person names
        tolerance: Maximum face distance to consider a match (lower is stricter)
        priority_list: Optional list of person names in priority order
        
    Returns:
        Tuple of (best_match, confidence) or (None, 0) if no match found
    """
    found_persons = []
    
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
