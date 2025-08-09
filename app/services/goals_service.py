"""
ADHD-Friendly Goal Management Service for BrainBudget
Focuses on small steps, visual progress, and celebration over perfection
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid
from dataclasses import dataclass, asdict
from app.services.firebase_service import FirebaseService

logger = logging.getLogger(__name__)


class GoalType(Enum):
    """Types of financial goals supported by BrainBudget."""
    SPENDING_REDUCTION = "spending_reduction"
    SAVINGS_TARGET = "savings_target"
    DEBT_REDUCTION = "debt_reduction"
    EMERGENCY_FUND = "emergency_fund"
    CUSTOM = "custom"


class GoalStatus(Enum):
    """Goal status states."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_TRACK = "on_track"
    BEHIND = "behind"
    AHEAD = "ahead"


class DifficultyLevel(Enum):
    """ADHD-friendly difficulty levels."""
    GENTLE = "gentle"      # Very achievable, confidence building
    MODERATE = "moderate"  # Standard challenge level
    AMBITIOUS = "ambitious" # Stretch goals for motivated periods


@dataclass
class Milestone:
    """Individual milestone within a goal."""
    id: str
    title: str
    description: str
    target_value: float
    target_date: str
    completed: bool = False
    completed_date: Optional[str] = None
    celebration_sent: bool = False
    order: int = 0


@dataclass
class Achievement:
    """Achievement/badge for goal accomplishments."""
    id: str
    name: str
    description: str
    icon: str
    category: str
    unlocked_date: Optional[str] = None
    progress: float = 0.0


class GoalsService:
    """
    ADHD-friendly goal management service.
    
    Key ADHD-friendly features:
    - Small, achievable milestones
    - Flexible goal adjustment without shame
    - Visual progress tracking
    - Celebration of small wins
    - Focus on progress over perfection
    """
    
    def __init__(self, firebase_service: FirebaseService = None):
        """Initialize the goals service."""
        self.firebase_service = firebase_service or FirebaseService()
        self.db = self.firebase_service.db
        
        # ADHD-friendly goal templates
        self.goal_templates = {
            GoalType.SPENDING_REDUCTION: [
                {
                    "name": "Gentle Dining Budget",
                    "description": "Reduce dining out by small, manageable amounts",
                    "category": "dining",
                    "reduction_percentage": 15,
                    "duration_weeks": 8,
                    "difficulty": DifficultyLevel.GENTLE.value,
                    "milestones_count": 4,
                    "adhd_tips": "Start with just 1-2 meals per week. Every small step counts!"
                },
                {
                    "name": "Shopping Mindfulness",
                    "description": "Thoughtful reduction in impulse purchases",
                    "category": "shopping",
                    "reduction_percentage": 20,
                    "duration_weeks": 12,
                    "difficulty": DifficultyLevel.MODERATE.value,
                    "milestones_count": 6,
                    "adhd_tips": "Use the 24-hour rule: wait a day before non-essential purchases."
                }
            ],
            GoalType.SAVINGS_TARGET: [
                {
                    "name": "Vacation Fund",
                    "description": "Save for that trip you've been dreaming about",
                    "target_amount": 1000,
                    "duration_weeks": 26,
                    "difficulty": DifficultyLevel.MODERATE.value,
                    "milestones_count": 5,
                    "adhd_tips": "Set up automatic transfers so you don't have to remember!"
                },
                {
                    "name": "New Gadget Goal",
                    "description": "Save for that tech you want (the ADHD-friendly way)",
                    "target_amount": 500,
                    "duration_weeks": 12,
                    "difficulty": DifficultyLevel.GENTLE.value,
                    "milestones_count": 4,
                    "adhd_tips": "Break it into bite-sized weekly amounts. Visual progress helps!"
                }
            ],
            GoalType.EMERGENCY_FUND: [
                {
                    "name": "Starter Emergency Fund",
                    "description": "Build a small safety net (start with just $500!)",
                    "target_amount": 500,
                    "duration_weeks": 20,
                    "difficulty": DifficultyLevel.GENTLE.value,
                    "milestones_count": 5,
                    "adhd_tips": "Even $100 is a huge win! Start small and celebrate every milestone."
                },
                {
                    "name": "Full Emergency Fund",
                    "description": "Build 3-6 months of expenses (we'll break it down!)",
                    "target_amount": 5000,
                    "duration_weeks": 52,
                    "difficulty": DifficultyLevel.AMBITIOUS.value,
                    "milestones_count": 10,
                    "adhd_tips": "This is a marathon, not a sprint. Adjust timeline as needed!"
                }
            ],
            GoalType.DEBT_REDUCTION: [
                {
                    "name": "Credit Card Freedom",
                    "description": "Pay down credit card debt step by step",
                    "debt_type": "credit_card",
                    "duration_weeks": 26,
                    "difficulty": DifficultyLevel.MODERATE.value,
                    "milestones_count": 6,
                    "adhd_tips": "Focus on one card at a time. Every payment is progress!"
                }
            ]
        }
        
        # Achievement definitions
        self.achievements = {
            "first_goal": Achievement(
                "first_goal", "Goal Setter", "Created your first financial goal",
                "🎯", "milestone"
            ),
            "first_milestone": Achievement(
                "first_milestone", "First Steps", "Completed your first milestone",
                "👶", "progress"
            ),
            "goal_complete": Achievement(
                "goal_complete", "Goal Crusher", "Completed a full goal",
                "🏆", "completion"
            ),
            "streak_7": Achievement(
                "streak_7", "Week Warrior", "7 days of goal progress",
                "🔥", "streak"
            ),
            "streak_30": Achievement(
                "streak_30", "Month Master", "30 days of consistent progress",
                "💪", "streak"
            ),
            "flexible_friend": Achievement(
                "flexible_friend", "Flexible Friend", "Adjusted a goal without giving up",
                "🤸", "adaptability"
            ),
            "comeback_champion": Achievement(
                "comeback_champion", "Comeback Champion", "Resumed a paused goal",
                "🌅", "resilience"
            )
        }
    
    async def create_goal(
        self,
        user_id: str,
        goal_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new ADHD-friendly goal with automatic milestone generation.
        
        Args:
            user_id: Firebase user ID
            goal_data: Goal configuration data
            
        Returns:
            Created goal data with generated milestones
        """
        try:
            goal_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            # Build goal object
            goal = {
                "id": goal_id,
                "user_id": user_id,
                "type": goal_data["type"],
                "name": goal_data["name"],
                "description": goal_data.get("description", ""),
                "category": goal_data.get("category"),
                "target_amount": goal_data.get("target_amount", 0),
                "current_amount": goal_data.get("current_amount", 0),
                "target_date": goal_data["target_date"],
                "difficulty": goal_data.get("difficulty", DifficultyLevel.MODERATE.value),
                "status": GoalStatus.ACTIVE.value,
                "created_at": current_time,
                "updated_at": current_time,
                "milestones": [],
                "settings": {
                    "allow_adjustments": goal_data.get("allow_adjustments", True),
                    "celebration_style": goal_data.get("celebration_style", "gentle"),
                    "reminder_frequency": goal_data.get("reminder_frequency", "weekly"),
                    "adhd_tips_enabled": goal_data.get("adhd_tips_enabled", True)
                },
                "progress": {
                    "percentage": 0.0,
                    "current_streak": 0,
                    "best_streak": 0,
                    "last_activity": current_time.isoformat(),
                    "milestones_completed": 0,
                    "total_milestones": 0
                },
                "metadata": {
                    "template_used": goal_data.get("template_id"),
                    "creation_method": goal_data.get("creation_method", "manual"),
                    "tags": goal_data.get("tags", [])
                }
            }
            
            # Generate ADHD-friendly milestones
            milestones = await self._generate_milestones(goal)
            goal["milestones"] = [asdict(m) for m in milestones]
            goal["progress"]["total_milestones"] = len(milestones)
            
            # Save to database
            goal_ref = self.db.collection('user_goals').document(f"{user_id}_{goal_id}")
            goal_ref.set(goal)
            
            # Award first goal achievement
            await self._unlock_achievement(user_id, "first_goal")
            
            # Log goal creation
            await self._log_goal_event(user_id, goal_id, "created", {"goal_type": goal["type"]})
            
            logger.info(f"Created goal for user {user_id}: {goal['name']}")
            return goal
            
        except Exception as e:
            logger.error(f"Error creating goal: {str(e)}")
            raise
    
    async def get_user_goals(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
        include_completed: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all goals for a user with current progress."""
        try:
            query = self.db.collection('user_goals').where('user_id', '==', user_id)
            
            if status_filter:
                query = query.where('status', '==', status_filter)
            
            docs = query.stream()
            goals = []
            
            for doc in docs:
                goal_data = doc.to_dict()
                
                # Skip completed goals if not requested
                if not include_completed and goal_data.get('status') == GoalStatus.COMPLETED.value:
                    continue
                
                # Update progress with latest data
                updated_goal = await self._update_goal_progress(goal_data)
                goals.append(updated_goal)
            
            # Sort by creation date (newest first)
            goals.sort(key=lambda g: g.get('created_at', datetime.min), reverse=True)
            
            return goals
            
        except Exception as e:
            logger.error(f"Error getting user goals: {str(e)}")
            return []
    
    async def update_goal_progress(
        self,
        user_id: str,
        goal_id: str,
        new_amount: Optional[float] = None,
        transaction_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Update goal progress based on new transaction or manual entry.
        
        Args:
            user_id: Firebase user ID
            goal_id: Goal ID to update
            new_amount: Manual progress update amount
            transaction_data: Transaction that affects this goal
            
        Returns:
            Updated goal data with new progress
        """
        try:
            goal_ref = self.db.collection('user_goals').document(f"{user_id}_{goal_id}")
            goal_doc = goal_ref.get()
            
            if not goal_doc.exists:
                raise ValueError(f"Goal {goal_id} not found")
            
            goal = goal_doc.to_dict()
            
            # Skip if goal is not active
            if goal.get('status') != GoalStatus.ACTIVE.value:
                return goal
            
            # Calculate new progress
            old_amount = goal.get('current_amount', 0)
            
            if new_amount is not None:
                # Manual update
                goal['current_amount'] = new_amount
                progress_change = new_amount - old_amount
            elif transaction_data:
                # Transaction-based update
                progress_change = await self._calculate_transaction_impact(goal, transaction_data)
                goal['current_amount'] = old_amount + progress_change
            else:
                # No change
                return goal
            
            # Update progress percentage
            target = goal.get('target_amount', 1)
            goal['progress']['percentage'] = min(100.0, (goal['current_amount'] / target) * 100)
            
            # Check for milestone completions
            milestones_completed = await self._check_milestone_completions(goal)
            
            # Update streak tracking
            await self._update_streak_tracking(goal, progress_change > 0)
            
            # Update timestamps
            goal['updated_at'] = datetime.utcnow()
            goal['progress']['last_activity'] = datetime.utcnow().isoformat()
            
            # Check if goal is complete
            if goal['progress']['percentage'] >= 100:
                goal['status'] = GoalStatus.COMPLETED.value
                goal['completed_at'] = datetime.utcnow()
                await self._unlock_achievement(user_id, "goal_complete")
                
                # Send celebration notification
                from app.services.notification_service import NotificationService
                notification_service = NotificationService()
                await notification_service.send_goal_achievement(
                    user_id, goal['name'], "milestone"
                )
            
            # Save updated goal
            goal_ref.set(goal)
            
            # Send milestone notifications for newly completed milestones
            for milestone in milestones_completed:
                await self._send_milestone_celebration(user_id, goal, milestone)
            
            # Log progress update
            await self._log_goal_event(
                user_id, goal_id, "progress_updated",
                {
                    "progress_change": progress_change,
                    "new_percentage": goal['progress']['percentage'],
                    "milestones_completed": len(milestones_completed)
                }
            )
            
            return goal
            
        except Exception as e:
            logger.error(f"Error updating goal progress: {str(e)}")
            raise
    
    async def adjust_goal(
        self,
        user_id: str,
        goal_id: str,
        adjustments: Dict[str, Any],
        reason: str = "user_adjustment"
    ) -> Dict[str, Any]:
        """
        ADHD-friendly goal adjustment without shame.
        
        Args:
            user_id: Firebase user ID
            goal_id: Goal to adjust
            adjustments: Changes to make (target_amount, target_date, etc.)
            reason: Reason for adjustment (for learning/analytics)
            
        Returns:
            Adjusted goal data
        """
        try:
            goal_ref = self.db.collection('user_goals').document(f"{user_id}_{goal_id}")
            goal_doc = goal_ref.get()
            
            if not goal_doc.exists:
                raise ValueError(f"Goal {goal_id} not found")
            
            goal = goal_doc.to_dict()
            
            # Check if adjustments are allowed
            if not goal.get('settings', {}).get('allow_adjustments', True):
                raise ValueError("Goal adjustments are disabled for this goal")
            
            old_values = {}
            
            # Apply adjustments
            for key, value in adjustments.items():
                if key in ['target_amount', 'target_date', 'name', 'description']:
                    old_values[key] = goal.get(key)
                    goal[key] = value
            
            # Regenerate milestones if target changed significantly
            if 'target_amount' in adjustments or 'target_date' in adjustments:
                milestones = await self._generate_milestones(goal)
                goal['milestones'] = [asdict(m) for m in milestones]
                goal['progress']['total_milestones'] = len(milestones)
            
            # Update progress percentage with new target
            if 'target_amount' in adjustments:
                new_target = adjustments['target_amount']
                current = goal.get('current_amount', 0)
                goal['progress']['percentage'] = min(100.0, (current / new_target) * 100)
            
            # Update metadata
            goal['updated_at'] = datetime.utcnow()
            goal['adjustments'] = goal.get('adjustments', []) + [{
                'date': datetime.utcnow().isoformat(),
                'reason': reason,
                'changes': adjustments,
                'old_values': old_values
            }]
            
            # Save updated goal
            goal_ref.set(goal)
            
            # Award flexibility achievement
            await self._unlock_achievement(user_id, "flexible_friend")
            
            # Log adjustment
            await self._log_goal_event(
                user_id, goal_id, "adjusted",
                {"reason": reason, "adjustments": list(adjustments.keys())}
            )
            
            logger.info(f"Adjusted goal {goal_id} for user {user_id}: {reason}")
            return goal
            
        except Exception as e:
            logger.error(f"Error adjusting goal: {str(e)}")
            raise
    
    async def pause_goal(
        self,
        user_id: str,
        goal_id: str,
        reason: str = "need_a_break"
    ) -> Dict[str, Any]:
        """
        Pause a goal without shame - ADHD brains sometimes need breaks!
        
        Args:
            user_id: Firebase user ID
            goal_id: Goal to pause
            reason: Reason for pausing (for support and learning)
            
        Returns:
            Paused goal data
        """
        try:
            goal_ref = self.db.collection('user_goals').document(f"{user_id}_{goal_id}")
            goal_doc = goal_ref.get()
            
            if not goal_doc.exists:
                raise ValueError(f"Goal {goal_id} not found")
            
            goal = goal_doc.to_dict()
            
            # Update status and metadata
            goal['status'] = GoalStatus.PAUSED.value
            goal['paused_at'] = datetime.utcnow()
            goal['pause_reason'] = reason
            goal['updated_at'] = datetime.utcnow()
            
            # Save paused goal
            goal_ref.set(goal)
            
            # Log pause event
            await self._log_goal_event(
                user_id, goal_id, "paused",
                {"reason": reason}
            )
            
            logger.info(f"Paused goal {goal_id} for user {user_id}: {reason}")
            return goal
            
        except Exception as e:
            logger.error(f"Error pausing goal: {str(e)}")
            raise
    
    async def resume_goal(
        self,
        user_id: str,
        goal_id: str,
        extend_deadline: bool = True
    ) -> Dict[str, Any]:
        """
        Resume a paused goal with encouragement.
        
        Args:
            user_id: Firebase user ID
            goal_id: Goal to resume
            extend_deadline: Whether to extend deadline by pause duration
            
        Returns:
            Resumed goal data
        """
        try:
            goal_ref = self.db.collection('user_goals').document(f"{user_id}_{goal_id}")
            goal_doc = goal_ref.get()
            
            if not goal_doc.exists:
                raise ValueError(f"Goal {goal_id} not found")
            
            goal = goal_doc.to_dict()
            
            if goal.get('status') != GoalStatus.PAUSED.value:
                raise ValueError("Goal is not paused")
            
            # Calculate pause duration
            paused_at = goal.get('paused_at')
            if paused_at and extend_deadline:
                pause_duration = datetime.utcnow() - paused_at
                
                # Extend target date by pause duration
                if 'target_date' in goal:
                    original_date = datetime.fromisoformat(goal['target_date'].replace('Z', '+00:00'))
                    new_date = original_date + pause_duration
                    goal['target_date'] = new_date.isoformat()
            
            # Update status
            goal['status'] = GoalStatus.ACTIVE.value
            goal['resumed_at'] = datetime.utcnow()
            goal['updated_at'] = datetime.utcnow()
            
            # Remove pause-specific fields
            if 'paused_at' in goal:
                del goal['paused_at']
            if 'pause_reason' in goal:
                del goal['pause_reason']
            
            # Save resumed goal
            goal_ref.set(goal)
            
            # Award comeback achievement
            await self._unlock_achievement(user_id, "comeback_champion")
            
            # Send encouragement notification
            from app.services.notification_service import NotificationService
            notification_service = NotificationService()
            await notification_service.send_encouragement(
                user_id, "comeback", {"goal_name": goal['name']}
            )
            
            # Log resume event
            await self._log_goal_event(
                user_id, goal_id, "resumed",
                {"deadline_extended": extend_deadline}
            )
            
            logger.info(f"Resumed goal {goal_id} for user {user_id}")
            return goal
            
        except Exception as e:
            logger.error(f"Error resuming goal: {str(e)}")
            raise
    
    async def get_goal_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get ADHD-friendly goal templates."""
        return {
            goal_type.value: templates 
            for goal_type, templates in self.goal_templates.items()
        }
    
    async def get_user_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's unlocked achievements and progress."""
        try:
            achievements_ref = self.db.collection('user_achievements').document(user_id)
            achievements_doc = achievements_ref.get()
            
            if achievements_doc.exists:
                user_achievements = achievements_doc.to_dict()
            else:
                user_achievements = {"unlocked": [], "progress": {}}
            
            # Build response with all achievements and unlock status
            result = []
            for achievement_id, achievement in self.achievements.items():
                achievement_data = asdict(achievement)
                achievement_data['unlocked'] = achievement_id in user_achievements.get('unlocked', [])
                
                if achievement_data['unlocked']:
                    # Get unlock date from user data
                    unlock_data = user_achievements.get('unlock_dates', {}).get(achievement_id)
                    if unlock_data:
                        achievement_data['unlocked_date'] = unlock_data
                
                # Get current progress
                progress = user_achievements.get('progress', {}).get(achievement_id, 0.0)
                achievement_data['progress'] = progress
                
                result.append(achievement_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user achievements: {str(e)}")
            return []
    
    async def get_goal_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics data for user's goal progress."""
        try:
            # Get all user goals
            goals = await self.get_user_goals(user_id, include_completed=True)
            
            # Calculate analytics
            total_goals = len(goals)
            completed_goals = len([g for g in goals if g.get('status') == GoalStatus.COMPLETED.value])
            active_goals = len([g for g in goals if g.get('status') == GoalStatus.ACTIVE.value])
            paused_goals = len([g for g in goals if g.get('status') == GoalStatus.PAUSED.value])
            
            # Calculate success rate
            success_rate = (completed_goals / total_goals * 100) if total_goals > 0 else 0
            
            # Get total milestones completed
            total_milestones = sum(g.get('progress', {}).get('milestones_completed', 0) for g in goals)
            
            # Get best streak
            best_streak = max(g.get('progress', {}).get('best_streak', 0) for g in goals) if goals else 0
            
            # Get achievements count
            achievements = await self.get_user_achievements(user_id)
            unlocked_achievements = len([a for a in achievements if a.get('unlocked')])
            
            return {
                "total_goals": total_goals,
                "completed_goals": completed_goals,
                "active_goals": active_goals,
                "paused_goals": paused_goals,
                "success_rate": round(success_rate, 1),
                "total_milestones_completed": total_milestones,
                "best_streak": best_streak,
                "unlocked_achievements": unlocked_achievements,
                "total_achievements": len(achievements)
            }
            
        except Exception as e:
            logger.error(f"Error getting goal analytics: {str(e)}")
            return {}
    
    # Private helper methods
    
    async def _generate_milestones(self, goal: Dict[str, Any]) -> List[Milestone]:
        """Generate ADHD-friendly milestones for a goal."""
        milestones = []
        goal_type = goal.get('type')
        target_amount = goal.get('target_amount', 0)
        target_date = datetime.fromisoformat(goal.get('target_date').replace('Z', '+00:00'))
        created_date = goal.get('created_at', datetime.utcnow())
        
        if isinstance(created_date, str):
            created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
        
        total_duration = (target_date - created_date).days
        
        # Determine number of milestones based on difficulty and duration
        difficulty = goal.get('difficulty', DifficultyLevel.MODERATE.value)
        
        if difficulty == DifficultyLevel.GENTLE.value:
            milestone_count = min(4, max(2, total_duration // 14))  # Every 2 weeks max
        elif difficulty == DifficultyLevel.MODERATE.value:
            milestone_count = min(6, max(3, total_duration // 10))  # Every 10 days max  
        else:  # AMBITIOUS
            milestone_count = min(10, max(4, total_duration // 7))  # Weekly max
        
        # Generate milestones
        for i in range(milestone_count):
            progress = (i + 1) / milestone_count
            milestone_amount = target_amount * progress
            
            # Calculate milestone date
            milestone_days = total_duration * progress
            milestone_date = created_date + timedelta(days=int(milestone_days))
            
            # Create encouraging milestone titles
            if goal_type == GoalType.SAVINGS_TARGET.value:
                title = f"Save ${milestone_amount:.0f}"
                description = f"You're {progress*100:.0f}% of the way to your goal! 🎯"
            elif goal_type == GoalType.SPENDING_REDUCTION.value:
                title = f"Reduce to ${milestone_amount:.0f}/month"
                description = f"Cut back by {progress*100:.0f}% - you've got this! 💪"
            elif goal_type == GoalType.DEBT_REDUCTION.value:
                title = f"Pay down to ${target_amount - milestone_amount:.0f}"
                description = f"Eliminated ${milestone_amount:.0f} in debt - amazing! 🎉"
            elif goal_type == GoalType.EMERGENCY_FUND.value:
                title = f"Build ${milestone_amount:.0f} safety net"
                description = f"Your future self will thank you! 🛡️"
            else:
                title = f"Milestone {i+1}"
                description = f"Step {i+1} of {milestone_count} complete!"
            
            milestone = Milestone(
                id=str(uuid.uuid4()),
                title=title,
                description=description,
                target_value=milestone_amount,
                target_date=milestone_date.isoformat(),
                order=i+1
            )
            
            milestones.append(milestone)
        
        return milestones
    
    async def _update_goal_progress(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """Update goal progress with latest transaction data."""
        # This would integrate with transaction data to calculate real progress
        # For now, return the goal as-is
        return goal
    
    async def _calculate_transaction_impact(
        self,
        goal: Dict[str, Any],
        transaction: Dict[str, Any]
    ) -> float:
        """Calculate how a transaction impacts goal progress."""
        goal_type = goal.get('type')
        transaction_amount = abs(transaction.get('amount', 0))
        transaction_category = transaction.get('category', '').lower()
        goal_category = goal.get('category', '').lower()
        
        if goal_type == GoalType.SAVINGS_TARGET.value:
            # Positive progress for savings transactions
            if transaction.get('type') == 'transfer' and 'savings' in transaction.get('description', '').lower():
                return transaction_amount
            
        elif goal_type == GoalType.SPENDING_REDUCTION.value:
            # Negative progress for spending in target category
            if goal_category and transaction_category == goal_category:
                return -transaction_amount
            
        elif goal_type == GoalType.DEBT_REDUCTION.value:
            # Positive progress for debt payments
            if 'payment' in transaction.get('description', '').lower():
                return transaction_amount
        
        return 0.0
    
    async def _check_milestone_completions(self, goal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check and mark newly completed milestones."""
        current_amount = goal.get('current_amount', 0)
        completed_milestones = []
        
        milestones = goal.get('milestones', [])
        for milestone in milestones:
            if not milestone.get('completed') and current_amount >= milestone.get('target_value', 0):
                milestone['completed'] = True
                milestone['completed_date'] = datetime.utcnow().isoformat()
                completed_milestones.append(milestone)
                
                # Update progress counters
                goal['progress']['milestones_completed'] = goal['progress'].get('milestones_completed', 0) + 1
        
        return completed_milestones
    
    async def _update_streak_tracking(self, goal: Dict[str, Any], made_progress: bool):
        """Update streak tracking for consistent goal progress."""
        if made_progress:
            goal['progress']['current_streak'] = goal['progress'].get('current_streak', 0) + 1
            goal['progress']['best_streak'] = max(
                goal['progress'].get('best_streak', 0),
                goal['progress']['current_streak']
            )
        else:
            goal['progress']['current_streak'] = 0
    
    async def _send_milestone_celebration(
        self,
        user_id: str,
        goal: Dict[str, Any],
        milestone: Dict[str, Any]
    ):
        """Send celebration notification for completed milestone."""
        try:
            if milestone.get('celebration_sent'):
                return
            
            from app.services.notification_service import NotificationService
            notification_service = NotificationService()
            
            await notification_service.send_goal_achievement(
                user_id,
                f"{goal['name']} - {milestone['title']}",
                "milestone"
            )
            
            milestone['celebration_sent'] = True
            
            # Award milestone achievement if this is their first
            milestones_completed = goal.get('progress', {}).get('milestones_completed', 0)
            if milestones_completed == 1:
                await self._unlock_achievement(user_id, "first_milestone")
            
        except Exception as e:
            logger.error(f"Error sending milestone celebration: {str(e)}")
    
    async def _unlock_achievement(self, user_id: str, achievement_id: str):
        """Unlock an achievement for the user."""
        try:
            achievements_ref = self.db.collection('user_achievements').document(user_id)
            achievements_doc = achievements_ref.get()
            
            if achievements_doc.exists:
                user_achievements = achievements_doc.to_dict()
            else:
                user_achievements = {"unlocked": [], "unlock_dates": {}, "progress": {}}
            
            # Check if already unlocked
            if achievement_id in user_achievements.get('unlocked', []):
                return
            
            # Unlock achievement
            user_achievements['unlocked'].append(achievement_id)
            user_achievements['unlock_dates'][achievement_id] = datetime.utcnow().isoformat()
            
            # Save updated achievements
            achievements_ref.set(user_achievements)
            
            # Send achievement notification
            achievement = self.achievements.get(achievement_id)
            if achievement:
                from app.services.notification_service import NotificationService
                notification_service = NotificationService()
                
                await notification_service.send_goal_achievement(
                    user_id,
                    f"🎉 {achievement.name}",
                    "achievement"
                )
            
            logger.info(f"Unlocked achievement {achievement_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error unlocking achievement: {str(e)}")
    
    async def _log_goal_event(
        self,
        user_id: str,
        goal_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """Log goal events for analytics and debugging."""
        try:
            event = {
                "user_id": user_id,
                "goal_id": goal_id,
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": datetime.utcnow(),
                "source": "goals_service"
            }
            
            self.db.collection('goal_events').add(event)
            
        except Exception as e:
            logger.error(f"Error logging goal event: {str(e)}")
    
    # Synchronous wrappers for Flask routes (since Flask doesn't support async)
    
    def create_goal_sync(self, user_id: str, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for create_goal."""
        import asyncio
        return asyncio.run(self.create_goal(user_id, goal_data))
    
    def get_user_goals_sync(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
        include_completed: bool = True
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_user_goals."""
        import asyncio
        return asyncio.run(self.get_user_goals(user_id, status_filter, include_completed))
    
    def update_goal_progress_sync(
        self,
        user_id: str,
        goal_id: str,
        new_amount: Optional[float] = None,
        transaction_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for update_goal_progress."""
        import asyncio
        return asyncio.run(self.update_goal_progress(user_id, goal_id, new_amount, transaction_data))
    
    def adjust_goal_sync(
        self,
        user_id: str,
        goal_id: str,
        adjustments: Dict[str, Any],
        reason: str = "user_adjustment"
    ) -> Dict[str, Any]:
        """Synchronous wrapper for adjust_goal."""
        import asyncio
        return asyncio.run(self.adjust_goal(user_id, goal_id, adjustments, reason))
    
    def pause_goal_sync(
        self,
        user_id: str,
        goal_id: str,
        reason: str = "need_a_break"
    ) -> Dict[str, Any]:
        """Synchronous wrapper for pause_goal."""
        import asyncio
        return asyncio.run(self.pause_goal(user_id, goal_id, reason))
    
    def resume_goal_sync(
        self,
        user_id: str,
        goal_id: str,
        extend_deadline: bool = True
    ) -> Dict[str, Any]:
        """Synchronous wrapper for resume_goal."""
        import asyncio
        return asyncio.run(self.resume_goal(user_id, goal_id, extend_deadline))
    
    def get_goal_templates_sync(self) -> Dict[str, List[Dict[str, Any]]]:
        """Synchronous wrapper for get_goal_templates."""
        import asyncio
        return asyncio.run(self.get_goal_templates())
    
    def get_user_achievements_sync(self, user_id: str) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_user_achievements."""
        import asyncio
        return asyncio.run(self.get_user_achievements(user_id))
    
    def get_goal_analytics_sync(self, user_id: str) -> Dict[str, Any]:
        """Synchronous wrapper for get_goal_analytics."""
        import asyncio
        return asyncio.run(self.get_goal_analytics(user_id))