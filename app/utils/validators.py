"""
Validation utilities for BrainBudget.
Input validation, file validation, and data sanitization.
"""
import re
import os
import logging
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
from typing import Any, Dict, List, Optional, Union
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


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
        Sanitized tex
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


def validate_file_content(file_content: bytes, filename: str) -> Dict[str, Union[bool, str]]:
    """
    Validate file content using magic numbers and content analysis.
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        
    Returns:
        Dictionary with validation result and details
    """
    result = {'is_valid': False, 'message': '', 'detected_type': ''}
    
    try:
        # Detect file type using magic numbers
        if len(file_content) < 4:
            result['message'] = 'File too small to analyze'
            return result
            
        # Try to detect file type with python-magic if available
        if MAGIC_AVAILABLE:
            try:
                detected_type = magic.from_buffer(file_content, mime=True)
                result['detected_type'] = detected_type
                
                # Check if detected type matches expected types
                allowed_mime_types = {
                    'application/pdf',
                    'image/png', 
                    'image/jpeg',
                    'image/jpg'
                }
                
                if detected_type not in allowed_mime_types:
                    result['message'] = f'Invalid file type detected: {detected_type}'
                    return result
                    
            except Exception as e:
                logger.warning(f"Magic detection failed: {e}")
        else:
            # Fallback to manual magic number checking
            magic_numbers = {
                b'%PDF': 'application/pdf',
                b'\x89PNG': 'image/png',
                b'\xff\xd8\xff': 'image/jpeg'
            }
            
            detected = False
            for magic_bytes, mime_type in magic_numbers.items():
                if file_content.startswith(magic_bytes):
                    result['detected_type'] = mime_type
                    detected = True
                    break
                    
            if not detected:
                result['message'] = 'File type not recognized'
                return result
        
        # Additional security checks
        
        # Check for embedded scripts or suspicious content
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'<%',
            b'<?php',
            b'exec(',
            b'system(',
            b'shell_exec',
            b'eval(',
            b'base64_decode'
        ]
        
        content_lower = file_content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                result['message'] = f'Suspicious content detected: {pattern.decode("utf-8", errors="ignore")}'
                logger.warning(f'Suspicious file content detected in {filename}: {pattern}')
                return result
        
        # Check file size constraints
        max_size = 16 * 1024 * 1024  # 16MB
        if len(file_content) > max_size:
            result['message'] = f'File too large: {len(file_content)} bytes (max: {max_size})'
            return result
            
        result['is_valid'] = True
        result['message'] = 'File content validated successfully'
        return result
        
    except Exception as e:
        logger.error(f'Error validating file content: {e}')
        result['message'] = 'Error during file validation'
        return result


def sanitize_html_input(text: str) -> str:
    """
    Sanitize HTML input to prevent XSS attacks.
    
    Args:
        text: Input text that may contain HTML
        
    Returns:
        Sanitized text with HTML escaped
    """
    if not text or not isinstance(text, str):
        return ''
    
    # HTML escape basic characters
    html_escape_table = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
    }
    
    for char, escape in html_escape_table.items():
        text = text.replace(char, escape)
    
    return text


def validate_password_strength(password: str) -> Dict[str, Union[bool, List[str]]]:
    """
    Validate password strength and security.
    
    Args:
        password: Password to validate
        
    Returns:
        Dictionary with validation result and requirements
    """
    issues = []
    
    if not password or not isinstance(password, str):
        return {'is_valid': False, 'issues': ['Password is required']}
    
    # Check length
    if len(password) < 8:
        issues.append('Password must be at least 8 characters long')
    
    if len(password) > 128:
        issues.append('Password must be less than 128 characters')
    
    # Check complexity
    if not re.search(r'[a-z]', password):
        issues.append('Password must contain at least one lowercase letter')
    
    if not re.search(r'[A-Z]', password):
        issues.append('Password must contain at least one uppercase letter')
    
    if not re.search(r'\d', password):
        issues.append('Password must contain at least one number')
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        issues.append('Password must contain at least one special character')
    
    # Check for common weak passwords
    weak_passwords = {
        'password', 'password123', '123456', '123456789', 'qwerty',
        'abc123', 'password1', 'admin', 'letmein', 'welcome'
    }
    
    if password.lower() in weak_passwords:
        issues.append('Password is too common and easily guessable')
    
    # Check for sequential characters
    if re.search(r'(.)\1{2,}', password):  # 3+ repeated characters
        issues.append('Password should not contain repeated characters')
    
    return {
        'is_valid': len(issues) == 0,
        'issues': issues
    }


def validate_currency_code(currency: str) -> bool:
    """
    Validate currency code format.
    
    Args:
        currency: Currency code to validate
        
    Returns:
        True if valid currency code, False otherwise
    """
    if not currency or not isinstance(currency, str):
        return False
    
    # Must be 3 letters, uppercase
    return bool(re.match(r'^[A-Z]{3}$', currency.strip().upper()))


def validate_user_profile_data(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize user profile data.
    
    Args:
        profile_data: User profile data to validate
        
    Returns:
        Dictionary with validation results and sanitized data
    """
    errors = []
    sanitized = {}
    
    # Validate display name
    if 'display_name' in profile_data:
        display_name = sanitize_text_input(profile_data['display_name'], max_length=50)
        if len(display_name.strip()) < 1:
            errors.append('Display name cannot be empty')
        else:
            sanitized['display_name'] = display_name
    
    # Validate email
    if 'email' in profile_data:
        email = profile_data['email']
        if not validate_email(email):
            errors.append('Invalid email format')
        else:
            sanitized['email'] = email.strip().lower()
    
    # Validate settings
    if 'settings' in profile_data and isinstance(profile_data['settings'], dict):
        settings = {}
        
        # Validate currency
        if 'currency' in profile_data['settings']:
            currency = profile_data['settings']['currency']
            if validate_currency_code(currency):
                settings['currency'] = currency.upper()
            else:
                settings['currency'] = 'USD'  # Default fallback
        
        # Validate boolean settings
        bool_settings = ['notifications_enabled', 'dark_mode', 'email_updates']
        for setting in bool_settings:
            if setting in profile_data['settings']:
                value = profile_data['settings'][setting]
                settings[setting] = bool(value) if isinstance(value, (bool, int)) else False
        
        sanitized['settings'] = settings
    
    return {
        'errors': errors,
        'sanitized_data': sanitized,
        'is_valid': len(errors) == 0
    }


def validate_financial_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate financial data for security and consistency.
    
    Args:
        data: Financial data to validate
        
    Returns:
        Validation results and sanitized data
    """
    errors = []
    warnings = []
    sanitized = {}
    
    # Validate transaction data if present
    if 'transactions' in data and isinstance(data['transactions'], list):
        validated_transactions = []
        for i, transaction in enumerate(data['transactions']):
            try:
                validated_tx = validate_transaction_data(transaction)
                validated_transactions.append(validated_tx)
            except Exception as e:
                errors.append(f'Invalid transaction at index {i}: {str(e)}')
        
        sanitized['transactions'] = validated_transactions
    
    # Validate summary data
    if 'summary' in data and isinstance(data['summary'], dict):
        summary = {}
        
        # Validate monetary amounts
        for field in ['total_spent', 'total_income', 'net_change']:
            if field in data['summary']:
                amount = validate_amount(data['summary'][field])
                if amount is not None:
                    summary[field] = amount
                else:
                    warnings.append(f'Invalid amount for {field}')
        
        # Validate counts
        for field in ['transaction_count']:
            if field in data['summary']:
                try:
                    count = int(data['summary'][field])
                    if count >= 0:
                        summary[field] = count
                    else:
                        warnings.append(f'Negative count for {field}')
                except (ValueError, TypeError):
                    warnings.append(f'Invalid count for {field}')
        
        sanitized['summary'] = summary
    
    return {
        'errors': errors,
        'warnings': warnings,
        'sanitized_data': sanitized,
        'is_valid': len(errors) == 0
    }


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key format and structure.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not api_key or not isinstance(api_key, str):
        return False
    
    # Basic format validation (adjust based on your API key format)
    api_key = api_key.strip()
    
    # Check length (most API keys are between 20-100 characters)
    if not (20 <= len(api_key) <= 100):
        return False
    
    # Check for valid characters (alphanumeric + some special chars)
    if not re.match(r'^[A-Za-z0-9\-_\.]+$', api_key):
        return False
    
    return True


def validate_file_upload_request(files: Dict, max_files: int = 1) -> Dict[str, Any]:
    """
    Validate file upload request.
    
    Args:
        files: Files from request
        max_files: Maximum number of files allowed
        
    Returns:
        Validation results
    """
    errors = []
    
    if not files:
        errors.append('No files provided')
        return {'errors': errors, 'is_valid': False}
    
    if len(files) > max_files:
        errors.append(f'Too many files (max: {max_files})')
    
    # Validate each file
    for filename, file in files.items():
        if not hasattr(file, 'filename') or not file.filename:
            errors.append('File must have a filename')
            continue
        
        # Check filename
        if not validate_file_type(file.filename, {'pdf', 'png', 'jpg', 'jpeg'}):
            errors.append(f'Invalid file type: {file.filename}')
        
        # Check if file has content
        if hasattr(file, 'content_length') and file.content_length == 0:
            errors.append('File is empty')
    
    return {
        'errors': errors,
        'is_valid': len(errors) == 0
    }


def rate_limit_key_validator(key: str) -> bool:
    """
    Validate rate limiting key format.
    
    Args:
        key: Rate limiting key
        
    Returns:
        True if valid, False otherwise
    """
    if not key or not isinstance(key, str):
        return False
    
    # Key should be reasonable length and contain safe characters
    if not (5 <= len(key) <= 100):
        return False
    
    # Allow alphanumeric, hyphens, underscores, and colons
    return bool(re.match(r'^[A-Za-z0-9\-_:]+$', key))


def validate_date_range(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Validate date range for queries.
    
    Args:
        start_date: Start date string
        end_date: End date string
        
    Returns:
        Validation results with parsed dates
    """
    errors = []
    result = {}
    
    # Validate individual dates
    if not validate_date_string(start_date):
        errors.append('Invalid start date format')
    else:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            result['start_date'] = start
        except ValueError:
            errors.append('Invalid start date')
    
    if not validate_date_string(end_date):
        errors.append('Invalid end date format')
    else:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            result['end_date'] = end
        except ValueError:
            errors.append('Invalid end date')
    
    # Validate date range logic
    if 'start_date' in result and 'end_date' in result:
        if result['start_date'] > result['end_date']:
            errors.append('Start date must be before end date')
        
        # Check for reasonable range (not more than 2 years)
        if result['end_date'] - result['start_date'] > timedelta(days=730):
            errors.append('Date range too large (max: 2 years)')
    
    return {
        'errors': errors,
        'is_valid': len(errors) == 0,
        'parsed_dates': result
    }
