"""
Community routes for BrainBudget web application.
Handles forum posts, discussions, content moderation, and community analytics.
"""
from flask import Blueprint, request, jsonify, session, render_template, current_app
from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)

# Create blueprint for community routes
community_bp = Blueprint('community', __name__)


def require_auth():
    """Simple authentication check - returns user_id if authenticated, None otherwise."""
    return session.get('user_id')


def is_content_appropriate(title, content):
    """
    Content moderation function to check if post content is appropriate.
    Returns (is_appropriate, reason) tuple.
    """
    # Combine title and content for analysis
    text = (title + ' ' + content).lower()
    
    # Banned words/phrases that indicate inappropriate content
    banned_words = [
        'spam', 'scam', 'bitcoin', 'crypto', 'investment opportunity',
        'get rich quick', 'pyramid scheme', 'mlm', 'multi-level marketing',
        'work from home', 'make money fast', 'guaranteed returns',
        'financial advisor', 'investment advice', 'buy this stock'
    ]
    
    # Check for banned content
    for word in banned_words:
        if word in text:
            return False, f"Content contains inappropriate term: '{word}'"
    
    # Check for excessive capitalization (spam indicator)
    if sum(1 for c in title if c.isupper()) > len(title) * 0.7 and len(title) > 10:
        return False, "Excessive capitalization detected"
    
    # Check for URLs (basic spam prevention)
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    if re.search(url_pattern, text):
        return False, "External URLs are not allowed in posts"
    
    # Check minimum content length
    if len(content.strip()) < 20:
        return False, "Post content is too short (minimum 20 characters)"
    
    return True, None


@community_bp.route('/api/community/posts', methods=['POST'])
def create_post():
    """Create a new community forum post."""
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get post data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        category = data.get('category', '').strip()
        
        if not all([title, content, category]):
            return jsonify({'error': 'Title, content, and category are required'}), 400
        
        # Content moderation
        is_appropriate, reason = is_content_appropriate(title, content)
        if not is_appropriate:
            return jsonify({'error': f'Content moderation failed: {reason}'}), 400
        
        # Validate category
        valid_categories = ['getting-started', 'adhd-tips', 'wins', 'support', 'feedback']
        if category not in valid_categories:
            return jsonify({'error': 'Invalid category'}), 400
        
        # Create post document
        post_data = {
            'user_id': user_id,
            'title': title,
            'content': content,
            'category': category,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'likes': 0,
            'replies': 0,
            'is_pinned': False,
            'is_locked': False,
            'moderation_status': 'approved',  # Auto-approve for now
            'user_display_name': f"User {user_id[-4:]}"  # Anonymous display
        }
        
        # Save to Firestore
        doc_ref = current_app.firebase.db.collection('community_posts').add(post_data)
        post_id = doc_ref[1].id
        
        # Update user's community stats
        user_stats_ref = current_app.firebase.db.collection('user_community_stats').document(user_id)
        user_stats = user_stats_ref.get()
        
        if user_stats.exists:
            stats_data = user_stats.to_dict()
            stats_data['posts_count'] = stats_data.get('posts_count', 0) + 1
            stats_data['last_post_at'] = datetime.now(timezone.utc).isoformat()
            user_stats_ref.update(stats_data)
        else:
            # Create new user stats
            stats_data = {
                'user_id': user_id,
                'posts_count': 1,
                'replies_count': 0,
                'likes_received': 0,
                'community_level': 'New Member',
                'joined_at': datetime.now(timezone.utc).isoformat(),
                'last_post_at': datetime.now(timezone.utc).isoformat()
            }
            user_stats_ref.set(stats_data)
        
        logger.info(f"New community post created: {post_id} by user {user_id}")
        
        return jsonify({
            'success': True,
            'post_id': post_id,
            'message': 'Post created successfully!'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating community post: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@community_bp.route('/api/community/posts', methods=['GET'])
def get_posts():
    """Get community forum posts with pagination and filtering."""
    try:
        # Get query parameters
        category = request.args.get('category')
        limit = min(int(request.args.get('limit', 20)), 100)  # Max 100 posts per request
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = current_app.firebase.db.collection('community_posts').order_by('created_at', direction='DESCENDING')
        
        if category:
            query = query.where('category', '==', category)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        posts = query.stream()
        
        posts_data = []
        for post in posts:
            post_data = post.to_dict()
            post_data['id'] = post.id
            
            # Convert timestamps to readable format
            if 'created_at' in post_data:
                created_at = datetime.fromisoformat(post_data['created_at'].replace('Z', '+00:00'))
                post_data['created_at_display'] = created_at.strftime('%Y-%m-%d %H:%M UTC')
            
            posts_data.append(post_data)
        
        return jsonify({
            'success': True,
            'posts': posts_data,
            'count': len(posts_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching community posts: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@community_bp.route('/api/community/posts/<post_id>/like', methods=['POST'])
def like_post(post_id):
    """Like or unlike a community post."""
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Check if post exists
        post_ref = current_app.firebase.db.collection('community_posts').document(post_id)
        post = post_ref.get()
        
        if not post.exists:
            return jsonify({'error': 'Post not found'}), 404
        
        # Check if user already liked this post
        like_ref = current_app.firebase.db.collection('community_likes').where('user_id', '==', user_id).where('post_id', '==', post_id)
        existing_like = list(like_ref.stream())
        
        if existing_like:
            # Unlike the post
            existing_like[0].reference.delete()
            
            # Decrease like count
            post_data = post.to_dict()
            post_ref.update({'likes': max(0, post_data.get('likes', 0) - 1)})
            
            return jsonify({
                'success': True,
                'liked': False,
                'message': 'Post unliked'
            }), 200
        else:
            # Like the post
            like_data = {
                'user_id': user_id,
                'post_id': post_id,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            current_app.firebase.db.collection('community_likes').add(like_data)
            
            # Increase like count
            post_data = post.to_dict()
            post_ref.update({'likes': post_data.get('likes', 0) + 1})
            
            return jsonify({
                'success': True,
                'liked': True,
                'message': 'Post liked'
            }), 200
        
    except Exception as e:
        logger.error(f"Error liking post {post_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@community_bp.route('/api/community/stats', methods=['GET'])
def get_community_stats():
    """Get overall community statistics."""
    try:
        # Get total members count
        users_count = len(list(current_app.firebase.db.collection('user_community_stats').stream()))
        
        # Get active discussions count (posts in last 7 days)
        seven_days_ago = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago_iso = seven_days_ago.isoformat()
        
        recent_posts = list(
            current_app.firebase.db.collection('community_posts')
            .where('created_at', '>=', seven_days_ago_iso)
            .stream()
        )
        
        # Get total tips shared (all posts)
        total_posts = len(list(current_app.firebase.db.collection('community_posts').stream()))
        
        # Calculate support rating (placeholder - in real app would be based on user feedback)
        support_rating = 95  # Static for now
        
        return jsonify({
            'success': True,
            'stats': {
                'members': users_count,
                'active_discussions': len(recent_posts),
                'tips_shared': total_posts,
                'support_rating': support_rating
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching community stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@community_bp.route('/api/community/user-progress', methods=['GET'])
def get_user_progress():
    """Get the current user's community progress and analytics."""
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get user's community stats
        user_stats_ref = current_app.firebase.db.collection('user_community_stats').document(user_id)
        user_stats = user_stats_ref.get()
        
        if not user_stats.exists:
            # Return default stats for new users
            return jsonify({
                'success': True,
                'progress': {
                    'posts_count': 0,
                    'replies_count': 0,
                    'likes_received': 0,
                    'community_level': 'New Member',
                    'next_milestone': 'Active Member at 10 posts',
                    'progress_percentage': 0
                }
            }), 200
        
        stats_data = user_stats.to_dict()
        
        # Calculate community level and progress
        posts_count = stats_data.get('posts_count', 0)
        replies_count = stats_data.get('replies_count', 0)
        total_activity = posts_count + replies_count
        
        # Determine community level
        if total_activity >= 50:
            level = 'Community Helper'
            next_milestone = 'Expert at 100 activities'
            progress = min(100, (total_activity / 100) * 100)
        elif total_activity >= 25:
            level = 'Active Member'
            next_milestone = 'Community Helper at 50 activities'
            progress = ((total_activity - 25) / 25) * 100
        elif total_activity >= 10:
            level = 'Rising Star'
            next_milestone = 'Active Member at 25 activities'
            progress = ((total_activity - 10) / 15) * 100
        else:
            level = 'New Member'
            next_milestone = 'Rising Star at 10 activities'
            progress = (total_activity / 10) * 100
        
        return jsonify({
            'success': True,
            'progress': {
                'posts_count': posts_count,
                'replies_count': replies_count,
                'likes_received': stats_data.get('likes_received', 0),
                'community_level': level,
                'next_milestone': next_milestone,
                'progress_percentage': round(progress, 1),
                'total_activity': total_activity
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching user community progress: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@community_bp.route('/api/community/report', methods=['POST'])
def report_content():
    """Report inappropriate community content."""
    try:
        # Check authentication
        user_id = require_auth()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get report data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        post_id = data.get('post_id')
        reason = data.get('reason', '').strip()
        
        if not post_id or not reason:
            return jsonify({'error': 'Post ID and reason are required'}), 400
        
        # Check if post exists
        post_ref = current_app.firebase.db.collection('community_posts').document(post_id)
        post = post_ref.get()
        
        if not post.exists:
            return jsonify({'error': 'Post not found'}), 404
        
        # Create report document
        report_data = {
            'reported_by': user_id,
            'post_id': post_id,
            'reason': reason,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        current_app.firebase.db.collection('content_reports').add(report_data)
        
        logger.info(f"Content report created for post {post_id} by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your report. Our moderation team will review it shortly.'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating content report: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Error handlers for community routes
@community_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return jsonify({'error': 'Bad request'}), 400


@community_bp.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors."""
    return jsonify({'error': 'Authentication required'}), 401


@community_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return jsonify({'error': 'Resource not found'}), 404


@community_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Community route internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500