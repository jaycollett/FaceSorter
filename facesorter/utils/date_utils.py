"""Date utility functions for FaceSorter"""

import os
import datetime
from dateutil.relativedelta import relativedelta
import re
import exifread
from PIL import Image
from PIL.ExifTags import TAGS

def extract_date_from_image(image_path):
    """
    Extract the date when an image was taken from EXIF data or filename
    
    Args:
        image_path: Path to the image file
        
    Returns:
        datetime.datetime object or None if date couldn't be extracted
    """
    # Try to extract from EXIF data first
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
            # Look for DateTimeOriginal tag
            if 'EXIF DateTimeOriginal' in tags:
                date_str = str(tags['EXIF DateTimeOriginal'])
                # Format is typically 'YYYY:MM:DD HH:MM:SS'
                return datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            
            # Try alternative date tags
            date_tags = ['EXIF DateTimeDigitized', 'Image DateTime']
            for tag in date_tags:
                if tag in tags:
                    date_str = str(tags[tag])
                    return datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    
    # Try PIL as a fallback for EXIF
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == 'DateTimeOriginal' or tag == 'DateTime':
                    return datetime.datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    
    # Try to extract date from filename
    filename = os.path.basename(image_path)
    
    # Common date patterns in filenames
    patterns = [
        # YYYY-MM-DD
        r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})',
        # YYYYMMDD
        r'(\d{4})(\d{2})(\d{2})',
        # DD-MM-YYYY
        r'(\d{2})[_-]?(\d{2})[_-]?(\d{4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                # Check if first group is year (4 digits) or day (2 digits)
                if len(groups[0]) == 4:  # YYYY-MM-DD format
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                else:  # DD-MM-YYYY format
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                
                # Validate date components
                if 1900 <= year <= datetime.datetime.now().year and 1 <= month <= 12 and 1 <= day <= 31:
                    try:
                        return datetime.datetime(year, month, day)
                    except ValueError:
                        # Invalid date (e.g., February 30)
                        continue
    
    # If all else fails, use file modification time
    try:
        mtime = os.path.getmtime(image_path)
        return datetime.datetime.fromtimestamp(mtime)
    except Exception:
        return None

def calculate_age(birthdate_str, photo_date):
    """
    Calculate a person's age at the time a photo was taken
    
    Args:
        birthdate_str: Birthdate string in 'YYYY-MM-DD' format
        photo_date: datetime.datetime object representing when the photo was taken
        
    Returns:
        Age in years as an integer, or None if calculation fails
    """
    if not birthdate_str or not photo_date:
        return None
    
    try:
        birthdate = datetime.datetime.strptime(birthdate_str, '%Y-%m-%d')
        # Calculate age using relativedelta for accurate years
        age = relativedelta(photo_date, birthdate).years
        return age
    except Exception:
        return None

def is_within_age_tolerance(actual_age, target_age, tolerance):
    """
    Check if an actual age is within tolerance of a target age
    
    Args:
        actual_age: Actual age in years
        target_age: Target age in years
        tolerance: Tolerance in years
        
    Returns:
        True if within tolerance, False otherwise
    """
    if actual_age is None or target_age is None:
        return True  # If we can't determine age, don't filter
    
    return abs(actual_age - target_age) <= tolerance
