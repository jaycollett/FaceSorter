"""Face detection functionality for FaceSorter"""

import face_recognition

# Import from other modules
from ..image.processing import resize_image_for_processing

def detect_faces(image, model="hog"):
    """
    Detect faces in an image
    
    Args:
        image: Image array
        model: Face detection model to use ('hog' or 'cnn')
        
    Returns:
        List of face locations (top, right, bottom, left)
    """
    return face_recognition.face_locations(image, model=model)

def detect_and_encode_faces(image, face_locations=None, model="hog"):
    """
    Detect and encode faces in an image
    
    Args:
        image: Image array
        face_locations: Optional pre-detected face locations
        model: Face detection model to use ('hog' or 'cnn')
        
    Returns:
        Tuple of (face_locations, face_encodings)
    """
    # Detect faces if locations not provided
    if face_locations is None:
        face_locations = detect_faces(image, model=model)
        
    # Encode faces
    face_encodings = face_recognition.face_encodings(image, face_locations)
    
    return face_locations, face_encodings

def filter_faces_by_size(face_locations, min_face_size=20):
    """
    Filter faces by size
    
    Args:
        face_locations: List of face locations (top, right, bottom, left)
        min_face_size: Minimum face size to consider (pixels)
        
    Returns:
        Filtered list of face locations
    """
    if min_face_size <= 0:
        return face_locations
        
    filtered_locations = []
    for location in face_locations:
        top, right, bottom, left = location
        face_height = bottom - top
        face_width = right - left
        
        if face_height >= min_face_size and face_width >= min_face_size:
            filtered_locations.append(location)
            
    return filtered_locations
