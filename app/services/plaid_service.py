"""
Plaid API service for BrainBudget.
Handles real-time banking data integration with ADHD-friendly error handling.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

# Plaid imports with graceful fallback
try:
    from plaid.api import plaid_api
    from plaid.model.transactions_get_request import TransactionsGetRequest
    from plaid.model.accounts_get_request import AccountsGetRequest
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.transactions_sync_request import TransactionsSyncRequest
    from plaid.model.item_remove_request import ItemRemoveRequest
    from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
    from plaid.configuration import Configuration
    from plaid.api_client import ApiClient
    from plaid.model.country_code import CountryCode
    from plaid.model.products import Products
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid import Environment
    PLAID_AVAILABLE = True
except ImportError:
    PLAID_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Plaid SDK not installed. Real-time banking features will use mock data.")

logger = logging.getLogger(__name__)


class PlaidService:
    """Plaid API service for banking data integration."""
    
    def __init__(self, client_id: str, secret: str, environment: str = 'sandbox'):
        """
        Initialize Plaid service.
        
        Args:
            client_id: Plaid client ID
            secret: Plaid secret key
            environment: Plaid environment (sandbox, development, production)
        """
        self.client_id = client_id
        self.secret = secret
        self.environment = environment
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Plaid API client."""
        try:
            if not PLAID_AVAILABLE:
                logger.warning("Plaid SDK not available, using mock mode")
                self.client = None
                return
            
            # Map environment strings to Plaid Environment enums
            env_mapping = {
                'sandbox': Environment.sandbox,
                'development': Environment.development,
                'production': Environment.production
            }
            
            host = env_mapping.get(self.environment.lower(), Environment.sandbox)
            
            configuration = Configuration(
                host=host,
                api_key={
                    'clientId': self.client_id,
                    'secret': self.secret,
                    'version': '2020-09-14'
                }
            )
            api_client = ApiClient(configuration)
            self.client = plaid_api.PlaidApi(api_client)
            
            logger.info(f"Plaid service initialized for {self.environment} environment")
            
        except Exception as e:
            logger.error(f"Failed to initialize Plaid client: {e}")
            if self.environment == 'production':
                raise
            else:
                # In development, continue with mock mode
                logger.warning("Falling back to mock mode for development")
                self.client = None
    
    def create_link_token(self, user_id: str, user_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Create a link token for Plaid Link initialization.
        
        Args:
            user_id: Unique user identifier
            user_name: User's name (optional)
            
        Returns:
            Link token data if successful, None otherwise
        """
        try:
            if not self.client or not PLAID_AVAILABLE:
                # Mock implementation for development/testing
                logger.info(f"Creating mock link token for user: {user_id}")
                return {
                    'link_token': 'link-sandbox-mock-token-' + user_id[:8],
                    'expiration': (datetime.utcnow() + timedelta(hours=4)).isoformat(),
                    'request_id': f'mock-request-{user_id}'
                }
            
            # Real Plaid implementation
            request = LinkTokenCreateRequest(
                products=[Products('transactions')],
                client_name="BrainBudget - ADHD-Friendly Finance",
                country_codes=[CountryCode('US')],
                language='en',
                user=LinkTokenCreateRequestUser(
                    client_user_id=user_id
                )
            )
            
            response = self.client.link_token_create(request)
            result = response['link_token']
            
            logger.info(f"Link token created successfully for user: {user_id}")
            return {
                'link_token': result,
                'expiration': response['expiration'],
                'request_id': response['request_id']
            }
            
        except Exception as e:
            logger.error(f"Failed to create link token for user {user_id}: {e}")
            return None
    
    def exchange_public_token(self, public_token: str) -> Optional[Dict[str, str]]:
        """
        Exchange public token for access token.
        
        Args:
            public_token: Public token from Plaid Link
            
        Returns:
            Dict with access_token and item_id if successful, None otherwise
        """
        try:
            if not self.client or not PLAID_AVAILABLE:
                # Mock implementation for development/testing
                logger.info("Exchanging mock public token for access token")
                return {
                    'access_token': f"access-sandbox-mock-{public_token[-8:]}",
                    'item_id': f"item-mock-{public_token[-8:]}"
                }
            
            # Real Plaid implementation
            request = ItemPublicTokenExchangeRequest(
                public_token=public_token
            )
            
            response = self.client.item_public_token_exchange(request)
            
            logger.info("Public token exchanged successfully")
            return {
                'access_token': response['access_token'],
                'item_id': response['item_id']
            }
            
        except Exception as e:
            logger.error(f"Failed to exchange public token: {e}")
            return None
    
    def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Get user's bank accounts.
        
        Args:
            access_token: Plaid access token
            
        Returns:
            List of account dictionaries
        """
        try:
            if not self.client or not PLAID_AVAILABLE:
                # Mock implementation for development/testing
                logger.info("Fetching mock user accounts")
                return [
                    {
                        'account_id': 'mock_checking_001',
                        'name': 'Main Checking',
                        'official_name': 'BrainBudget Checking Account',
                        'type': 'depository',
                        'subtype': 'checking',
                        'balance': {
                            'available': 1234.56,
                            'current': 1234.56,
                            'currency': 'USD'
                        },
                        'mask': '0000'
                    },
                    {
                        'account_id': 'mock_credit_001',
                        'name': 'Credit Card',
                        'official_name': 'BrainBudget Rewards Card',
                        'type': 'credit',
                        'subtype': 'credit card',
                        'balance': {
                            'available': 2500.00,
                            'current': -150.25,
                            'currency': 'USD'
                        },
                        'mask': '1234'
                    }
                ]
            
            # Real Plaid implementation
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            
            accounts = []
            for account in response['accounts']:
                account_dict = {
                    'account_id': account['account_id'],
                    'name': account['name'],
                    'official_name': account.get('official_name'),
                    'type': account['type'],
                    'subtype': account['subtype'],
                    'mask': account.get('mask'),
                    'balance': {
                        'available': account['balances']['available'],
                        'current': account['balances']['current'],
                        'currency': account['balances']['iso_currency_code'] or 'USD'
                    }
                }
                accounts.append(account_dict)
            
            logger.info(f"Retrieved {len(accounts)} accounts successfully")
            return accounts
            
        except Exception as e:
            logger.error(f"Failed to get accounts: {e}")
            return []
    
    def get_transactions(self, access_token: str, start_date: datetime = None, 
                        end_date: datetime = None, account_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get user's transactions.
        
        Args:
            access_token: Plaid access token
            start_date: Start date for transactions (default: 30 days ago)
            end_date: End date for transactions (default: today)
            account_ids: List of account IDs to filter (optional)
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # Set default date range if not provided
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            if not self.client or not PLAID_AVAILABLE:
                # Mock implementation for development/testing
                logger.info(f"Fetching mock transactions from {start_date.date()} to {end_date.date()}")
                return [
                    {
                        'transaction_id': 'mock_txn_001',
                        'account_id': 'mock_checking_001',
                        'amount': 4.50,
                        'date': (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d'),
                        'name': 'STARBUCKS COFFEE',
                        'merchant_name': 'Starbucks',
                        'category': ['Food and Drink', 'Restaurants', 'Coffee Shop'],
                        'category_id': '13005043',
                        'account_owner': None,
                        'pending': False,
                        'location': {
                            'address': '123 Main St',
                            'city': 'San Francisco',
                            'region': 'CA',
                            'postal_code': '94105',
                            'country': 'US'
                        }
                    },
                    {
                        'transaction_id': 'mock_txn_002',
                        'account_id': 'mock_checking_001',
                        'amount': 87.32,
                        'date': (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d'),
                        'name': 'WHOLE FOODS MARKET',
                        'merchant_name': 'Whole Foods Market',
                        'category': ['Shops', 'Supermarkets and Groceries'],
                        'category_id': '19047000',
                        'account_owner': None,
                        'pending': False,
                        'location': {
                            'address': '456 Market St',
                            'city': 'San Francisco', 
                            'region': 'CA',
                            'postal_code': '94105',
                            'country': 'US'
                        }
                    },
                    {
                        'transaction_id': 'mock_txn_003',
                        'account_id': 'mock_checking_001',
                        'amount': -2500.00,
                        'date': (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%d'),
                        'name': 'ACME CORP PAYROLL',
                        'merchant_name': 'Acme Corp',
                        'category': ['Deposit', 'Payroll'],
                        'category_id': '21009000',
                        'account_owner': None,
                        'pending': False,
                        'location': {}
                    }
                ]
            
            # Real Plaid implementation
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date.date(),
                end_date=end_date.date(),
                account_ids=account_ids
            )
            
            response = self.client.transactions_get(request)
            
            transactions = []
            for txn in response['transactions']:
                transaction_dict = {
                    'transaction_id': txn['transaction_id'],
                    'account_id': txn['account_id'],
                    'amount': float(txn['amount']),
                    'date': str(txn['date']),
                    'name': txn['name'],
                    'merchant_name': txn.get('merchant_name'),
                    'category': txn.get('category', []),
                    'category_id': txn.get('category_id'),
                    'account_owner': txn.get('account_owner'),
                    'pending': txn.get('pending', False),
                    'location': txn.get('location', {})
                }
                transactions.append(transaction_dict)
            
            logger.info(f"Retrieved {len(transactions)} transactions successfully")
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get transactions: {e}")
            return []
    
    def sync_transactions(self, access_token: str, cursor: str = None) -> Dict[str, Any]:
        """
        Sync transactions using Plaid's sync endpoint for real-time updates.
        
        Args:
            access_token: Plaid access token
            cursor: Cursor for incremental sync (optional)
            
        Returns:
            Sync response with added, modified, and removed transactions
        """
        try:
            if not self.client or not PLAID_AVAILABLE:
                # Mock implementation for development/testing
                logger.info("Mock syncing transactions")
                return {
                    'added': [],
                    'modified': [],
                    'removed': [],
                    'next_cursor': f'mock_cursor_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
                    'has_more': False
                }
            
            # Real Plaid implementation using transactions/sync endpoint
            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor
            )
            
            response = self.client.transactions_sync(request)
            
            # Transform transactions to match our internal format
            added = []
            for txn in response.get('added', []):
                added.append({
                    'transaction_id': txn['transaction_id'],
                    'account_id': txn['account_id'],
                    'amount': float(txn['amount']),
                    'date': str(txn['date']),
                    'name': txn['name'],
                    'merchant_name': txn.get('merchant_name'),
                    'category': txn.get('category', []),
                    'pending': txn.get('pending', False)
                })
            
            modified = []
            for txn in response.get('modified', []):
                modified.append({
                    'transaction_id': txn['transaction_id'],
                    'account_id': txn['account_id'],
                    'amount': float(txn['amount']),
                    'date': str(txn['date']),
                    'name': txn['name'],
                    'merchant_name': txn.get('merchant_name'),
                    'category': txn.get('category', []),
                    'pending': txn.get('pending', False)
                })
            
            removed = [txn['transaction_id'] for txn in response.get('removed', [])]
            
            logger.info(f"Sync completed: {len(added)} added, {len(modified)} modified, {len(removed)} removed")
            
            return {
                'added': added,
                'modified': modified,
                'removed': removed,
                'next_cursor': response.get('next_cursor'),
                'has_more': response.get('has_more', False)
            }
            
        except Exception as e:
            logger.error(f"Failed to sync transactions: {e}")
            return {
                'added': [],
                'modified': [],
                'removed': [],
                'next_cursor': None,
                'has_more': False
            }
    
    def get_balance(self, access_token: str, account_id: str = None) -> Dict[str, Any]:
        """
        Get current account balance(s).
        
        Args:
            access_token: Plaid access token
            account_id: Specific account ID (optional)
            
        Returns:
            Balance information
        """
        try:
            # TODO: Implement in Phase 2
            # This will use the accounts endpoint to get real-time balances
            
            # Placeholder implementation
            logger.info(f"Fetching balance for account: {account_id or 'all accounts'}")
            
            if account_id:
                return {
                    'account_id': account_id,
                    'available': 1234.56,
                    'current': 1234.56,
                    'currency': 'USD',
                    'last_updated': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'accounts': [
                        {
                            'account_id': 'placeholder_checking_001',
                            'available': 1234.56,
                            'current': 1234.56,
                            'currency': 'USD'
                        }
                    ],
                    'last_updated': datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return {}
    
    def remove_item(self, access_token: str) -> bool:
        """
        Remove (disconnect) a bank connection.
        
        Args:
            access_token: Plaid access token
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.client or not PLAID_AVAILABLE:
                # Mock implementation for development/testing
                logger.info("Mock removing bank connection")
                return True
            
            # Real Plaid implementation
            request = ItemRemoveRequest(access_token=access_token)
            response = self.client.item_remove(request)
            
            logger.info("Bank connection removed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove item: {e}")
            return False
    
    def get_institution_info(self, institution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a financial institution.
        
        Args:
            institution_id: Plaid institution ID
            
        Returns:
            Institution information if found
        """
        try:
            # TODO: Implement in Phase 2
            # This will use Plaid's /institutions/get_by_id endpoint
            
            # Placeholder implementation
            logger.info(f"Fetching institution info for: {institution_id}")
            return {
                'institution_id': institution_id,
                'name': 'Sample Bank',
                'products': ['transactions', 'auth', 'identity'],
                'country_codes': ['US'],
                'logo': None,
                'primary_color': '#003366'
            }
            
        except Exception as e:
            logger.error(f"Failed to get institution info: {e}")
            return None
    
    def transform_to_internal_format(self, plaid_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform Plaid transactions to BrainBudget internal format.
        
        Args:
            plaid_transactions: List of transactions from Plaid
            
        Returns:
            List of transactions in internal format
        """
        internal_transactions = []
        
        for txn in plaid_transactions:
            # Map Plaid categories to BrainBudget categories
            category_mapping = {
                'Food and Drink': 'Food & Dining',
                'Shops': 'Shopping', 
                'Recreation': 'Entertainment',
                'Transportation': 'Transportation',
                'Healthcare': 'Healthcare',
                'Transfer': 'Transfer',
                'Deposit': 'Income',
                'Payment': 'Bills & Utilities'
            }
            
            plaid_category = txn.get('category', [])
            primary_category = plaid_category[0] if plaid_category else 'Other'
            internal_category = category_mapping.get(primary_category, 'Other')
            
            internal_txn = {
                'id': txn['transaction_id'],
                'date': txn['date'],
                'description': txn['name'],
                'amount': abs(float(txn['amount'])),
                'type': 'debit' if float(txn['amount']) > 0 else 'credit',
                'category': internal_category,
                'subcategory': plaid_category[1] if len(plaid_category) > 1 else internal_category,
                'merchant': txn.get('merchant_name', txn['name']),
                'account_id': txn['account_id'],
                'pending': txn.get('pending', False),
                'confidence': 0.95,  # High confidence for Plaid data
                'source': 'plaid',
                'location': txn.get('location', {}),
                'raw_data': txn  # Keep original for debugging
            }
            
            internal_transactions.append(internal_txn)
        
        return internal_transactions
    
    def detect_duplicates(self, new_transactions: List[Dict[str, Any]], 
                         existing_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect and filter out duplicate transactions.
        
        Args:
            new_transactions: New transactions to check
            existing_transactions: Previously stored transactions
            
        Returns:
            List of unique transactions
        """
        # Create a set of existing transaction signatures
        existing_signatures = set()
        for txn in existing_transactions:
            signature = f"{txn['date']}_{txn['amount']}_{txn['description'][:20]}"
            existing_signatures.add(signature)
        
        unique_transactions = []
        for txn in new_transactions:
            signature = f"{txn['date']}_{txn['amount']}_{txn['description'][:20]}"
            if signature not in existing_signatures:
                unique_transactions.append(txn)
                existing_signatures.add(signature)  # Prevent duplicates within the new set too
        
        logger.info(f"Filtered {len(new_transactions) - len(unique_transactions)} duplicates")
        return unique_transactions
    
    def get_friendly_error_message(self, error: Exception) -> str:
        """
        Convert Plaid errors to ADHD-friendly messages.
        
        Args:
            error: Exception from Plaid API
            
        Returns:
            User-friendly error message
        """
        error_str = str(error).lower()
        
        friendly_messages = {
            'item_login_required': "Your bank needs you to log in again. No worries, just reconnect! 🔑",
            'invalid_credentials': "Your login info doesn't match. Let's try connecting again! 🤔", 
            'invalid_mfa': "The verification code didn't work. Please try again! 🔢",
            'item_locked': "Your bank account is temporarily locked. Contact your bank to unlock it! 🔒",
            'user_setup_required': "Your bank needs some additional setup. Check your bank's website! ⚙️",
            'insufficient_credentials': "We need a bit more info from your bank. Let's try reconnecting! 📋",
            'invalid_updated_username': "Your username changed at your bank. Let's update it! ✏️",
            'invalid_updated_password': "Your password changed at your bank. Let's update it! 🔐",
            'item_not_supported': "This bank isn't supported yet, but you can still upload statements! 📄",
            'no_accounts': "No accounts found at this bank. Try a different bank! 🏦",
            'item_no_error': "Everything looks good! 👍",
            'rate_limit': "We're getting data a bit fast. Let's wait a moment and try again! ⏰",
            'api_error': "There's a temporary issue with our banking partner. Try again soon! 🔄",
            'internal_server_error': "Something went wrong on our end. We're fixing it! 🛠️"
        }
        
        for key, message in friendly_messages.items():
            if key in error_str:
                return message
        
        # Default friendly message
        return "Something didn't work as expected with your bank connection. No worries, you can try again or upload a statement instead! 💪"


class PlaidError(Exception):
    """Custom exception for Plaid-specific errors."""
    
    def __init__(self, message: str, error_code: str = None, display_message: str = None):
        super().__init__(message)
        self.error_code = error_code
        self.display_message = display_message


class PlaidConnectionError(PlaidError):
    """Exception for Plaid connection issues."""
    pass


class PlaidAuthenticationError(PlaidError):
    """Exception for Plaid authentication issues."""
    pass


class PlaidRateLimitError(PlaidError):
    """Exception for Plaid rate limiting."""
    pass