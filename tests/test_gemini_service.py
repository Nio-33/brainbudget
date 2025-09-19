"""
Gemini AI Service Tests
=======================

Tests for Google Gemini AI integration and bank statement analysis.
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock

from app.services.gemini_ai import GeminiAIService


class TestGeminiAIService:
    """Test Gemini AI service functionality."""
    
    @pytest.fixture
    def gemini_service(self):
        """Create a Gemini AI service instance for testing."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model:
            
            service = GeminiAIService('test-api-key')
            service.model = Mock()
            service.vision_model = Mock()
            return service
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content for testing."""
        return b'%PDF-1.4\nSample bank statement content'
    
    @pytest.fixture
    def sample_transactions(self):
        """Sample transaction data for testing."""
        return [
            {
                "date": "2024-01-15",
                "description": "COFFEE SHOP",
                "amount": -4.50,
                "type": "debit",
                "balance": 1234.56
            },
            {
                "date": "2024-01-14",
                "description": "SALARY DEPOSIT",
                "amount": 3000.00,
                "type": "credit",
                "balance": 1239.06
            },
            {
                "date": "2024-01-13",
                "description": "GROCERY STORE",
                "amount": -125.50,
                "type": "debit",
                "balance": -1760.94
            }
        ]
    
    def test_initialization_success(self):
        """Test successful Gemini AI service initialization."""
        with patch('google.generativeai.configure') as mock_configure, \
             patch('google.generativeai.GenerativeModel') as mock_model:
            
            service = GeminiAIService('test-api-key')
            
            assert service.api_key == 'test-api-key'
            mock_configure.assert_called_with(api_key='test-api-key')
            assert mock_model.call_count == 2  # Two models initialized
    
    def test_initialization_failure(self):
        """Test Gemini AI service initialization failure."""
        with patch('google.generativeai.configure') as mock_configure:
            mock_configure.side_effect = Exception("API key invalid")
            
            with pytest.raises(Exception):
                GeminiAIService('invalid-api-key')
    
    def test_extract_transactions_success(self, gemini_service, sample_pdf_content, sample_transactions):
        """Test successful transaction extraction from document."""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = json.dumps(sample_transactions)
        gemini_service.vision_model.generate_content.return_value = mock_response
        
        result = gemini_service._extract_transactions(sample_pdf_content, 'application/pdf')
        
        assert len(result) == 3
        assert result[0]['description'] == 'COFFEE SHOP'
        assert result[0]['amount'] == -4.50
        assert result[1]['amount'] == 3000.00
    
    def test_extract_transactions_with_markdown(self, gemini_service, sample_pdf_content, sample_transactions):
        """Test transaction extraction with markdown-formatted response."""
        # Mock Gemini response with markdown code blocks
        mock_response = Mock()
        mock_response.text = f"```json\n{json.dumps(sample_transactions)}\n```"
        gemini_service.vision_model.generate_content.return_value = mock_response
        
        result = gemini_service._extract_transactions(sample_pdf_content, 'application/pdf')
        
        assert len(result) == 3
        assert result[0]['description'] == 'COFFEE SHOP'
    
    def test_extract_transactions_invalid_json(self, gemini_service, sample_pdf_content):
        """Test transaction extraction with invalid JSON response."""
        mock_response = Mock()
        mock_response.text = "Invalid JSON response"
        gemini_service.vision_model.generate_content.return_value = mock_response
        
        result = gemini_service._extract_transactions(sample_pdf_content, 'application/pdf')
        
        assert result == []
    
    def test_extract_transactions_api_error(self, gemini_service, sample_pdf_content):
        """Test transaction extraction with API error."""
        gemini_service.vision_model.generate_content.side_effect = Exception("API error")
        
        result = gemini_service._extract_transactions(sample_pdf_content, 'application/pdf')
        
        assert result == []
    
    def test_categorize_transactions_success(self, gemini_service, sample_transactions):
        """Test successful transaction categorization."""
        # Add categories to sample transactions
        categorized_transactions = []
        for tx in sample_transactions:
            tx_copy = tx.copy()
            if 'COFFEE' in tx['description']:
                tx_copy['category'] = 'Food & Dining'
                tx_copy['subcategory'] = 'Coffee Shops'
            elif 'SALARY' in tx['description']:
                tx_copy['category'] = 'Income'
                tx_copy['subcategory'] = 'Salary'
            elif 'GROCERY' in tx['description']:
                tx_copy['category'] = 'Food & Dining'
                tx_copy['subcategory'] = 'Groceries'
            categorized_transactions.append(tx_copy)
        
        mock_response = Mock()
        mock_response.text = json.dumps(categorized_transactions)
        gemini_service.model.generate_content.return_value = mock_response
        
        result = gemini_service._categorize_transactions(sample_transactions)
        
        assert len(result) == 3
        assert result[0]['category'] == 'Food & Dining'
        assert result[0]['subcategory'] == 'Coffee Shops'
        assert result[1]['category'] == 'Income'
    
    def test_categorize_transactions_json_error(self, gemini_service, sample_transactions):
        """Test transaction categorization with JSON parsing error."""
        mock_response = Mock()
        mock_response.text = "Invalid JSON"
        gemini_service.model.generate_content.return_value = mock_response
        
        result = gemini_service._categorize_transactions(sample_transactions)
        
        # Should return original transactions with default category
        assert len(result) == 3
        for tx in result:
            assert tx['category'] == 'Other'
            assert tx['subcategory'] == 'Uncategorized'
    
    def test_generate_summary(self, gemini_service):
        """Test spending summary generation."""
        categorized_transactions = [
            {'amount': -100.00, 'category': 'Food & Dining'},
            {'amount': -50.00, 'category': 'Transportation'},
            {'amount': 3000.00, 'category': 'Income'},
            {'amount': -200.00, 'category': 'Food & Dining'},
            {'amount': -75.00, 'category': 'Entertainment'}
        ]
        
        result = gemini_service._generate_summary(categorized_transactions)
        
        assert result['total_spent'] == 425.00
        assert result['total_income'] == 3000.00
        assert result['net_change'] == 2575.00
        assert result['transaction_count'] == 5
        
        # Check top categories
        top_categories = result['top_categories']
        assert len(top_categories) > 0
        assert top_categories[0]['category'] == 'Food & Dining'
        assert top_categories[0]['amount'] == 300.00
        assert top_categories[0]['percentage'] == 70.6  # 300/425 * 100
    
    def test_generate_insights_success(self, gemini_service, sample_transactions):
        """Test successful insights generation."""
        summary = {
            'total_spent': 130.00,
            'total_income': 3000.00,
            'transaction_count': 3
        }
        
        insights_response = {
            'key_patterns': [
                'Regular income deposits detected',
                'Small frequent purchases observed'
            ],
            'gentle_suggestions': [
                'Consider setting up automatic savings',
                'Track small purchases to build awareness'
            ],
            'achievements': [
                'Great job tracking your spending!'
            ],
            'adhd_tips': [
                'Use visual reminders for financial goals',
                'Set up automatic transfers'
            ],
            'motivation': 'You\'re making great progress! 🌟'
        }
        
        mock_response = Mock()
        mock_response.text = json.dumps(insights_response)
        gemini_service.model.generate_content.return_value = mock_response
        
        result = gemini_service._generate_insights(sample_transactions, summary)
        
        assert 'key_patterns' in result
        assert 'gentle_suggestions' in result
        assert 'achievements' in result
        assert 'adhd_tips' in result
        assert 'motivation' in result
        assert len(result['key_patterns']) == 2
    
    def test_generate_insights_json_error(self, gemini_service, sample_transactions):
        """Test insights generation with JSON parsing error."""
        summary = {'total_spent': 100.00}
        
        mock_response = Mock()
        mock_response.text = "Invalid JSON"
        gemini_service.model.generate_content.return_value = mock_response
        
        result = gemini_service._generate_insights(sample_transactions, summary)
        
        # Should return default insights
        assert 'key_patterns' in result
        assert 'gentle_suggestions' in result
        assert 'achievements' in result
        assert 'adhd_tips' in result
        assert 'motivation' in result
    
    def test_get_default_insights(self, gemini_service):
        """Test default insights structure."""
        result = gemini_service._get_default_insights()
        
        required_keys = ['key_patterns', 'gentle_suggestions', 'achievements', 'adhd_tips', 'motivation']
        for key in required_keys:
            assert key in result
            if key != 'motivation':
                assert isinstance(result[key], list)
                assert len(result[key]) > 0
            else:
                assert isinstance(result[key], str)
                assert len(result[key]) > 0
    
    def test_analyze_bank_statement_success(self, gemini_service, sample_pdf_content):
        """Test complete bank statement analysis."""
        # Mock the extraction process
        sample_transactions = [
            {
                "date": "2024-01-15",
                "description": "COFFEE SHOP",
                "amount": -4.50,
                "type": "debit"
            }
        ]
        
        # Mock transaction extraction
        gemini_service.vision_model.generate_content.return_value.text = json.dumps(sample_transactions)
        
        # Mock categorization
        categorized_transactions = sample_transactions.copy()
        categorized_transactions[0]['category'] = 'Food & Dining'
        categorized_transactions[0]['subcategory'] = 'Coffee Shops'
        
        gemini_service.model.generate_content.side_effect = [
            Mock(text=json.dumps(categorized_transactions)),  # Categorization
            Mock(text=json.dumps({  # Insights
                'key_patterns': ['Coffee spending detected'],
                'gentle_suggestions': ['Consider brewing at home'],
                'achievements': ['Tracking your spending!'],
                'adhd_tips': ['Set coffee budget reminders'],
                'motivation': 'Great start! ☕'
            }))
        ]
        
        result = gemini_service.analyze_bank_statement(
            sample_pdf_content, 'application/pdf', 'test_statement.pdf'
        )
        
        assert result['success'] is True
        assert result['filename'] == 'test_statement.pdf'
        assert result['transaction_count'] == 1
        assert 'transactions' in result
        assert 'summary' in result
        assert 'insights' in result
        assert 'analyzed_at' in result
    
    def test_analyze_bank_statement_no_transactions(self, gemini_service, sample_pdf_content):
        """Test bank statement analysis with no transactions found."""
        # Mock empty extraction
        gemini_service.vision_model.generate_content.return_value.text = "[]"
        
        result = gemini_service.analyze_bank_statement(
            sample_pdf_content, 'application/pdf', 'empty_statement.pdf'
        )
        
        assert result['success'] is False
        assert 'No transactions found' in result['error']
        assert result['transactions'] == []
    
    def test_analyze_bank_statement_extraction_error(self, gemini_service, sample_pdf_content):
        """Test bank statement analysis with extraction error."""
        gemini_service.vision_model.generate_content.side_effect = Exception("Extraction failed")
        
        result = gemini_service.analyze_bank_statement(
            sample_pdf_content, 'application/pdf', 'error_statement.pdf'
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert result['transactions'] == []
    
    def test_generate_spending_advice_success(self, gemini_service):
        """Test successful spending advice generation."""
        user_query = "How can I reduce my food spending?"
        spending_data = {
            'summary': {
                'total_spent': 500.00,
                'category_breakdown': {
                    'Food & Dining': 200.00,
                    'Transportation': 100.00
                }
            }
        }
        
        mock_response = Mock()
        mock_response.text = "Based on your spending data, I can see you spent $200 on food. Try meal planning!"
        gemini_service.model.generate_content.return_value = mock_response
        
        result = gemini_service.generate_spending_advice(user_query, spending_data)
        
        assert "meal planning" in result.lower()
        assert "$200" in result
    
    def test_generate_spending_advice_error(self, gemini_service):
        """Test spending advice generation with error."""
        gemini_service.model.generate_content.side_effect = Exception("API error")
        
        result = gemini_service.generate_spending_advice(
            "How can I save money?", {}
        )
        
        assert "try asking again" in result.lower()
        assert "🤗" in result


class TestGeminiServiceIntegration:
    """Integration tests for Gemini AI service."""
    
    def test_full_analysis_pipeline(self):
        """Test the complete analysis pipeline from PDF to insights."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            
            # Setup mocks
            mock_vision_model = Mock()
            mock_text_model = Mock()
            mock_model_class.side_effect = [mock_text_model, mock_vision_model]
            
            service = GeminiAIService('test-api-key')
            
            # Mock extraction response
            transactions = [
                {
                    "date": "2024-01-15",
                    "description": "STARBUCKS",
                    "amount": -5.99,
                    "type": "debit"
                },
                {
                    "date": "2024-01-14",
                    "description": "PAYCHECK",
                    "amount": 2500.00,
                    "type": "credit"
                }
            ]
            
            mock_vision_model.generate_content.return_value.text = json.dumps(transactions)
            
            # Mock categorization and insights
            categorized = [
                {**tx, 'category': 'Food & Dining' if 'STARBUCKS' in tx['description'] else 'Income',
                 'subcategory': 'Coffee' if 'STARBUCKS' in tx['description'] else 'Salary'}
                for tx in transactions
            ]
            
            insights = {
                'key_patterns': ['Regular income and coffee purchases'],
                'gentle_suggestions': ['Consider coffee budget'],
                'achievements': ['Consistent income tracking'],
                'adhd_tips': ['Set coffee spending alerts'],
                'motivation': 'Great financial tracking! ☕💰'
            }
            
            mock_text_model.generate_content.side_effect = [
                Mock(text=json.dumps(categorized)),
                Mock(text=json.dumps(insights))
            ]
            
            # Run full analysis
            result = service.analyze_bank_statement(
                b'fake pdf content', 'application/pdf', 'test.pdf'
            )
            
            # Verify complete results
            assert result['success'] is True
            assert len(result['transactions']) == 2
            assert result['summary']['total_spent'] == 5.99
            assert result['summary']['total_income'] == 2500.00
            assert result['insights']['motivation'] == 'Great financial tracking! ☕💰'
    
    def test_safety_settings_applied(self):
        """Test that safety settings are properly applied to API calls."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            
            mock_model = Mock()
            mock_model_class.return_value = mock_model
            
            service = GeminiAIService('test-api-key')
            
            # Mock responses
            mock_model.generate_content.return_value.text = "[]"
            
            # Test extraction (uses safety settings)
            service._extract_transactions(b'content', 'application/pdf')
            
            # Verify safety settings were used
            call_args = mock_model.generate_content.call_args
            assert 'safety_settings' in call_args.kwargs
            
            safety_settings = call_args.kwargs['safety_settings']
            assert len(safety_settings) == 4  # Should have 4 safety categories


if __name__ == '__main__':
    pytest.main([__file__])