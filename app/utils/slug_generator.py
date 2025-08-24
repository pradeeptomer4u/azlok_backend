"""
Utility for generating URL-friendly slugs from strings.
"""
import re
import unicodedata
from typing import Optional


def generate_slug(text: str, max_length: Optional[int] = None) -> str:
    """
    Generate a URL-friendly slug from a given string.
    
    Args:
        text: The string to convert to a slug
        max_length: Optional maximum length for the slug
        
    Returns:
        A URL-friendly slug
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    
    # Remove all non-word characters (except hyphens)
    text = re.sub(r'[^\w\-]', '', text)
    
    # Replace multiple hyphens with a single hyphen
    text = re.sub(r'-+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    # Truncate to max_length if specified
    if max_length is not None and len(text) > max_length:
        text = text[:max_length].rstrip('-')
    
    return text
