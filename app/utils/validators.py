"""
Validation utilities for BrainBudget.
Input validation, file validation, and data sanitization.
"""
import re
import os
from typing import Any, Dict, List, Optional, Union
from werkzeug.utils import secure_filename


def validate_file_type(filename: str, allowed_extensions: set) -> bool:
    """
    Validate file type based on extension.
    
    Args:
        filename: Name of the file
        allowed_extensions: Set of allowed file extensions
        
    Returns:
        True if file type is allowed, False otherwise
    """
    if not filename:
        return False
    
    # Get file extension
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return extension in allowed_extensions


def validate_file_size(file_size: int, max_size: int) -> bool:
    """
    Validate file size.
    
    Args:
        file_size: Size of the file in bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if file size is acceptable, False otherwise
    """
    return 0 < file_size <= max_size


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None


def validate_user_id(user_id: str) -> bool:
    """
    Validate Firebase user ID format.
    
    Args:
        user_id: User ID to validate
        
    Returns:
        True if user ID is valid, False otherwise
    """
    if not user_id or not isinstance(user_id, str):
        return False
    
    # Firebase UIDs are typically 28 characters long and alphanumeric
    return len(user_id) >= 10 and user_id.isalnum()


def validate_amount(amount: Union[str, int, float]) -> Optional[float]:
    """
    Validate and convert monetary amount.
    
    Args:
        amount: Amount to validate (can be string, int, or float)
        
    Returns:
        Validated amount as float, or None if invalid
    """
    try:
        if isinstance(amount, str):
            # Remove common currency symbols and whitespace
            cleaned = re.sub(r'[$,\s]', '', amount.strip())
            amount = float(cleaned)
        elif isinstance(amount, (int, float)):
            amount = float(amount)
        else:
            return None
        
        # Check for reasonable bounds (not negative infinity, not too large)
        if not (-1000000 <= amount <= 1000000):
            return None
        
        # Round to 2 decimal places for currency
        return round(amount, 2)
        
    except (ValueError, TypeError):
        return None


def validate_date_string(date_str: str) -> bool:
    """
    Validate date string format (YYYY-MM-DD).
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if date format is valid, False otherwise
    """
    if not date_str or not isinstance(date_str, str):
        return False
    
    # Check format with regex
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False
    
    try:
        from datetime import datetime
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return 'untitled'
    
    # Use werkzeug's secure_filename and add additional sanitization
    safe_name = secure_filename(filename)
    
    # Remove any remaining problematic characters
    safe_name = re.sub(r'[^\w\-_.]', '_', safe_name)
    
    # Ensure it's not too long
    if len(safe_name) > 100:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:95] + ext
    
    return safe_name or 'untitled'


def sanitize_text_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize text input by removing dangerous characters.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text or not isinstance(text, str):
        return ''
    
    # Strip whitespace
    text = text.strip()
    
    # Remove null bytes and control characters (except newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_transaction_data(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize transaction data.
    
    Args:
        transaction: Transaction dictionary to validate
        
    Returns:
        Validated and sanitized transaction data
    """
    validated = {}
    
    # Validate date
    date_str = transaction.get('date', '')
    if validate_date_string(date_str):
        validated['date'] = date_str
    else:
        from datetime import datetime
        validated['date'] = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Validate description
    description = sanitize_text_input(transaction.get('description', ''), max_length=200)
    validated['description'] = description or 'Unknown Transaction'
    
    # Validate amount
    amount = validate_amount(transaction.get('amount', 0))
    validated['amount'] = amount if amount is not None else 0.0
    
    # Validate type
    transaction_type = transaction.get('type', '').lower()
    validated['type'] = transaction_type if transaction_type in ['debit', 'credit'] else 'debit'
    
    # Validate category
    category = sanitize_text_input(transaction.get('category', ''), max_length=50)
    validated['category'] = category or 'Other'
    
    # Validate subcategory
    subcategory = sanitize_text_input(transaction.get('subcategory', ''), max_length=50)
    validated['subcategory'] = subcategory or 'Uncategorized'
    
    # Validate balance (optional)
    balance = validate_amount(transaction.get('balance', 0))
    if balance is not None:
        validated['balance'] = balance
    
    return validated


def validate_analysis_request(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate analysis request data.
    
    Args:
        data: Analysis request data
        
    Returns:
        Dictionary with 'errors' list and 'warnings' list
    """
    errors = []
    warnings = []
    
    # Check for required fields (this depends on the specific analysis type)
    # For now, this is a placeholder for future validation logic
    
    if not isinstance(data, dict):
        errors.append("Invalid data format")
        return {'errors': errors, 'warnings': warnings}
    
    # Validate file-related fields if present
    if 'filename' in data:
        filename = data['filename']
        if not filename or not isinstance(filename, str):
            errors.append("Invalid filename")
        elif len(filename) > 255:
            errors.append("Filename too long")
    
    # Add more validation rules as needed
    
    return {'errors': errors, 'warnings': warnings}


def is_valid_json(json_string: str) -> bool:
    """
    Check if a string is valid JSON.
    
    Args:
        json_string: String to validate
        
    Returns:
        True if valid JSON, False otherwise
    """
    try:
        import json
        json.loads(json_string)
        return True
    except (ValueError, TypeError):
        return False


def validate_pagination_params(page: Union[str, int], limit: Union[str, int]) -> Dict[str, int]:
    """
    Validate and sanitize pagination parameters.
    
    Args:
        page: Page number
        limit: Items per page limit
        
    Returns:
        Dictionary with validated 'page' and 'limit' values
    """
    try:
        page = int(page) if page else 1
        limit = int(limit) if limit else 10
        
        # Set reasonable bounds
        page = max(1, page)  # Page must be at least 1
        limit = max(1, min(100, limit))  # Limit between 1 and 100
        
        return {'page': page, 'limit': limit}
        
    except (ValueError, TypeError):
        return {'page': 1, 'limit': 10}


def validate_search_query(query: str) -> str:
    """
    Validate and sanitize search query.
    
    Args:
        query: Search query string
        
    Returns:
        Sanitized search query
    """
    if not query or not isinstance(query, str):
        return ''
    
    # Remove dangerous characters but keep spaces and basic punctuation
    query = re.sub(r'[<>"\'\\\x00-\x1f]', '', query.strip())
    
    # Limit length
    if len(query) > 100:
        query = query[:100]
    
    return query