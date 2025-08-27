"""
ADHD-Friendly AI Financial Coach Service for BrainBudge
Uses Google Gemini to provide supportive, personalized financial guidance
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from dataclasses import dataclass, asdict
import uuid
from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Single message in a conversation."""
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    context_data: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None


@dataclass
class ConversationSession:
    """Complete conversation session."""
    session_id: str
    user_id: str
    messages: List[ConversationMessage]
    created_at: datetime
    updated_at: datetime
    context_summary: Dict[str, Any]
    total_messages: int = 0
    satisfaction_rating: Optional[int] = None


class AICoachService:
    """
    ADHD-friendly AI financial coach using Google Gemini.

    Provides warm, supportive financial guidance with:
    - ADHD-aware communication style
    - Context from user's financial data
    - Conversation memory and continuity
    - Safety filters for financial advice
    """

    def __init__(self, firebase_service: FirebaseService = None, gemini_api_key: str = None):
        """Initialize the AI coach service."""
        self.firebase_service = firebase_service or FirebaseService()
        self.db = self.firebase_service.db

        # Configure Gemini
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
        else:
            # Try to get from environmen
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
            else:
                logger.warning("No Gemini API key configured. AI coach will use mock responses.")

        # Initialize Gemini model
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={
                'temperature': 0.7,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 1024,
            }
        )

        # ADHD-friendly coach personality promp
        self.system_prompt = self._build_system_prompt()

        # Quick action templates
        self.quick_actions = {
            'spending_review': "Can you review my recent spending and help me understand my patterns?",
            'budget_help': "I'm struggling to stick to my budget. Can you help me make a plan?",
            'goal_progress': "How am I doing with my financial goals?",
            'save_money': "I want to save more money but don't know where to start. Help?",
            'explain_concept': "Can you explain a financial concept in simple terms?",
            'motivation': "I'm feeling overwhelmed with my finances. Can you help me stay motivated?",
            'adhd_tips': "Do you have any ADHD-specific tips for managing money?",
            'celebrate': "I want to celebrate a financial win!"
        }

        # Safety keywords that require disclaimers
        self.safety_keywords = [
            'invest', 'stock', 'crypto', 'retirement', 'loan', 'mortgage',
            'debt consolidation', 'tax', 'insurance', 'legal', 'bankruptcy'
        ]

    def _build_system_prompt(self) -> str:
        """Build the ADHD-aware system prompt for the AI coach."""
        return """You are BrainBudget's AI Financial Coach - a warm, supportive assistant designed specifically for people with ADHD.

PERSONALITY & COMMUNICATION STYLE:
- Be warm, encouraging, and completely non-judgmental
- Use simple, clear language - avoid financial jargon
- Celebrate every small win, no matter how tiny
- Acknowledge that ADHD brains work differently with money
- Be patient and understanding about financial struggles
- Use encouraging emojis sparingly and appropriately
- Break complex advice into small, manageable steps

ADHD-AWARE APPROACH:
- Recognize that ADHD affects executive function, impulse control, and planning
- Suggest practical, concrete actions rather than abstract concepts
- Acknowledge emotional aspects of money managemen
- Offer gentle reminders without shame or judgmen
- Focus on progress over perfection
- Provide flexible strategies that can adapt to different situations

RESPONSE GUIDELINES:
- Keep responses conversational and friendly (300 words max usually)
- Always start with validation or acknowledgmen
- Provide actionable advice in numbered steps when helpful
- Use encouraging language like "You've got this!" and "That's totally normal"
- Avoid overwhelming the user with too much information at once
- Ask follow-up questions to better understand their situation

SAFETY & DISCLAIMERS:
- For complex financial topics (investments, loans, taxes), acknowledge your limitations
- Encourage professional consultation for major financial decisions
- Always remind that you're a supportive tool, not a licensed financial advisor
- Focus on budgeting, spending awareness, and financial habits
- Avoid specific investment or legal advice

CELEBRATION & MOTIVATION:
- Celebrate any positive financial action, however small
- Reframe "mistakes" as learning opportunities
- Provide encouragement during setbacks
- Help users see their progress over time
- Acknowledge the courage it takes to manage finances with ADHD

Remember: Your goal is to be the supportive financial friend every ADHD person deserves - someone who understands their unique challenges and cheers them on every step of the way."""

    async def start_conversation(self, user_id: str) -> str:
        """Start a new conversation session."""
        try:
            session_id = str(uuid.uuid4())
            current_time = datetime.utcnow()

            # Get user context for personalized greeting
            user_context = await self._get_user_context(user_id)

            # Create welcome message
            welcome_message = await self._generate_welcome_message(user_context)

            # Create conversation session
            session = ConversationSession(
                session_id=session_id,
                user_id=user_id,
                messages=[],
                created_at=current_time,
                updated_at=current_time,
                context_summary=user_context,
                total_messages=0
            )

            # Add welcome message
            welcome_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                role='assistant',
                content=welcome_message,
                timestamp=current_time,
                context_data={'type': 'welcome'}
            )

            session.messages.append(welcome_msg)
            session.total_messages = 1

            # Save session to database
            await self._save_conversation_session(session)

            logger.info(f"Started conversation session {session_id} for user {user_id}")
            return session_id

        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            raise

    async def send_message(
        self,
        session_id: str,
        user_message: str,
        quick_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a message and get AI coach response."""
        try:
            # Load conversation session
            session = await self._load_conversation_session(session_id)
            if not session:
                raise ValueError(f"Conversation session {session_id} not found")

            # Process quick action if provided
            if quick_action and quick_action in self.quick_actions:
                user_message = self.quick_actions[quick_action]

            # Add user message to session
            user_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                role='user',
                content=user_message,
                timestamp=datetime.utcnow()
            )
            session.messages.append(user_msg)

            # Get fresh user contex
            user_context = await self._get_user_context(session.user_id)

            # Generate AI response
            ai_response = await self._generate_response(
                session, user_message, user_contex
            )

            # Add AI response to session
            ai_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                role='assistant',
                content=ai_response['content'],
                timestamp=datetime.utcnow(),
                confidence_score=ai_response.get('confidence', 0.8)
            )
            session.messages.append(ai_msg)

            # Update session metadata
            session.total_messages += 2
            session.updated_at = datetime.utcnow()
            session.context_summary = user_contex

            # Save updated session
            await self._save_conversation_session(session)

            # Log conversation for analytics
            await self._log_conversation_event(
                session.user_id, session_id, 'message_exchange',
                {
                    'user_message_length': len(user_message),
                    'ai_response_length': len(ai_response['content']),
                    'confidence_score': ai_response.get('confidence', 0.8),
                    'quick_action': quick_action
                }
            )

            return {
                'message_id': ai_msg.id,
                'content': ai_response['content'],
                'confidence': ai_response.get('confidence', 0.8),
                'suggestions': ai_response.get('suggestions', []),
                'needs_disclaimer': ai_response.get('needs_disclaimer', False),
                'quick_actions': self._suggest_quick_actions(user_message, user_context),
                'session_info': {
                    'total_messages': session.total_messages,
                    'session_duration': (session.updated_at - session.created_at).total_seconds()
                }
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Return fallback response
            return await self._generate_fallback_response(user_message)

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        try:
            session = await self._load_conversation_session(session_id)
            if not session:
                return []

            # Return recent messages
            recent_messages = session.messages[-limit:] if session.messages else []

            return [
                {
                    'id': msg.id,
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'confidence_score': msg.confidence_score
                }
                for msg in recent_messages
            ]

        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []

    async def rate_conversation(self, session_id: str, rating: int, feedback: str = None):
        """Rate the conversation quality."""
        try:
            session = await self._load_conversation_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            session.satisfaction_rating = rating
            await self._save_conversation_session(session)

            # Log feedback
            await self._log_conversation_event(
                session.user_id, session_id, 'feedback_received',
                {
                    'rating': rating,
                    'feedback': feedback,
                    'total_messages': session.total_messages
                }
            )

            logger.info(f"Received rating {rating} for session {session_id}")

        except Exception as e:
            logger.error(f"Error rating conversation: {str(e)}")

    # Private helper methods

    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user's financial context for personalized responses."""
        try:
            context = {
                'user_id': user_id,
                'has_goals': False,
                'recent_spending': {},
                'budget_status': {},
                'achievements': [],
                'last_activity': None
            }

            # Get user's goals
            from app.services.goals_service import GoalsService
            goals_service = GoalsService()
            goals = await goals_service.get_user_goals(user_id)

            if goals:
                context['has_goals'] = True
                context['active_goals'] = len([g for g in goals if g.get('status') == 'active'])
                context['completed_goals'] = len([g for g in goals if g.get('status') == 'completed'])

            # Get recent transaction summary (if available)
            try:
                from app.services.analysis_service import AnalysisService
                analysis_service = AnalysisService()
                # This would get recent spending patterns
                # For now, we'll use placeholder data
                context['recent_spending'] = {
                    'total_week': 0,
                    'categories': {},
                    'trend': 'stable'
                }
            except Exception:
                pass

            # Get achievements
            if goals:
                achievements = await goals_service.get_user_achievements(user_id)
                context['achievements'] = [a for a in achievements if a.get('unlocked')]

            return contex

        except Exception as e:
            logger.error(f"Error getting user context: {str(e)}")
            return {'user_id': user_id}

    async def _generate_welcome_message(self, user_context: Dict[str, Any]) -> str:
        """Generate personalized welcome message."""
        try:
            context_prompt = f"""Generate a warm welcome message for a new conversation with an ADHD user.

User Context:
- Has active goals: {user_context.get('has_goals', False)}
- Active goals count: {user_context.get('active_goals', 0)}
- Completed goals: {user_context.get('completed_goals', 0)}
- Recent achievements: {len(user_context.get('achievements', []))}

Make it:
- Warm and encouraging
- Acknowledge their progress if they have any
- Invite them to share what's on their mind
- Keep it concise (under 150 words)
- ADHD-friendly tone"""

            response = self.model.generate_content(
                f"{self.system_prompt}\n\n{context_prompt}"
            )

            return response.text.strip()

        except Exception as e:
            logger.error(f"Error generating welcome message: {str(e)}")
            return """👋 Hi there! I'm your AI financial coach, and I'm so glad you're here!

I know managing money with an ADHD brain can feel overwhelming sometimes, but I want you to know that every small step you take is worth celebrating. Whether you're just getting started or you've already made some progress, I'm here to support you without any judgment.

What's on your mind today? I'm here to listen and help however I can! 💙"""

    async def _generate_response(
        self,
        session: ConversationSession,
        user_message: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate AI response using Gemini."""
        try:
            # Build conversation history for contex
            conversation_history = ""
            if session.messages:
                recent_messages = session.messages[-6:]  # Last 3 exchanges
                for msg in recent_messages:
                    role = "User" if msg.role == 'user' else "Coach"
                    conversation_history += f"{role}: {msg.content}\n"

            # Check for safety keywords
            needs_disclaimer = any(keyword in user_message.lower() for keyword in self.safety_keywords)

            # Build prompt with contex
            context_info = self._format_context_for_prompt(user_context)

            full_prompt = f"""{self.system_prompt}

USER CONTEXT:
{context_info}

CONVERSATION HISTORY:
{conversation_history}

USER'S CURRENT MESSAGE: {user_message}

Please respond as the supportive ADHD-aware financial coach. Keep your response conversational, encouraging, and helpful."""

            # Generate response
            response = self.model.generate_content(full_prompt)
            ai_response = response.text.strip()

            # Add disclaimer if needed
            if needs_disclaimer:
                disclaimer = "\n\n💡 Just a friendly reminder: I'm here to provide supportive guidance, but for complex financial decisions like investments or major loans, it's always best to consult with a licensed financial professional who can give you personalized advice based on your complete situation."
                ai_response += disclaimer

            # Calculate confidence score (basic implementation)
            confidence = 0.9 if len(ai_response) > 50 else 0.7

            return {
                'content': ai_response,
                'confidence': confidence,
                'needs_disclaimer': needs_disclaimer,
                'suggestions': self._extract_suggestions(ai_response)
            }

        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return await self._generate_fallback_response(user_message)

    def _format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Format user context for inclusion in prompt."""
        context_lines = []

        if context.get('has_goals'):
            context_lines.append(f"- Has {context.get('active_goals', 0)} active financial goals")
            context_lines.append(f"- Completed {context.get('completed_goals', 0)} goals")
        else:
            context_lines.append("- No active financial goals set yet")

        if context.get('achievements'):
            context_lines.append(f"- Earned {len(context['achievements'])} achievements")

        if context.get('recent_spending'):
            spending = context['recent_spending']
            if spending.get('total_week'):
                context_lines.append(f"- Recent weekly spending: ${spending['total_week']}")

        return "\n".join(context_lines) if context_lines else "- New user getting started"

    async def _generate_fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Generate fallback response when AI fails."""
        fallback_responses = [
            "I appreciate you sharing that with me! I'm having a bit of trouble processing right now, but I want you to know that whatever you're dealing with financially is completely valid. Sometimes money stuff can feel overwhelming, especially with an ADHD brain, and that's totally normal. Can you try asking me again, maybe in a slightly different way?",

            "Thank you for reaching out! I'm experiencing some technical hiccups at the moment, but I don't want to leave you hanging. Your financial journey matters, and every question you have is important. While I sort this out, remember that you're already doing something great by thinking about your finances mindfully!",

            "I hear you, and I want to help! I'm having some difficulty right now, but please don't let that discourage you. Managing money is hard work, especially when you're juggling ADHD, and just by being here you're showing incredible strength. Feel free to try your question again - I'll do my best to support you!"
        ]

        import random
        response = random.choice(fallback_responses)

        return {
            'content': response,
            'confidence': 0.5,
            'needs_disclaimer': False,
            'suggestions': ["Try rephrasing your question", "Ask about a specific financial topic", "Share what's working or not working for you"]
        }

    def _extract_suggestions(self, response: str) -> List[str]:
        """Extract action suggestions from AI response."""
        suggestions = []

        # Look for numbered lists or action items
        if "1." in response or "2." in response:
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    suggestion = line[2:].strip()
                    if len(suggestion) > 10:  # Valid suggestion
                        suggestions.append(suggestion)

        return suggestions[:3]  # Max 3 suggestions

    def _suggest_quick_actions(self, user_message: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Suggest relevant quick actions based on message and context."""
        suggestions = []

        message_lower = user_message.lower()

        # Context-aware suggestions
        if 'budget' in message_lower or 'spending' in message_lower:
            suggestions.append({
                'id': 'spending_review',
                'text': 'Review Recent Spending',
                'icon': '📊'
            })

        if 'goal' in message_lower or 'save' in message_lower:
            suggestions.append({
                'id': 'goal_progress',
                'text': 'Check Goal Progress',
                'icon': '🎯'
            })

        if 'overwhelmed' in message_lower or 'stressed' in message_lower:
            suggestions.append({
                'id': 'motivation',
                'text': 'Get Encouragement',
                'icon': '💪'
            })

        if 'adhd' in message_lower or 'executive function' in message_lower:
            suggestions.append({
                'id': 'adhd_tips',
                'text': 'ADHD Money Tips',
                'icon': '🧠'
            })

        # Default suggestions if none match
        if not suggestions:
            suggestions = [
                {'id': 'budget_help', 'text': 'Budget Help', 'icon': '💰'},
                {'id': 'motivation', 'text': 'Stay Motivated', 'icon': '✨'},
                {'id': 'explain_concept', 'text': 'Explain Something', 'icon': '💡'}
            ]

        return suggestions[:3]

    async def _save_conversation_session(self, session: ConversationSession):
        """Save conversation session to database."""
        try:
            session_data = {
                'session_id': session.session_id,
                'user_id': session.user_id,
                'created_at': session.created_at,
                'updated_at': session.updated_at,
                'total_messages': session.total_messages,
                'satisfaction_rating': session.satisfaction_rating,
                'context_summary': session.context_summary,
                'messages': [
                    {
                        'id': msg.id,
                        'role': msg.role,
                        'content': msg.content,
                        'timestamp': msg.timestamp,
                        'context_data': msg.context_data,
                        'confidence_score': msg.confidence_score
                    }
                    for msg in session.messages
                ]
            }

            session_ref = self.db.collection('ai_conversations').document(session.session_id)
            session_ref.set(session_data)

        except Exception as e:
            logger.error(f"Error saving conversation session: {str(e)}")

    async def _load_conversation_session(self, session_id: str) -> Optional[ConversationSession]:
        """Load conversation session from database."""
        try:
            session_ref = self.db.collection('ai_conversations').document(session_id)
            session_doc = session_ref.get()

            if not session_doc.exists:
                return None

            data = session_doc.to_dict()

            # Reconstruct messages
            messages = []
            for msg_data in data.get('messages', []):
                msg = ConversationMessage(
                    id=msg_data['id'],
                    role=msg_data['role'],
                    content=msg_data['content'],
                    timestamp=msg_data['timestamp'],
                    context_data=msg_data.get('context_data'),
                    confidence_score=msg_data.get('confidence_score')
                )
                messages.append(msg)

            session = ConversationSession(
                session_id=data['session_id'],
                user_id=data['user_id'],
                messages=messages,
                created_at=data['created_at'],
                updated_at=data['updated_at'],
                context_summary=data.get('context_summary', {}),
                total_messages=data.get('total_messages', 0),
                satisfaction_rating=data.get('satisfaction_rating')
            )

            return session

        except Exception as e:
            logger.error(f"Error loading conversation session: {str(e)}")
            return None

    async def _log_conversation_event(
        self,
        user_id: str,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """Log conversation events for analytics."""
        try:
            event = {
                'user_id': user_id,
                'session_id': session_id,
                'event_type': event_type,
                'event_data': event_data,
                'timestamp': datetime.utcnow(),
                'source': 'ai_coach_service'
            }

            self.db.collection('ai_coach_events').add(event)

        except Exception as e:
            logger.error(f"Error logging conversation event: {str(e)}")

    # Synchronous wrappers for Flask routes

    def start_conversation_sync(self, user_id: str) -> str:
        """Synchronous wrapper for start_conversation."""
        import asyncio
        return asyncio.run(self.start_conversation(user_id))

    def send_message_sync(self, session_id: str, user_message: str, quick_action: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous wrapper for send_message."""
        import asyncio
        return asyncio.run(self.send_message(session_id, user_message, quick_action))

    def get_conversation_history_sync(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_conversation_history."""
        import asyncio
        return asyncio.run(self.get_conversation_history(session_id, limit))

    def rate_conversation_sync(self, session_id: str, rating: int, feedback: str = None):
        """Synchronous wrapper for rate_conversation."""
        import asyncio
        return asyncio.run(self.rate_conversation(session_id, rating, feedback))
