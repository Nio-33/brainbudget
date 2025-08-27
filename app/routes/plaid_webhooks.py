"""
Plaid webhook handlers for BrainBudget.
Handles real-time notifications from Plaid for transaction updates, errors, and account changes.
"""
import logging
import hmac
import hashlib
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from app.services.firebase_service import FirebaseService
from app.services.plaid_service import PlaidService

logger = logging.getLogger(__name__)

plaid_webhooks_bp = Blueprint('plaid_webhooks', __name__)


def verify_webhook_signature(body: bytes, signature: str, webhook_secret: str) -> bool:
    """
    Verify Plaid webhook signature for security.

    Args:
        body: Raw request body
        signature: Signature from Plaid-Verification header
        webhook_secret: Your webhook secret from Plaid dashboard

    Returns:
        True if signature is valid
    """
    try:
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


@plaid_webhooks_bp.route('/transactions', methods=['POST'])
def handle_transactions_webhook():
    """
    Handle transaction webhook notifications from Plaid.

    Webhook types:
    - INITIAL_UPDATE: New historical transactions available
    - HISTORICAL_UPDATE: Historical transaction updates
    - DEFAULT_UPDATE: New transactions available
    - TRANSACTIONS_REMOVED: Transactions were removed
    """
    try:
        # Verify webhook signature (in production)
        if not current_app.debug:
            webhook_secret = current_app.config.get('PLAID_WEBHOOK_SECRET')
            if webhook_secret:
                signature = request.headers.get('Plaid-Verification')
                if not signature or not verify_webhook_signature(request.data, signature, webhook_secret):
                    logger.warning("Invalid webhook signature")
                    return jsonify({'error': 'Invalid signature'}), 401

        data = request.get_json()
        webhook_type = data.get('webhook_type')
        webhook_code = data.get('webhook_code')
        item_id = data.get('item_id')

        logger.info(f"Received Plaid webhook: {webhook_type}.{webhook_code} for item {item_id}")

        # Find the connection for this item
        firebase_service: FirebaseService = current_app.firebase
        connections_ref = firebase_service.db.collection('plaid_connections')
        connection_query = connections_ref.where('item_id', '==', item_id).where('status', '==', 'active').limit(1)
        connection_docs = list(connection_query.stream())

        if not connection_docs:
            logger.warning(f"No active connection found for item_id: {item_id}")
            return jsonify({'status': 'ignored', 'reason': 'connection_not_found'}), 200

        connection_doc = connection_docs[0]
        connection_data = connection_doc.to_dict()
        user_id = connection_data['user_id']
        access_token = connection_data['access_token']

        plaid_service = PlaidService(
            client_id=current_app.config['PLAID_CLIENT_ID'],
            secret=current_app.config['PLAID_SECRET'],
            environment=current_app.config['PLAID_ENV']
        )

        if webhook_code in ['INITIAL_UPDATE', 'HISTORICAL_UPDATE', 'DEFAULT_UPDATE']:
            # Sync new/updated transactions
            try:
                cursor = connection_data.get('sync_cursor')
                sync_result = plaid_service.sync_transactions(access_token, cursor)

                # Process added transactions
                new_transactions = 0
                if sync_result['added']:
                    internal_transactions = plaid_service.transform_to_internal_format(sync_result['added'])

                    for txn in internal_transactions:
                        txn_data = {
                            'user_id': user_id,
                            'connection_id': connection_doc.id,
                            'transaction': txn,
                            'created_at': datetime.utcnow(),
                            'source': f'plaid_webhook_{webhook_code.lower()}'
                        }
                        firebase_service.db.collection('plaid_transactions').add(txn_data)

                    new_transactions = len(internal_transactions)

                # Process modified transactions
                modified_transactions = 0
                if sync_result['modified']:
                    # For modified transactions, we would typically update existing records
                    # For now, we'll log and handle in future iterations
                    modified_transactions = len(sync_result['modified'])
                    logger.info(f"Received {modified_transactions} modified transactions (handling TBD)")

                # Process removed transactions
                removed_transactions = 0
                if sync_result['removed']:
                    removed_transactions = len(sync_result['removed'])
                    logger.info(f"Received {removed_transactions} removed transactions (handling TBD)")

                # Update connection with new cursor and last sync time
                connection_doc.reference.update({
                    'last_sync': datetime.utcnow(),
                    'sync_cursor': sync_result['next_cursor'],
                    'last_webhook': {
                        'type': webhook_type,
                        'code': webhook_code,
                        'processed_at': datetime.utcnow(),
                        'new_transactions': new_transactions,
                        'modified_transactions': modified_transactions,
                        'removed_transactions': removed_transactions
                    }
                })

                logger.info(f"Webhook processed: {new_transactions} new, {modified_transactions} modified, {removed_transactions} removed")

                return jsonify({
                    'status': 'success',
                    'processed': {
                        'new_transactions': new_transactions,
                        'modified_transactions': modified_transactions,
                        'removed_transactions': removed_transactions
                    }
                }), 200

            except Exception as e:
                logger.error(f"Error processing transaction webhook: {e}")
                # Update connection with error status but don't fail the webhook
                connection_doc.reference.update({
                    'last_webhook_error': {
                        'error': str(e),
                        'webhook_type': webhook_type,
                        'webhook_code': webhook_code,
                        'occurred_at': datetime.utcnow()
                    }
                })
                return jsonify({'status': 'error', 'message': str(e)}), 500

        elif webhook_code == 'TRANSACTIONS_REMOVED':
            # Handle removed transactions
            removed_transaction_ids = data.get('removed_transactions', [])
            logger.info(f"Processing {len(removed_transaction_ids)} removed transactions")

            # Mark transactions as removed (soft delete)
            for txn_id in removed_transaction_ids:
                txn_query = firebase_service.db.collection('plaid_transactions').where(
                    'transaction.id', '==', txn_id
                ).limit(1)
                txn_docs = list(txn_query.stream())

                for txn_doc in txn_docs:
                    txn_doc.reference.update({
                        'removed_at': datetime.utcnow(),
                        'status': 'removed'
                    })

            return jsonify({'status': 'success', 'removed': len(removed_transaction_ids)}), 200

        else:
            logger.info(f"Unhandled webhook code: {webhook_code}")
            return jsonify({'status': 'ignored', 'reason': 'unhandled_webhook_code'}), 200

    except Exception as e:
        logger.error(f"Error handling transaction webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@plaid_webhooks_bp.route('/item', methods=['POST'])
def handle_item_webhook():
    """
    Handle item webhook notifications from Plaid.

    Webhook types:
    - ERROR: Item errors (login required, etc.)
    - PENDING_EXPIRATION: Credentials will expire soon
    - USER_PERMISSION_REVOKED: User revoked access
    """
    try:
        # Verify webhook signature (in production)
        if not current_app.debug:
            webhook_secret = current_app.config.get('PLAID_WEBHOOK_SECRET')
            if webhook_secret:
                signature = request.headers.get('Plaid-Verification')
                if not signature or not verify_webhook_signature(request.data, signature, webhook_secret):
                    logger.warning("Invalid webhook signature")
                    return jsonify({'error': 'Invalid signature'}), 401

        data = request.get_json()
        webhook_type = data.get('webhook_type')
        webhook_code = data.get('webhook_code')
        item_id = data.get('item_id')
        error = data.get('error')

        logger.info(f"Received Plaid item webhook: {webhook_type}.{webhook_code} for item {item_id}")

        # Find the connection for this item
        firebase_service: FirebaseService = current_app.firebase
        connections_ref = firebase_service.db.collection('plaid_connections')
        connection_query = connections_ref.where('item_id', '==', item_id).limit(1)
        connection_docs = list(connection_query.stream())

        if not connection_docs:
            logger.warning(f"No connection found for item_id: {item_id}")
            return jsonify({'status': 'ignored', 'reason': 'connection_not_found'}), 200

        connection_doc = connection_docs[0]
        user_id = connection_doc.to_dict()['user_id']

        if webhook_code == 'ERROR':
            # Handle item errors
            error_code = error.get('error_code') if error else 'UNKNOWN_ERROR'
            error_message = error.get('display_message', 'Unknown error occurred') if error else 'Unknown error'

            # Update connection status
            connection_doc.reference.update({
                'status': 'error',
                'error': {
                    'code': error_code,
                    'message': error_message,
                    'occurred_at': datetime.utcnow(),
                    'webhook_type': webhook_type,
                    'webhook_code': webhook_code
                },
                'last_webhook': {
                    'type': webhook_type,
                    'code': webhook_code,
                    'processed_at': datetime.utcnow()
                }
            })

            # Log for monitoring
            logger.warning(f"Item error for user {user_id}: {error_code} - {error_message}")

            # TODO: In the future, could send user notification about the error
            # and provide friendly instructions for reconnecting

            return jsonify({'status': 'success', 'action': 'error_recorded'}), 200

        elif webhook_code == 'PENDING_EXPIRATION':
            # Credentials will expire soon - notify user to update
            connection_doc.reference.update({
                'status': 'pending_expiration',
                'expiration_warning': {
                    'received_at': datetime.utcnow(),
                    'webhook_type': webhook_type,
                    'webhook_code': webhook_code
                },
                'last_webhook': {
                    'type': webhook_type,
                    'code': webhook_code,
                    'processed_at': datetime.utcnow()
                }
            })

            logger.info(f"Credentials expiring soon for user {user_id}")
            return jsonify({'status': 'success', 'action': 'expiration_warning_recorded'}), 200

        elif webhook_code == 'USER_PERMISSION_REVOKED':
            # User revoked access at their bank
            connection_doc.reference.update({
                'status': 'revoked',
                'revoked_at': datetime.utcnow(),
                'last_webhook': {
                    'type': webhook_type,
                    'code': webhook_code,
                    'processed_at': datetime.utcnow()
                }
            })

            logger.info(f"User {user_id} revoked bank access")
            return jsonify({'status': 'success', 'action': 'access_revoked'}), 200

        else:
            logger.info(f"Unhandled item webhook code: {webhook_code}")
            return jsonify({'status': 'ignored', 'reason': 'unhandled_webhook_code'}), 200

    except Exception as e:
        logger.error(f"Error handling item webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@plaid_webhooks_bp.route('/holdings', methods=['POST'])
def handle_holdings_webhook():
    """
    Handle holdings/investments webhook notifications from Plaid.
    (For future investment account support)
    """
    try:
        data = request.get_json()
        webhook_type = data.get('webhook_type')
        webhook_code = data.get('webhook_code')
        item_id = data.get('item_id')

        logger.info(f"Received Plaid holdings webhook: {webhook_type}.{webhook_code} for item {item_id}")

        # For now, just log and acknowledge
        # Investment account support would be implemented here

        return jsonify({
            'status': 'acknowledged',
            'message': 'Holdings webhooks not yet implemented'
        }), 200

    except Exception as e:
        logger.error(f"Error handling holdings webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@plaid_webhooks_bp.route('/health', methods=['GET'])
def webhook_health():
    """Health check endpoint for webhook service."""
    return jsonify({
        'status': 'healthy',
        'service': 'plaid_webhooks',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
