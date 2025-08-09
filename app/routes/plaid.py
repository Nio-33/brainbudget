"""
Plaid API routes for BrainBudget.
Handles bank account connections, real-time data sync, and transaction management.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from app.routes.auth import require_auth
from app.services.firebase_service import FirebaseService
from app.services.plaid_service import PlaidService, PlaidError, PlaidConnectionError, PlaidAuthenticationError
from app.services.gemini_ai import GeminiAIService

logger = logging.getLogger(__name__)

plaid_bp = Blueprint('plaid', __name__)


@plaid_bp.route('/link/token/create', methods=['POST'])
@require_auth
def create_link_token():
    """
    Create a link token for Plaid Link initialization.
    
    Expected JSON:
    {
        "user_name": "Optional user name"
    }
    
    Returns:
        Link token for frontend Plaid Link initialization
    """
    try:
        uid = request.user['uid']
        data = request.get_json() or {}
        user_name = data.get('user_name')
        
        # Initialize Plaid service
        plaid_service = PlaidService(
            client_id=current_app.config['PLAID_CLIENT_ID'],
            secret=current_app.config['PLAID_SECRET'],
            environment=current_app.config['PLAID_ENV']
        )
        
        # Create link token
        link_token_data = plaid_service.create_link_token(uid, user_name)
        
        if not link_token_data:
            raise PlaidError("Failed to create link token")
        
        logger.info(f"Link token created for user {uid}")
        
        return jsonify({
            'success': True,
            'link_token': link_token_data['link_token'],
            'expiration': link_token_data['expiration'],
            'message': "Ready to connect your bank account! This is secure and encrypted. 🔒"
        })
        
    except PlaidError as e:
        logger.error(f"Plaid error creating link token: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't create bank connection token. Let's try again! 🔄",
            'debug_info': str(e) if current_app.debug else None
        }), 400
    except Exception as e:
        logger.error(f"Error creating link token: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong setting up bank connection. Our team is on it! 🛠️"
        }), 500


@plaid_bp.route('/link/token/exchange', methods=['POST'])
@require_auth  
def exchange_public_token():
    """
    Exchange public token from Plaid Link for access token.
    
    Expected JSON:
    {
        "public_token": "Public token from Plaid Link",
        "accounts": [
            {
                "id": "account_id",
                "name": "Account Name", 
                "type": "depository",
                "subtype": "checking"
            }
        ],
        "institution": {
            "name": "Bank Name",
            "institution_id": "ins_123"
        }
    }
    
    Returns:
        Success status and account information
    """
    try:
        uid = request.user['uid']
        data = request.get_json()
        
        if not data or 'public_token' not in data:
            raise BadRequest("Missing public token")
        
        public_token = data['public_token']
        account_metadata = data.get('accounts', [])
        institution_metadata = data.get('institution', {})
        
        # Initialize services
        plaid_service = PlaidService(
            client_id=current_app.config['PLAID_CLIENT_ID'],
            secret=current_app.config['PLAID_SECRET'],
            environment=current_app.config['PLAID_ENV']
        )
        firebase_service: FirebaseService = current_app.firebase
        
        # Exchange public token for access token
        token_data = plaid_service.exchange_public_token(public_token)
        
        if not token_data:
            raise PlaidConnectionError("Failed to exchange tokens")
        
        access_token = token_data['access_token']
        item_id = token_data['item_id']
        
        # Get real account information from Plaid
        accounts = plaid_service.get_accounts(access_token)
        
        if not accounts:
            raise PlaidConnectionError("No accounts found after connection")
        
        # Store connection information in Firebase
        connection_data = {
            'user_id': uid,
            'item_id': item_id,
            'access_token': access_token,  # In production, encrypt this!
            'institution': {
                'id': institution_metadata.get('institution_id'),
                'name': institution_metadata.get('name', 'Unknown Bank')
            },
            'accounts': accounts,
            'connected_at': datetime.utcnow(),
            'last_sync': None,
            'sync_cursor': None,
            'status': 'active'
        }
        
        # Save to Firebase
        doc_ref = firebase_service.db.collection('plaid_connections').document()
        doc_ref.set(connection_data)
        
        # Initial transaction sync
        try:
            transactions = plaid_service.get_transactions(
                access_token=access_token,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow()
            )
            
            # Transform and store transactions
            if transactions:
                internal_transactions = plaid_service.transform_to_internal_format(transactions)
                
                # Store transactions in Firebase
                for txn in internal_transactions:
                    txn_data = {
                        'user_id': uid,
                        'connection_id': doc_ref.id,
                        'transaction': txn,
                        'created_at': datetime.utcnow(),
                        'source': 'plaid_initial_sync'
                    }
                    firebase_service.db.collection('plaid_transactions').add(txn_data)
                
                logger.info(f"Initial sync: {len(internal_transactions)} transactions stored")
        except Exception as e:
            logger.warning(f"Initial transaction sync failed: {e}")
            # Don't fail the connection for sync issues
        
        logger.info(f"Plaid connection established for user {uid} with {len(accounts)} accounts")
        
        return jsonify({
            'success': True,
            'connection_id': doc_ref.id,
            'accounts': accounts,
            'institution': institution_metadata,
            'initial_transactions': len(transactions) if 'transactions' in locals() else 0,
            'message': f"Successfully connected to {institution_metadata.get('name', 'your bank')}! 🎉 We're now syncing your transactions."
        })
        
    except BadRequest as e:
        raise e
    except PlaidAuthenticationError as e:
        logger.error(f"Plaid authentication error: {e}")
        return jsonify({
            'success': False,
            'error': "Bank authentication failed. Please try connecting again! 🔑"
        }), 401
    except PlaidConnectionError as e:
        logger.error(f"Plaid connection error: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't complete bank connection. Let's try again! 🔄"
        }), 400
    except Exception as e:
        logger.error(f"Error exchanging public token: {e}")
        return jsonify({
            'success': False,
            'error': "Something went wrong connecting your bank. Our team is investigating! 🛠️"
        }), 500


@plaid_bp.route('/accounts', methods=['GET'])
@require_auth
def get_connected_accounts():
    """
    Get all connected bank accounts for the user.
    
    Returns:
        List of connected accounts with balances
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase
        
        # Get user's Plaid connections
        connections_ref = firebase_service.db.collection('plaid_connections')
        connections = connections_ref.where('user_id', '==', uid).where('status', '==', 'active').stream()
        
        all_accounts = []
        plaid_service = PlaidService(
            client_id=current_app.config['PLAID_CLIENT_ID'],
            secret=current_app.config['PLAID_SECRET'],
            environment=current_app.config['PLAID_ENV']
        )
        
        for connection_doc in connections:
            connection = connection_doc.to_dict()
            access_token = connection['access_token']
            
            try:
                # Get fresh account data with current balances
                accounts = plaid_service.get_accounts(access_token)
                
                for account in accounts:
                    account['connection_id'] = connection_doc.id
                    account['institution'] = connection['institution']
                    account['last_sync'] = connection.get('last_sync')
                
                all_accounts.extend(accounts)
                
            except Exception as e:
                logger.warning(f"Failed to get accounts for connection {connection_doc.id}: {e}")
                # Add stored account info as fallback
                stored_accounts = connection.get('accounts', [])
                for account in stored_accounts:
                    account['connection_id'] = connection_doc.id
                    account['institution'] = connection['institution']
                    account['status'] = 'error'
                all_accounts.extend(stored_accounts)
        
        logger.info(f"Retrieved {len(all_accounts)} accounts for user {uid}")
        
        return jsonify({
            'success': True,
            'accounts': all_accounts,
            'total_accounts': len(all_accounts),
            'message': f"Here are your {len(all_accounts)} connected accounts! 💳"
        })
        
    except Exception as e:
        logger.error(f"Error getting connected accounts: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your accounts right now. Your data is safe! 💾"
        }), 500


@plaid_bp.route('/transactions/sync', methods=['POST'])
@require_auth
def sync_transactions():
    """
    Manually trigger transaction sync for all connections.
    
    Optional JSON:
    {
        "connection_id": "Specific connection ID to sync"
    }
    
    Returns:
        Sync results
    """
    try:
        uid = request.user['uid']
        data = request.get_json() or {}
        specific_connection_id = data.get('connection_id')
        
        firebase_service: FirebaseService = current_app.firebase
        plaid_service = PlaidService(
            client_id=current_app.config['PLAID_CLIENT_ID'],
            secret=current_app.config['PLAID_SECRET'],
            environment=current_app.config['PLAID_ENV']
        )
        
        # Get connections to sync
        connections_ref = firebase_service.db.collection('plaid_connections')
        query = connections_ref.where('user_id', '==', uid).where('status', '==', 'active')
        
        if specific_connection_id:
            query = query.where(connections_ref.document_id, '==', specific_connection_id)
        
        connections = query.stream()
        
        total_added = 0
        total_modified = 0
        total_removed = 0
        synced_connections = 0
        
        for connection_doc in connections:
            connection = connection_doc.to_dict()
            access_token = connection['access_token']
            cursor = connection.get('sync_cursor')
            
            try:
                # Sync transactions
                sync_result = plaid_service.sync_transactions(access_token, cursor)
                
                # Process added transactions
                if sync_result['added']:
                    internal_transactions = plaid_service.transform_to_internal_format(sync_result['added'])
                    
                    for txn in internal_transactions:
                        txn_data = {
                            'user_id': uid,
                            'connection_id': connection_doc.id,
                            'transaction': txn,
                            'created_at': datetime.utcnow(),
                            'source': 'plaid_sync'
                        }
                        firebase_service.db.collection('plaid_transactions').add(txn_data)
                
                # Update connection with new cursor
                connection_doc.reference.update({
                    'last_sync': datetime.utcnow(),
                    'sync_cursor': sync_result['next_cursor']
                })
                
                total_added += len(sync_result['added'])
                total_modified += len(sync_result['modified'])
                total_removed += len(sync_result['removed'])
                synced_connections += 1
                
            except Exception as e:
                logger.error(f"Failed to sync connection {connection_doc.id}: {e}")
                # Continue with other connections
        
        logger.info(f"Sync completed for user {uid}: {total_added} added, {total_modified} modified, {total_removed} removed")
        
        return jsonify({
            'success': True,
            'sync_results': {
                'connections_synced': synced_connections,
                'transactions_added': total_added,
                'transactions_modified': total_modified,
                'transactions_removed': total_removed
            },
            'message': f"Sync complete! Found {total_added} new transactions across {synced_connections} accounts! 🔄"
        })
        
    except Exception as e:
        logger.error(f"Error syncing transactions: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't sync your transactions right now. We'll keep trying automatically! 🔄"
        }), 500


@plaid_bp.route('/connections/<connection_id>/disconnect', methods=['DELETE'])
@require_auth
def disconnect_bank_account(connection_id):
    """
    Disconnect a bank account connection.
    
    Args:
        connection_id: ID of connection to disconnect
        
    Returns:
        Success status
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase
        plaid_service = PlaidService(
            client_id=current_app.config['PLAID_CLIENT_ID'],
            secret=current_app.config['PLAID_SECRET'],
            environment=current_app.config['PLAID_ENV']
        )
        
        # Get connection
        connection_doc = firebase_service.db.collection('plaid_connections').document(connection_id)
        connection = connection_doc.get()
        
        if not connection.exists:
            return jsonify({
                'success': False,
                'error': "Connection not found"
            }), 404
        
        connection_data = connection.to_dict()
        
        # Verify ownership
        if connection_data['user_id'] != uid:
            return jsonify({
                'success': False,
                'error': "Not authorized"
            }), 403
        
        # Remove from Plaid
        access_token = connection_data['access_token']
        try:
            plaid_service.remove_item(access_token)
        except Exception as e:
            logger.warning(f"Failed to remove item from Plaid: {e}")
            # Continue anyway to clean up our data
        
        # Mark connection as disconnected
        connection_doc.update({
            'status': 'disconnected',
            'disconnected_at': datetime.utcnow()
        })
        
        institution_name = connection_data.get('institution', {}).get('name', 'Bank')
        
        logger.info(f"Disconnected bank connection {connection_id} for user {uid}")
        
        return jsonify({
            'success': True,
            'message': f"Successfully disconnected from {institution_name}. Your data is still safe with us! 👋"
        })
        
    except Exception as e:
        logger.error(f"Error disconnecting bank account: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't disconnect right now. Contact support if this continues! 📞"
        }), 500


@plaid_bp.route('/transactions', methods=['GET'])
@require_auth
def get_plaid_transactions():
    """
    Get transactions from Plaid connections.
    
    Query parameters:
    - connection_id: Specific connection ID (optional)
    - start_date: Start date (YYYY-MM-DD) (optional)
    - end_date: End date (YYYY-MM-DD) (optional)
    - limit: Number of transactions to return (default: 50)
    
    Returns:
        List of transactions
    """
    try:
        uid = request.user['uid']
        connection_id = request.args.get('connection_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 50))
        
        firebase_service: FirebaseService = current_app.firebase
        
        # Build query
        transactions_ref = firebase_service.db.collection('plaid_transactions')
        query = transactions_ref.where('user_id', '==', uid)
        
        if connection_id:
            query = query.where('connection_id', '==', connection_id)
        
        # Order by creation date (most recent first) and limit
        query = query.order_by('created_at', direction='DESCENDING').limit(limit)
        
        transactions_docs = query.stream()
        
        transactions = []
        for doc in transactions_docs:
            doc_data = doc.to_dict()
            transaction = doc_data['transaction']
            transaction['id'] = doc.id
            transaction['created_at'] = doc_data['created_at']
            transactions.append(transaction)
        
        # Filter by date if specified
        if start_date or end_date:
            filtered_transactions = []
            for txn in transactions:
                txn_date = datetime.strptime(txn['date'], '%Y-%m-%d').date()
                
                if start_date:
                    start = datetime.strptime(start_date, '%Y-%m-%d').date()
                    if txn_date < start:
                        continue
                
                if end_date:
                    end = datetime.strptime(end_date, '%Y-%m-%d').date()
                    if txn_date > end:
                        continue
                
                filtered_transactions.append(txn)
            
            transactions = filtered_transactions
        
        logger.info(f"Retrieved {len(transactions)} Plaid transactions for user {uid}")
        
        return jsonify({
            'success': True,
            'transactions': transactions,
            'total_count': len(transactions),
            'message': f"Here are your {len(transactions)} recent transactions! 💳"
        })
        
    except Exception as e:
        logger.error(f"Error getting Plaid transactions: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your transactions right now. Your data is safe! 💾"
        }), 500


@plaid_bp.route('/balances', methods=['GET'])
@require_auth
def get_account_balances():
    """
    Get current balances for all connected accounts.
    
    Returns:
        Current account balances
    """
    try:
        uid = request.user['uid']
        firebase_service: FirebaseService = current_app.firebase
        plaid_service = PlaidService(
            client_id=current_app.config['PLAID_CLIENT_ID'],
            secret=current_app.config['PLAID_SECRET'],
            environment=current_app.config['PLAID_ENV']
        )
        
        # Get active connections
        connections_ref = firebase_service.db.collection('plaid_connections')
        connections = connections_ref.where('user_id', '==', uid).where('status', '==', 'active').stream()
        
        all_balances = []
        total_available = 0
        total_current = 0
        
        for connection_doc in connections:
            connection = connection_doc.to_dict()
            access_token = connection['access_token']
            
            try:
                accounts = plaid_service.get_accounts(access_token)
                
                for account in accounts:
                    balance_info = {
                        'account_id': account['account_id'],
                        'account_name': account['name'],
                        'type': account['type'],
                        'subtype': account['subtype'],
                        'mask': account.get('mask'),
                        'balance': account['balance'],
                        'institution': connection['institution'],
                        'last_updated': datetime.utcnow().isoformat()
                    }
                    
                    all_balances.append(balance_info)
                    
                    # Add to totals (only for depository accounts)
                    if account['type'] == 'depository':
                        if account['balance']['available']:
                            total_available += account['balance']['available']
                        if account['balance']['current']:
                            total_current += account['balance']['current']
                
            except Exception as e:
                logger.warning(f"Failed to get balances for connection {connection_doc.id}: {e}")
        
        summary = {
            'total_accounts': len(all_balances),
            'total_available': round(total_available, 2),
            'total_current': round(total_current, 2),
            'last_updated': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Retrieved balances for {len(all_balances)} accounts for user {uid}")
        
        return jsonify({
            'success': True,
            'balances': all_balances,
            'summary': summary,
            'message': f"Here are your current balances across {len(all_balances)} accounts! 💰"
        })
        
    except Exception as e:
        logger.error(f"Error getting account balances: {e}")
        return jsonify({
            'success': False,
            'error': "Couldn't load your balances right now. Your accounts are still secure! 🔒"
        }), 500