"""Image processing utilities for FaceSorter"""

import numpy as np
from PIL import Image
import face_recognition

# Import constants from config
from ..config import SIZE_PROGRESSION

def resize_image_for_processing(image_input, max_size=2000):
    """
    Resize an image to a maximum dimension while preserving aspect ratio
    
    Args:
        image_input: Either a file path (string) or an image array (numpy array)
        max_size: Maximum dimension for the image
        
    Returns:
        Resized image as numpy array, or None if loading fails
    """
    # Check if input is a file path (string) or an image array
    if isinstance(image_input, str):
        # It's a file path, load the image
        try:
            pil_img = Image.open(image_input)
            # Convert to RGB if needed (handles RGBA, grayscale, etc.)
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            # Convert to numpy array
            image = np.array(pil_img)
        except Exception as e:
            # If loading fails, return None
            return None
    else:
        # It's already an image array
        image = image_input
    
    # Get image dimensions
    try:
        height, width = image.shape[:2]
    except Exception as e:
        # If we can't get dimensions, something is wrong with the image
        return None
    
    # If image is already smaller than max_size, return as is
    if max(height, width) <= max_size:
        return image
    
    # Calculate new dimensions
    if height > width:
        new_height = max_size
        new_width = int(width * (max_size / height))
    else:
        new_width = max_size
        new_height = int(height * (max_size / width))
    
    # Use PIL for high-quality resizing
    pil_img = Image.fromarray(image)
    # Check PIL version for LANCZOS constant
    try:
        resized_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
    except AttributeError:
        try:
            # For older PIL versions
            resized_img = pil_img.resize((new_width, new_height), Image.ANTIALIAS)
        except AttributeError:
            # Last resort - simple resize
            resized_img = pil_img.resize((new_width, new_height))
    
    # Convert back to numpy array
    return np.array(resized_img)


def progressive_resize_and_detect(image, model="hog", min_size=500, max_size=2000, step=500):
    """
    Use progressive resizing to optimize face detection performance
    Start with smaller images and only go to larger sizes if no faces are found
    """
    # Define size progression (try smaller sizes first)
    sizes = list(range(min_size, max_size + step, step))
    
    # Try each size until faces are found
    for size in sizes:
        # Resize image to current size
        current_img = resize_image_for_processing(image, max_size=size)
        
        # Detect faces
        face_locations = face_recognition.face_locations(current_img, model=model)
        
        # If faces found, return the locations
        if face_locations:
            # Scale face locations back to original image size if needed
            if size < max(image.shape[0], image.shape[1]):
                scale_h = image.shape[0] / current_img.shape[0]
                scale_w = image.shape[1] / current_img.shape[1]
                
                scaled_locations = []
                for top, right, bottom, left in face_locations:
                    scaled_top = int(top * scale_h)
                    scaled_right = int(right * scale_w)
                    scaled_bottom = int(bottom * scale_h)
                    scaled_left = int(left * scale_w)
                    scaled_locations.append((scaled_top, scaled_right, scaled_bottom, scaled_left))
                
                return scaled_locations
            else:
                return face_locations
    
    # If no faces found at any size, return empty list
    return []
