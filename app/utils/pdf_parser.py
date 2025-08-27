"""
PDF parsing utilities for BrainBudget.
Extract text and data from PDF bank statements.
"""
import logging
import io
from typing import Dict, Any, List, Optional, Tuple
import re

# PDF parsing libraries (will be installed via requirements.txt)
try:
    import PyPDF2
    from PIL import Image
    import pytesseract
    PDF_PARSING_AVAILABLE = True
except ImportError:
    PDF_PARSING_AVAILABLE = False


logger = logging.getLogger(__name__)


class PDFParser:
    """PDF parsing utility for bank statements."""

    def __init__(self):
        """Initialize PDF parser."""
        self.supported_formats = ['pdf', 'png', 'jpg', 'jpeg']

        if not PDF_PARSING_AVAILABLE:
            logger.warning("PDF parsing libraries not available. Install PyPDF2, PIL, and pytesseract.")

    def parse_pdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """
        Parse PDF file and extract text content.

        Args:
            pdf_data: PDF file data as bytes

        Returns:
            Dictionary containing extracted text and metadata
        """
        if not PDF_PARSING_AVAILABLE:
            return {
                'success': False,
                'error': 'PDF parsing not available. Using AI-only analysis.',
                'text': '',
                'pages': 0
            }

        try:
            # Create PDF reader from bytes
            pdf_file = io.BytesIO(pdf_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            # Extract text from all pages
            extracted_text = []
            page_count = len(pdf_reader.pages)

            for page_num in range(page_count):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()

                if text.strip():
                    extracted_text.append(text)
                else:
                    # If text extraction fails, may need OCR processing
                    logger.warning(f"No text found on page {page_num + 1}, may need OCR")

            full_text = '\n'.join(extracted_text)

            logger.info(f"Extracted text from {page_count} pages, {len(full_text)} characters")

            return {
                'success': True,
                'text': full_text,
                'pages': page_count,
                'has_text': len(full_text.strip()) > 0
            }

        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'pages': 0
            }

    def parse_image(self, image_data: bytes, file_type: str) -> Dict[str, Any]:
        """
        Parse image file using OCR to extract text.

        Args:
            image_data: Image file data as bytes
            file_type: Image MIME type

        Returns:
            Dictionary containing extracted text and metadata
        """
        if not PDF_PARSING_AVAILABLE:
            return {
                'success': False,
                'error': 'OCR parsing not available. Using AI-only analysis.',
                'text': '',
                'confidence': 0
            }

        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Use pytesseract for OCR
            extracted_text = pytesseract.image_to_string(image)

            # Get confidence score if available
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            except:
                avg_confidence = 0

            logger.info(f"OCR extracted {len(extracted_text)} characters with {avg_confidence:.1f}% confidence")

            return {
                'success': True,
                'text': extracted_text,
                'confidence': round(avg_confidence, 1),
                'has_text': len(extracted_text.strip()) > 0
            }

        except Exception as e:
            logger.error(f"Error parsing image with OCR: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'confidence': 0
            }

    def extract_transactions_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract transaction data from parsed text using regex patterns.

        Args:
            text: Extracted text from PDF/image

        Returns:
            List of transaction dictionaries
        """
        transactions = []

        try:
            # Common patterns for bank statements
            patterns = [
                # Pattern: MM/DD/YYYY DESCRIPTION AMOUNT
                r'(\d{1,2}/\d{1,2}/\d{4})\s+([A-Za-z0-9\s\-\*\.]+?)\s+([\-\$]?\d+\.\d{2})',

                # Pattern: MM-DD-YYYY DESCRIPTION AMOUNT
                r'(\d{1,2}-\d{1,2}-\d{4})\s+([A-Za-z0-9\s\-\*\.]+?)\s+([\-\$]?\d+\.\d{2})',

                # Pattern: YYYY-MM-DD DESCRIPTION AMOUNT
                r'(\d{4}-\d{1,2}-\d{1,2})\s+([A-Za-z0-9\s\-\*\.]+?)\s+([\-\$]?\d+\.\d{2})',

                # Pattern: DD/MM/YYYY DESCRIPTION AMOUNT (European format)
                r'(\d{1,2}/\d{1,2}/\d{4})\s+([A-Za-z0-9\s\-\*\.]+?)\s+([\-\$]?\d+\.\d{2})'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)

                for match in matches:
                    date_str, description, amount_str = match

                    # Parse date
                    parsed_date = self._parse_date(date_str)
                    if not parsed_date:
                        continue

                    # Parse amount
                    parsed_amount = self._parse_amount(amount_str)
                    if parsed_amount is None:
                        continue

                    # Clean description
                    cleaned_description = self._clean_description(description)
                    if not cleaned_description:
                        continue

                    transaction = {
                        'date': parsed_date,
                        'description': cleaned_description,
                        'amount': parsed_amount,
                        'type': 'debit' if parsed_amount < 0 else 'credit',
                        'raw_text': f"{date_str} {description} {amount_str}".strip()
                    }

                    transactions.append(transaction)

            # Remove duplicates based on date, description, and amoun
            unique_transactions = []
            seen = set()

            for txn in transactions:
                key = (txn['date'], txn['description'], txn['amount'])
                if key not in seen:
                    seen.add(key)
                    unique_transactions.append(txn)

            logger.info(f"Extracted {len(unique_transactions)} unique transactions from text")
            return unique_transactions

        except Exception as e:
            logger.error(f"Error extracting transactions from text: {e}")
            return []

    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse various date formats and return standardized format.

        Args:
            date_str: Date string to parse

        Returns:
            Standardized date string (YYYY-MM-DD) or None if invalid
        """
        try:
            from datetime import datetime

            # Common date formats
            formats = [
                '%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d',
                '%d/%m/%Y', '%d-%m-%Y',
                '%m/%d/%y', '%m-%d-%y',
                '%d/%m/%y', '%d-%m-%y'
            ]

            for fmt in formats:
                try:
                    parsed = datetime.strptime(date_str.strip(), fmt)
                    return parsed.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            return None

        except Exception:
            return None

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse amount string and return float value.

        Args:
            amount_str: Amount string to parse

        Returns:
            Float amount or None if invalid
        """
        try:
            # Remove currency symbols and extra spaces
            cleaned = re.sub(r'[$,\s]', '', amount_str.strip())

            # Check for negative indicators
            is_negative = cleaned.startswith('-') or amount_str.strip().startswith('(')

            # Remove negative sign and parentheses
            cleaned = re.sub(r'[\-\(\)]', '', cleaned)

            # Convert to float
            amount = float(cleaned)

            return -amount if is_negative else amount

        except (ValueError, TypeError):
            return None

    def _clean_description(self, description: str) -> str:
        """
        Clean and normalize transaction description.

        Args:
            description: Raw description string

        Returns:
            Cleaned description string
        """
        if not description:
            return ''

        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', description.strip())

        # Remove common bank codes and reference numbers
        cleaned = re.sub(r'\b(REF|TXN|ID|#)\s*\d+\b', '', cleaned, flags=re.IGNORECASE)

        # Remove asterisks used for pending transactions
        cleaned = re.sub(r'\*+', '', cleaned)

        # Capitalize properly
        cleaned = cleaned.title()

        return cleaned.strip()

    def detect_bank_type(self, text: str) -> Optional[str]:
        """
        Detect bank type from statement text.

        Args:
            text: Extracted text from statement

        Returns:
            Bank name or type if detected, None otherwise
        """
        try:
            text_upper = text.upper()

            # Common bank patterns
            bank_patterns = {
                'Chase': r'CHASE|JPM',
                'Bank of America': r'BANK\s+OF\s+AMERICA|BOA',
                'Wells Fargo': r'WELLS\s+FARGO|WF',
                'Citibank': r'CITI|CITIBANK',
                'Capital One': r'CAPITAL\s+ONE',
                'US Bank': r'U\.?S\.?\s+BANK',
                'PNC': r'PNC\s+BANK',
                'TD Bank': r'TD\s+BANK',
                'Ally': r'ALLY\s+BANK',
                'Discover': r'DISCOVER\s+BANK'
            }

            for bank_name, pattern in bank_patterns.items():
                if re.search(pattern, text_upper):
                    logger.info(f"Detected bank: {bank_name}")
                    return bank_name

            return None

        except Exception as e:
            logger.error(f"Error detecting bank type: {e}")
            return None

    def validate_statement(self, text: str) -> Dict[str, Any]:
        """
        Validate if the text appears to be from a bank statement.

        Args:
            text: Extracted text to validate

        Returns:
            Validation result with confidence score
        """
        try:
            score = 0
            indicators = []

            # Check for common bank statement indicators
            text_upper = text.upper()

            # Look for banking terms
            banking_terms = [
                'STATEMENT', 'ACCOUNT', 'BALANCE', 'TRANSACTION',
                'DEPOSIT', 'WITHDRAWAL', 'DEBIT', 'CREDIT',
                'BEGINNING BALANCE', 'ENDING BALANCE'
            ]

            for term in banking_terms:
                if term in text_upper:
                    score += 10
                    indicators.append(f"Found term: {term}")

            # Look for date patterns (transactions should have dates)
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'\d{1,2}-\d{1,2}-\d{4}',
                r'\d{4}-\d{1,2}-\d{1,2}'
            ]

            date_count = 0
            for pattern in date_patterns:
                matches = re.findall(pattern, text)
                date_count += len(matches)

            if date_count >= 3:
                score += 20
                indicators.append(f"Found {date_count} date patterns")

            # Look for money amounts
            money_pattern = r'\$?\d+\.\d{2}'
            money_matches = re.findall(money_pattern, text)

            if len(money_matches) >= 3:
                score += 20
                indicators.append(f"Found {len(money_matches)} monetary amounts")

            # Determine confidence level
            if score >= 40:
                confidence = 'high'
            elif score >= 20:
                confidence = 'medium'
            else:
                confidence = 'low'

            result = {
                'is_valid': score >= 20,
                'confidence': confidence,
                'score': score,
                'indicators': indicators
            }

            logger.info(f"Statement validation: {confidence} confidence (score: {score})")
            return result

        except Exception as e:
            logger.error(f"Error validating statement: {e}")
            return {
                'is_valid': False,
                'confidence': 'low',
                'score': 0,
                'indicators': ['Error during validation']
            }
