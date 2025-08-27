"""
AI-powered bank statement analyzer using Google Gemini API.
Provides ADHD-friendly transaction analysis and categorization.
"""
import logging
import re
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)

@dataclass
class Transaction:
    """Represents a single transaction from a bank statement."""
    date: date
    description: str
    amount: float
    transaction_type: str  # 'debit', 'credit'
    category: str
    confidence: float  # AI confidence in categorization (0-1)
    raw_text: str = ""  # Original text from statemen

@dataclass
class SpendingInsight:
    """Represents an insight about spending patterns."""
    title: str
    message: str
    category: str
    amount: float
    percentage: float
    insight_type: str  # 'positive', 'neutral', 'improvement'
    recommendation: Optional[str] = None

@dataclass
class AnalysisResult:
    """Complete analysis result for a bank statement."""
    transactions: List[Transaction]
    spending_breakdown: Dict[str, float]
    insights: List[SpendingInsight]
    total_income: float
    total_expenses: float
    net_flow: float
    analysis_period: Tuple[date, date]
    confidence_score: float

class StatementAnalyzer:
    """AI-powered bank statement analyzer with ADHD-friendly features."""

    # Spending categories for transaction classification
    CATEGORIES = {
        'Housing': ['rent', 'mortgage', 'property tax', 'home insurance', 'utilities', 'repairs', 'maintenance'],
        'Transportation': ['gas', 'fuel', 'uber', 'lyft', 'taxi', 'bus', 'train', 'car payment', 'insurance', 'parking'],
        'Food & Dining': ['restaurant', 'fast food', 'coffee', 'groceries', 'supermarket', 'food delivery', 'dining'],
        'Entertainment': ['movie', 'streaming', 'games', 'concerts', 'events', 'books', 'hobbies', 'subscription'],
        'Shopping': ['amazon', 'store', 'clothing', 'electronics', 'online shopping', 'retail'],
        'Healthcare': ['doctor', 'medical', 'pharmacy', 'prescription', 'dental', 'therapy', 'health'],
        'Bills & Utilities': ['phone', 'internet', 'electricity', 'water', 'cable', 'insurance', 'subscription'],
        'Income': ['salary', 'paycheck', 'deposit', 'refund', 'interest', 'dividend', 'freelance'],
        'Other': ['atm', 'fee', 'transfer', 'cash', 'miscellaneous']
    }

    def __init__(self, api_key: str):
        """Initialize the analyzer with Gemini API key."""
        self.api_key = api_key
        genai.configure(api_key=api_key)

        # Configure Gemini model
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-latest",
            generation_config={
                "temperature": 0.1,  # Low temperature for consistent categorization
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096,
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        )

        logger.info("Statement analyzer initialized with Gemini AI")

    def analyze_text_statement(self, statement_text: str) -> AnalysisResult:
        """Analyze a bank statement from text content."""
        try:
            # Extract transactions from tex
            transactions = self._extract_transactions(statement_text)

            # Categorize transactions using AI
            categorized_transactions = self._categorize_transactions(transactions)

            # Generate insights and recommendations
            analysis = self._generate_analysis(categorized_transactions)

            logger.info(f"Successfully analyzed statement with {len(categorized_transactions)} transactions")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing statement: {e}")
            raise

    def analyze_image_statement(self, image_data: bytes, mime_type: str) -> AnalysisResult:
        """Analyze a bank statement from image data (PDF or image)."""
        try:
            # Use Gemini Vision to extract text from image
            image_part = {
                "mime_type": mime_type,
                "data": image_data
            }

            prompt = self._create_extraction_prompt()
            response = self.model.generate_content([prompt, image_part])

            if not response.text:
                raise ValueError("Could not extract text from image")

            # Process the extracted text as a regular text statemen
            return self.analyze_text_statement(response.text)

        except Exception as e:
            logger.error(f"Error analyzing image statement: {e}")
            raise

    def _extract_transactions(self, statement_text: str) -> List[Dict[str, Any]]:
        """Extract transaction data from statement text using AI."""
        prompt = f"""
        You are a helpful AI assistant that extracts transaction data from bank statements.
        Please analyze the following bank statement text and extract all transactions.

        For each transaction, provide:
        - Date (YYYY-MM-DD format)
        - Description (clean, readable description)
        - Amount (positive number, we'll determine debit/credit separately)
        - Type (either "debit" or "credit")
        - Raw text (original line from statement)

        Return the data as a JSON array of transaction objects.
        Be very careful with amounts - include decimals and handle negative/positive correctly.

        Bank statement text:
        {statement_text}

        Respond with only the JSON array, no additional text.
        """

        try:
            response = self.model.generate_content(prompt)

            if not response.text:
                raise ValueError("No response from Gemini API")

            # Clean up response and parse JSON
            json_text = response.text.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:-3]
            elif json_text.startswith('```'):
                json_text = json_text[3:-3]

            transactions = json.loads(json_text)

            logger.info(f"Extracted {len(transactions)} transactions from statement")
            return transactions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse transaction JSON: {e}")
            raise ValueError("Could not parse transaction data from AI response")
        except Exception as e:
            logger.error(f"Error extracting transactions: {e}")
            raise

    def _categorize_transactions(self, raw_transactions: List[Dict[str, Any]]) -> List[Transaction]:
        """Categorize transactions using AI with predefined categories."""
        categorized = []

        for raw_txn in raw_transactions:
            try:
                # Create categorization promp
                prompt = f"""
                Please categorize this transaction into one of these categories:
                {', '.join(self.CATEGORIES.keys())}

                Transaction: {raw_txn.get('description', '')}
                Amount: ${raw_txn.get('amount', 0)}

                Consider these category guidelines:
                - Housing: Rent, mortgage, utilities, home repairs
                - Transportation: Gas, rideshares, public transit, car payments
                - Food & Dining: Restaurants, groceries, food delivery
                - Entertainment: Movies, streaming, games, hobbies
                - Shopping: Retail purchases, online shopping, clothing
                - Healthcare: Medical expenses, pharmacy, therapy
                - Bills & Utilities: Phone, internet, subscriptions
                - Income: Salary, payments received, refunds
                - Other: ATM fees, transfers, unclear transactions

                Respond with only the category name and a confidence score (0-1).
                Format: "Category: [category_name], Confidence: [0.X]"
                """

                response = self.model.generate_content(prompt)

                if not response.text:
                    category, confidence = "Other", 0.3
                else:
                    # Parse AI response
                    category, confidence = self._parse_categorization_response(response.text)

                # Convert raw transaction to Transaction objec
                transaction = Transaction(
                    date=datetime.strptime(raw_txn.get('date', '2025-01-01'), '%Y-%m-%d').date(),
                    description=raw_txn.get('description', 'Unknown Transaction'),
                    amount=float(raw_txn.get('amount', 0)),
                    transaction_type=raw_txn.get('type', 'debit'),
                    category=category,
                    confidence=confidence,
                    raw_text=raw_txn.get('raw_text', '')
                )

                categorized.append(transaction)

            except Exception as e:
                logger.warning(f"Error categorizing transaction: {e}")
                # Fallback transaction with low confidence
                transaction = Transaction(
                    date=datetime.strptime(raw_txn.get('date', '2025-01-01'), '%Y-%m-%d').date(),
                    description=raw_txn.get('description', 'Unknown Transaction'),
                    amount=float(raw_txn.get('amount', 0)),
                    transaction_type=raw_txn.get('type', 'debit'),
                    category="Other",
                    confidence=0.1,
                    raw_text=raw_txn.get('raw_text', '')
                )
                categorized.append(transaction)

        logger.info(f"Categorized {len(categorized)} transactions")
        return categorized

    def _parse_categorization_response(self, response_text: str) -> Tuple[str, float]:
        """Parse AI categorization response to extract category and confidence."""
        try:
            # Look for category pattern
            category_match = re.search(r'Category:\s*([^,]+)', response_text, re.IGNORECASE)
            confidence_match = re.search(r'Confidence:\s*([\d.]+)', response_text, re.IGNORECASE)

            category = "Other"
            if category_match:
                potential_category = category_match.group(1).strip()
                # Validate against known categories
                if potential_category in self.CATEGORIES:
                    category = potential_category

            confidence = 0.5
            if confidence_match:
                confidence = min(1.0, max(0.0, float(confidence_match.group(1))))

            return category, confidence

        except Exception as e:
            logger.warning(f"Error parsing categorization response: {e}")
            return "Other", 0.3

    def _generate_analysis(self, transactions: List[Transaction]) -> AnalysisResult:
        """Generate comprehensive analysis with ADHD-friendly insights."""
        if not transactions:
            return AnalysisResult(
                transactions=[],
                spending_breakdown={},
                insights=[],
                total_income=0,
                total_expenses=0,
                net_flow=0,
                analysis_period=(date.today(), date.today()),
                confidence_score=0
            )

        # Calculate spending breakdown
        spending_breakdown = {}
        total_income = 0
        total_expenses = 0

        for txn in transactions:
            if txn.transaction_type == 'credit' or txn.category == 'Income':
                total_income += txn.amount
            else:
                total_expenses += txn.amount
                spending_breakdown[txn.category] = spending_breakdown.get(txn.category, 0) + txn.amount

        net_flow = total_income - total_expenses

        # Determine analysis period
        dates = [txn.date for txn in transactions]
        analysis_period = (min(dates), max(dates))

        # Calculate overall confidence
        confidence_score = sum(txn.confidence for txn in transactions) / len(transactions) if transactions else 0

        # Generate ADHD-friendly insights
        insights = self._generate_insights(transactions, spending_breakdown, total_income, total_expenses)

        return AnalysisResult(
            transactions=transactions,
            spending_breakdown=spending_breakdown,
            insights=insights,
            total_income=total_income,
            total_expenses=total_expenses,
            net_flow=net_flow,
            analysis_period=analysis_period,
            confidence_score=confidence_score
        )

    def _generate_insights(self, transactions: List[Transaction],
                         spending_breakdown: Dict[str, float],
                         total_income: float, total_expenses: float) -> List[SpendingInsight]:
        """Generate ADHD-friendly insights and recommendations."""
        insights = []

        if not spending_breakdown:
            return insights

        try:
            # Create AI prompt for generating insights
            prompt = f"""
            You are a supportive financial advisor who specializes in helping people with ADHD manage their finances.
            Please analyze this spending data and provide 3-5 insights that are:
            - Encouraging and non-judgmental
            - Focused on patterns and positive behaviors
            - Simple and actionable
            - Highlight strengths before suggesting improvements

            Spending Summary:
            Total Income: ${total_income:.2f}
            Total Expenses: ${total_expenses:.2f}
            Net Flow: ${total_income - total_expenses:.2f}

            Spending by Category:
            {json.dumps(spending_breakdown, indent=2)}

            Transaction Count: {len(transactions)}

            For each insight, provide:
            1. A positive, encouraging title
            2. A supportive message explaining the pattern
            3. The relevant category
            4. The amount/percentage involved
            5. Type: 'positive' (celebrating good habits), 'neutral' (informational), or 'improvement' (gentle suggestions)
            6. An optional actionable recommendation

            Focus on celebrating what they're doing well first, then gently suggest improvements.
            Use warm, understanding language that acknowledges ADHD challenges.

            Respond with a JSON array of insights.
            """

            response = self.model.generate_content(prompt)

            if response.text:
                # Parse AI-generated insights
                json_text = response.text.strip()
                if json_text.startswith('```json'):
                    json_text = json_text[7:-3]
                elif json_text.startswith('```'):
                    json_text = json_text[3:-3]

                ai_insights = json.loads(json_text)

                # Convert to SpendingInsight objects
                for insight_data in ai_insights:
                    insight = SpendingInsight(
                        title=insight_data.get('title', 'Spending Insight'),
                        message=insight_data.get('message', ''),
                        category=insight_data.get('category', 'Other'),
                        amount=float(insight_data.get('amount', 0)),
                        percentage=float(insight_data.get('percentage', 0)),
                        insight_type=insight_data.get('type', 'neutral'),
                        recommendation=insight_data.get('recommendation')
                    )
                    insights.append(insight)

        except Exception as e:
            logger.warning(f"Error generating AI insights: {e}")
            # Fallback to basic insights
            insights = self._generate_basic_insights(spending_breakdown, total_income, total_expenses)

        return insights

    def _generate_basic_insights(self, spending_breakdown: Dict[str, float],
                               total_income: float, total_expenses: float) -> List[SpendingInsight]:
        """Generate basic insights as fallback when AI fails."""
        insights = []

        if spending_breakdown:
            # Find top spending category
            top_category = max(spending_breakdown.items(), key=lambda x: x[1])

            insights.append(SpendingInsight(
                title="Your Biggest Spending Area",
                message=f"Most of your spending went to {top_category[0]}, which is totally normal! "
                       f"This represents ${top_category[1]:.2f} of your expenses.",
                category=top_category[0],
                amount=top_category[1],
                percentage=(top_category[1] / total_expenses * 100) if total_expenses > 0 else 0,
                insight_type="neutral"
            ))

        # Net flow insigh
        if total_income > total_expenses:
            insights.append(SpendingInsight(
                title="Great Job Staying Within Budget! 🎉",
                message=f"You had ${total_income - total_expenses:.2f} left over this period. "
                       f"That's wonderful financial management!",
                category="Income",
                amount=total_income - total_expenses,
                percentage=((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0,
                insight_type="positive",
                recommendation="Consider setting aside some of this surplus for future goals!"
            ))

        return insights

    def _create_extraction_prompt(self) -> str:
        """Create prompt for extracting text from image statements."""
        return """
        Please carefully examine this bank statement image and extract all transaction information.
        Look for transaction dates, descriptions, and amounts (both debits and credits).

        For each transaction, identify:
        - Date
        - Description/merchant name
        - Amount (note if it's a debit/withdrawal or credit/deposit)
        - Account balance changes

        Present the information in a clear, structured format that can be easily processed.
        Include the account holder name, statement period, and any account summary information you can see.

        Be very careful with numbers - ensure all amounts are accurate including decimal places.
        """

    def get_category_breakdown_for_charts(self, analysis: AnalysisResult) -> Dict[str, Any]:
        """Format spending data for Chart.js visualization."""
        if not analysis.spending_breakdown:
            return {
                "labels": [],
                "data": [],
                "colors": []
            }

        # ADHD-friendly colors - soft, warm palette
        category_colors = {
            'Housing': '#4A90E2',      # Calm blue
            'Transportation': '#7ED321', # Fresh green
            'Food & Dining': '#F5A623',  # Warm orange
            'Entertainment': '#BD10E0',  # Gentle purple
            'Shopping': '#B8E986',       # Light green
            'Healthcare': '#50E3C2',     # Min
            'Bills & Utilities': '#9013FE', # Soft purple
            'Income': '#4BD863',         # Success green
            'Other': '#D0021B'           # Attention red
        }

        # Sort by amount for better visualization
        sorted_breakdown = sorted(analysis.spending_breakdown.items(), key=lambda x: x[1], reverse=True)

        return {
            "labels": [category for category, _ in sorted_breakdown],
            "data": [amount for _, amount in sorted_breakdown],
            "colors": [category_colors.get(category, '#95A5A6') for category, _ in sorted_breakdown],
            "total": sum(analysis.spending_breakdown.values())
        }

    def validate_analysis_result(self, analysis: AnalysisResult) -> Dict[str, Any]:
        """Validate analysis results and return validation info."""
        issues = []
        low_confidence_count = 0

        for txn in analysis.transactions:
            if txn.confidence < 0.5:
                low_confidence_count += 1

        if low_confidence_count > len(analysis.transactions) * 0.3:  # More than 30% low confidence
            issues.append({
                "type": "low_confidence",
                "message": f"{low_confidence_count} transactions have low confidence categorization",
                "count": low_confidence_count,
                "suggestion": "You might want to review and manually adjust some categories"
            })

        if analysis.confidence_score < 0.6:
            issues.append({
                "type": "overall_confidence",
                "message": "Overall analysis confidence is lower than usual",
                "confidence": analysis.confidence_score,
                "suggestion": "Consider uploading a clearer statement image or checking for manual adjustments needed"
            })

        return {
            "is_valid": len(issues) == 0,
            "confidence_score": analysis.confidence_score,
            "issues": issues,
            "manual_review_suggested": low_confidence_count > 0
        }