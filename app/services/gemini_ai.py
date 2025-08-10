"""
Google Gemini AI service for BrainBudget.
Handles PDF/image analysis of bank statements and spending categorization.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
import json
import base64
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold


logger = logging.getLogger(__name__)


class GeminiAIService:
    """Google Gemini AI service for financial document analysis."""
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini AI service.
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        self.model = None
        self.vision_model = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize Gemini models."""
        try:
            genai.configure(api_key=self.api_key)
            
            # Text model for analysis
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Vision model for image/PDF processing  
            self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
            
            logger.info("Gemini AI models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI models: {e}")
            raise
    
    def analyze_bank_statement(self, file_content: bytes, file_type: str, filename: str) -> Dict[str, Any]:
        """
        Analyze bank statement using Gemini AI.
        
        Args:
            file_content: File content as bytes
            file_type: File MIME type
            filename: Original filename
            
        Returns:
            Analysis results dictionary
        """
        try:
            logger.info(f"Starting analysis of {filename} ({file_type})")
            
            # Extract transactions from document
            transactions = self._extract_transactions(file_content, file_type)
            
            if not transactions:
                return {
                    'success': False,
                    'error': 'No transactions found in the document',
                    'transactions': [],
                    'summary': {}
                }
            
            # Categorize and analyze transactions
            categorized_transactions = self._categorize_transactions(transactions)
            summary = self._generate_summary(categorized_transactions)
            insights = self._generate_insights(categorized_transactions, summary)
            
            result = {
                'success': True,
                'filename': filename,
                'analyzed_at': datetime.utcnow().isoformat(),
                'transactions': categorized_transactions,
                'summary': summary,
                'insights': insights,
                'transaction_count': len(categorized_transactions)
            }
            
            logger.info(f"Successfully analyzed {len(categorized_transactions)} transactions from {filename}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze bank statement {filename}: {e}")
            return {
                'success': False,
                'error': str(e),
                'transactions': [],
                'summary': {}
            }
    
    def _extract_transactions(self, file_content: bytes, file_type: str) -> List[Dict[str, Any]]:
        """
        Extract transactions from bank statement using Gemini Vision.
        
        Args:
            file_content: File content as bytes
            file_type: File MIME type
            
        Returns:
            List of extracted transactions
        """
        try:
            # Prepare image data for Gemini
            image_data = {
                'mime_type': file_type,
                'data': base64.b64encode(file_content).decode('utf-8')
            }
            
            prompt = """
            Please analyze this bank statement and extract all transactions in JSON format.
            For each transaction, provide:
            - date: Transaction date (YYYY-MM-DD format)
            - description: Transaction description/merchant name
            - amount: Transaction amount (positive for credits, negative for debits)
            - type: "debit" or "credit"
            - balance: Account balance after transaction (if available)
            
            Return ONLY a valid JSON array of transactions, no other text.
            Example format:
            [
                {
                    "date": "2024-01-15",
                    "description": "COFFEE SHOP",
                    "amount": -4.50,
                    "type": "debit",
                    "balance": 1234.56
                }
            ]
            """
            
            # Generate content with safety settings
            response = self.vision_model.generate_content(
                [prompt, image_data],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Clean up response (remove markdown code blocks if present)
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            transactions = json.loads(response_text)
            logger.info(f"Extracted {len(transactions)} transactions from document")
            return transactions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to extract transactions: {e}")
            return []
    
    def _categorize_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Categorize transactions using Gemini AI.
        
        Args:
            transactions: List of transactions to categorize
            
        Returns:
            List of categorized transactions
        """
        try:
            # Prepare transactions for categorization
            transactions_text = json.dumps(transactions, indent=2)
            
            prompt = f"""
            Please categorize these financial transactions into appropriate spending categories.
            Add a "category" field to each transaction with one of these categories:
            - Food & Dining
            - Transportation
            - Shopping
            - Entertainment
            - Bills & Utilities
            - Healthcare
            - Education
            - Travel
            - Income
            - Transfer
            - Fees & Charges
            - Other
            
            Also add a "subcategory" field with a more specific classification.
            
            Transactions:
            {transactions_text}
            
            Return ONLY the JSON array with the added category and subcategory fields, no other text.
            """
            
            response = self.model.generate_content(
                prompt,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Clean up response (remove markdown code blocks if present)
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            categorized = json.loads(response_text)
            logger.info(f"Successfully categorized {len(categorized)} transactions")
            return categorized
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse categorization JSON: {e}")
            # Return original transactions with default category
            for transaction in transactions:
                transaction['category'] = 'Other'
                transaction['subcategory'] = 'Uncategorized'
            return transactions
        except Exception as e:
            logger.error(f"Failed to categorize transactions: {e}")
            # Return original transactions with default category
            for transaction in transactions:
                transaction['category'] = 'Other'
                transaction['subcategory'] = 'Uncategorized'
            return transactions
    
    def _generate_summary(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate spending summary from categorized transactions.
        
        Args:
            transactions: List of categorized transactions
            
        Returns:
            Summary dictionary
        """
        try:
            # Calculate totals by category
            category_totals = {}
            total_spent = 0
            total_income = 0
            
            for transaction in transactions:
                amount = transaction.get('amount', 0)
                category = transaction.get('category', 'Other')
                
                if amount < 0:  # Spending
                    total_spent += abs(amount)
                    if category not in category_totals:
                        category_totals[category] = 0
                    category_totals[category] += abs(amount)
                else:  # Income
                    total_income += amount
            
            # Sort categories by spending amount
            sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            
            summary = {
                'total_spent': round(total_spent, 2),
                'total_income': round(total_income, 2),
                'net_change': round(total_income - total_spent, 2),
                'transaction_count': len(transactions),
                'top_categories': [
                    {'category': cat, 'amount': round(amount, 2), 'percentage': round((amount / total_spent) * 100, 1)}
                    for cat, amount in sorted_categories[:5]
                ],
                'category_breakdown': {cat: round(amount, 2) for cat, amount in category_totals.items()}
            }
            
            logger.info(f"Generated summary: ${total_spent:.2f} spent across {len(category_totals)} categories")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return {}
    
    def _generate_insights(self, transactions: List[Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate ADHD-friendly insights and recommendations.
        
        Args:
            transactions: List of categorized transactions
            summary: Spending summary
            
        Returns:
            Insights dictionary
        """
        try:
            # Prepare data for AI analysis
            data = {
                'summary': summary,
                'transaction_sample': transactions[:10]  # First 10 transactions for context
            }
            
            prompt = f"""
            Based on this spending data, provide ADHD-friendly financial insights and gentle recommendations.
            
            Data:
            {json.dumps(data, indent=2)}
            
            Please provide insights in JSON format with these fields:
            - "key_patterns": List of 2-3 spending patterns observed
            - "gentle_suggestions": List of 2-3 positive, non-judgmental suggestions
            - "achievements": List of 1-2 positive things the user did well
            - "adhd_tips": List of 2-3 ADHD-specific budgeting tips
            - "motivation": A single encouraging message
            
            Keep all messages positive, supportive, and non-judgmental. Focus on progress, not perfection.
            Use encouraging emojis and friendly language suitable for someone with ADHD.
            """
            
            response = self.model.generate_content(
                prompt,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Clean up response (remove markdown code blocks if present)
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            insights = json.loads(response_text)
            logger.info("Generated ADHD-friendly insights successfully")
            return insights
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse insights JSON: {e}")
            return self._get_default_insights()
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return self._get_default_insights()
    
    def _get_default_insights(self) -> Dict[str, Any]:
        """
        Get default insights when AI generation fails.
        
        Returns:
            Default insights dictionary
        """
        return {
            'key_patterns': [
                "You're actively tracking your spending - that's awesome! 🌟",
                "Your transactions show a variety of spending categories"
            ],
            'gentle_suggestions': [
                "Keep up the great work with tracking your expenses! 💪",
                "Consider celebrating small wins in your financial journey"
            ],
            'achievements': [
                "You took the step to analyze your spending - that's huge! 🎉"
            ],
            'adhd_tips': [
                "Try setting up automatic transfers to make saving easier",
                "Use visual reminders for your financial goals"
            ],
            'motivation': "Every step forward is progress worth celebrating! You've got this! 🚀"
        }
    
    def generate_spending_advice(self, user_query: str, spending_data: Dict[str, Any]) -> str:
        """
        Generate personalized spending advice based on user query.
        
        Args:
            user_query: User's question or concern
            spending_data: User's spending analysis data
            
        Returns:
            AI-generated advice
        """
        try:
            prompt = f"""
            A user with ADHD is asking for financial advice. Please provide a helpful, supportive,
            and non-judgmental response based on their spending data.
            
            User Question: {user_query}
            
            Spending Data:
            {json.dumps(spending_data, indent=2)}
            
            Provide a friendly, encouraging response that:
            - Addresses their specific question
            - Uses their actual spending data
            - Offers practical, ADHD-friendly tips
            - Maintains a positive, supportive tone
            - Includes encouraging emojis
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Failed to generate spending advice: {e}")
            return "I'd love to help you with that! Could you try asking again? Sometimes I need a moment to think through the best advice for you! 🤗"