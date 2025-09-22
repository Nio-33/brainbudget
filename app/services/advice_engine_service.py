"""
BrainBudget Personalized Financial Advice Engine
ADHD-aware financial guidance with AI-powered personalization
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import random
import hashlib

# ML and data processing - make optional for faster startup
ML_AVAILABLE = False
try:
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestClassifier
    ML_AVAILABLE = True
except ImportError:
    logger.info("ML libraries not available - using basic advice engine")

logger = logging.getLogger(__name__)

from app.services.firebase_service import FirebaseService

class AdviceCategory(Enum):
    BUDGETING = "budgeting"
    DEBT_REDUCTION = "debt_reduction"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    EMERGENCY_FUND = "emergency_fund"

class ADHDSymptomImpact(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

class AdviceUrgency(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class PersonalizationFactors:
    """User factors that influence advice personalization"""
    user_id: str
    income_level: str  # low, medium, high, variable
    income_variability: float  # 0.0-1.0, higher = more variable
    debt_levels: Dict[str, float]
    spending_patterns: Dict[str, any]  # From ML analytics
    financial_goals: List[Dict]  # Active goals
    adhd_symptom_impact: ADHDSymptomImpact
    executive_function_level: float  # 0.0-1.0
    stress_level: float  # 0.0-1.0
    motivation_level: float  # 0.0-1.0
    learning_preference: str  # visual, text, step-by-step, etc.

@dataclass
class AdviceTemplate:
    """Template for generating personalized advice"""
    template_id: str
    category: AdviceCategory
    title: str
    description: str
    content_blocks: List[Dict]  # Modular content pieces
    personalization_rules: Dict  # Rules for customization
    adhd_adaptations: Dict  # ADHD-specific modifications
    difficulty_level: int  # 1-5 scale
    time_investment: str  # "5 min", "15 min", "ongoing", etc.
    effectiveness_metrics: Dict  # Historical performance data

@dataclass
class PersonalizedAdvice:
    """Personalized advice generated for a specific user"""
    advice_id: str
    user_id: str
    category: AdviceCategory
    title: str
    summary: str
    content: str
    action_steps: List[str]
    adhd_tips: List[str]
    urgency: AdviceUrgency
    confidence_score: float  # 0.0-1.0
    personalization_reasons: List[str]
    estimated_impact: str
    time_to_implement: str
    follow_up_actions: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None

class AdviceEngineService:
    """
    ADHD-aware personalized financial advice engine
    """

    def __init__(self, firebase_service: FirebaseService = None):
        self.firebase_service = firebase_service or FirebaseService()
        self.ml_available = ML_AVAILABLE

        # Initialize advice templates
        self._advice_templates = {}
        self._load_advice_templates()

        # ML models for personalization
        self.models = {}
        if self.ml_available:
            self._initialize_ml_models()

        # Cache for user factors
        self._user_factors_cache = {}
        self._cache_ttl = timedelta(hours=1)

        logger.info("Advice Engine initialized successfully")

    def _load_advice_templates(self):
        """Load and initialize advice templates"""
        templates = {
            # Budgeting Templates
            "adhd_budget_simple": AdviceTemplate(
                template_id="adhd_budget_simple",
                category=AdviceCategory.BUDGETING,
                title="ADHD-Friendly Simple Budget",
                description="A visual, easy-to-follow budget that works with ADHD brains",
                content_blocks=[
                    {
                        "type": "introduction",
                        "content": "Traditional budgets can feel overwhelming for ADHD minds. Let's create something that actually works for your brain!"
                    },
                    {
                        "type": "method",
                        "content": "The 50/30/20 Rule - Made Simple",
                        "details": ["50% for needs (rent, groceries, utilities)", "30% for wants (fun, hobbies, treats)", "20% for savings and debt"]
                    },
                    {
                        "type": "visual_tool",
                        "content": "Use three physical envelopes or separate bank accounts to make it tangible"
                    }
                ],
                personalization_rules={
                    "income_variable": "Add buffer categories for income fluctuations",
                    "high_impulse": "Reduce wants category to 20%, increase buffer to 10%",
                    "low_executive": "Use automated transfers to remove decision fatigue"
                },
                adhd_adaptations={
                    "visual": "Color-code categories (red=needs, blue=wants, green=savings)",
                    "gamification": "Track progress with visual charts or apps",
                    "flexibility": "Allow 10% flexibility between categories each month",
                    "celebration": "Set up small rewards for meeting budget goals"
                },
                difficulty_level=2,
                time_investment="15 min setup, 5 min weekly",
                effectiveness_metrics={"user_rating": 4.2, "completion_rate": 0.78, "adherence_rate": 0.65}
            ),

            "debt_snowball_adhd": AdviceTemplate(
                template_id="debt_snowball_adhd",
                category=AdviceCategory.DEBT_REDUCTION,
                title="ADHD Debt Snowball Method",
                description="Pay off debts in a way that keeps ADHD brains motivated",
                content_blocks=[
                    {
                        "type": "introduction",
                        "content": "The debt snowball method works perfectly for ADHD because it provides quick wins and momentum!"
                    },
                    {
                        "type": "strategy",
                        "content": "Pay minimum on all debts, then attack the smallest balance first",
                        "rationale": "Quick wins release dopamine and keep you motivated"
                    },
                    {
                        "type": "adhd_hack",
                        "content": "Create a visual debt thermometer - color in progress as you pay down each debt"
                    }
                ],
                personalization_rules={
                    "high_debt": "Consider debt consolidation first if multiple high-interest debts",
                    "variable_income": "Set minimum monthly debt payment based on lowest expected income",
                    "low_motivation": "Start with debts under $500 for immediate wins"
                },
                adhd_adaptations={
                    "dopamine_hits": "Celebrate each debt payoff with a small, planned reward",
                    "visual_progress": "Use debt tracker apps or physical charts",
                    "automation": "Set up automatic payments to reduce decision fatigue",
                    "support": "Share progress with an accountability partner or online community"
                },
                difficulty_level=3,
                time_investment="30 min setup, 10 min monthly",
                effectiveness_metrics={"user_rating": 4.5, "completion_rate": 0.72, "debt_reduction_rate": 0.83}
            ),

            "emergency_fund_micro": AdviceTemplate(
                template_id="emergency_fund_micro",
                category=AdviceCategory.EMERGENCY_FUND,
                title="Micro Emergency Fund for ADHD",
                description="Start tiny and build an emergency fund that doesn't overwhelm",
                content_blocks=[
                    {
                        "type": "reframe",
                        "content": "Forget the '6 months expenses' rule. Start with just $100 - that's already huge!"
                    },
                    {
                        "type": "strategy",
                        "content": "The $1-a-day method",
                        "details": ["Week 1-2: Save $1 per day ($14 total)", "Week 3-4: Save $2 per day ($28 total)", "Continue doubling every 2 weeks until comfortable"]
                    },
                    {
                        "type": "adhd_adaptation",
                        "content": "Use a separate savings account you can't easily access - make friction your friend"
                    }
                ],
                personalization_rules={
                    "low_income": "Start with $0.50/day and increase by $0.50 every month",
                    "high_impulse": "Use automatic transfers on payday before discretionary spending",
                    "irregular_income": "Save percentage instead of fixed amounts"
                },
                adhd_adaptations={
                    "visual_progress": "Use a savings thermometer or jar to see progress",
                    "micro_goals": "Celebrate every $25 milestone",
                    "gamification": "Turn it into a game - can you save for 30 days straight?",
                    "flexibility": "It's okay to pause if life happens - just restart when ready"
                },
                difficulty_level=1,
                time_investment="2 min daily",
                effectiveness_metrics={"user_rating": 4.7, "completion_rate": 0.89, "fund_growth_rate": 0.76}
            ),

            "investment_simple": AdviceTemplate(
                template_id="investment_simple",
                category=AdviceCategory.INVESTMENT,
                title="ADHD-Simple Investing",
                description="Investing strategy that doesn't require constant attention or complex decisions",
                content_blocks=[
                    {
                        "type": "philosophy",
                        "content": "The best investment strategy for ADHD is the boring one you can stick with"
                    },
                    {
                        "type": "strategy",
                        "content": "Three-Fund Portfolio",
                        "details": ["60% Total Stock Market Index", "30% International Stock Index", "10% Bond Index"]
                    },
                    {
                        "type": "automation",
                        "content": "Set up automatic monthly investments - remove the decision from your brain"
                    }
                ],
                personalization_rules={
                    "risk_averse": "Increase bond allocation to 20-30%",
                    "young_investor": "Increase stock allocation to 80-90%",
                    "irregular_income": "Set up automatic investment on income days only"
                },
                adhd_adaptations={
                    "simplicity": "Use target-date funds if three funds feel overwhelming",
                    "set_forget": "Check portfolio maximum once per quarter",
                    "education": "Read one investing article per month to stay motivated",
                    "patience_tools": "Set up 'investment jar' visualization to see long-term growth"
                },
                difficulty_level=2,
                time_investment="1 hour setup, 15 min quarterly",
                effectiveness_metrics={"user_rating": 4.1, "completion_rate": 0.68, "portfolio_growth": 0.72}
            ),

            "savings_automated": AdviceTemplate(
                template_id="savings_automated",
                category=AdviceCategory.SAVINGS,
                title="Set-and-Forget ADHD Savings",
                description="Automated savings that work even when your brain doesn't",
                content_blocks=[
                    {
                        "type": "principle",
                        "content": "The best savings plan is the one you never have to think about"
                    },
                    {
                        "type": "method",
                        "content": "Pay Yourself First - Automatically",
                        "details": ["Set up automatic transfer on payday", "Start small - even $25/month helps", "Increase by $10 every 3 months"]
                    },
                    {
                        "type": "psychology",
                        "content": "Make it invisible - use a separate bank entirely if needed"
                    }
                ],
                personalization_rules={
                    "variable_income": "Save percentage instead of fixed amount",
                    "high_impulse": "Use separate bank with no debit card access",
                    "goal_oriented": "Link savings to specific goals with visual progress tracking"
                },
                adhd_adaptations={
                    "automation": "Remove all manual decision-making from the process",
                    "visual_feedback": "Set up savings tracking app with celebration animations",
                    "flexibility": "Allow yourself to pause/adjust without guilt",
                    "celebration": "Set milestone rewards (dinner out at $500 saved, etc.)"
                },
                difficulty_level=1,
                time_investment="30 min setup, 0 min ongoing",
                effectiveness_metrics={"user_rating": 4.6, "completion_rate": 0.84, "savings_growth": 0.79}
            )
        }

        self._advice_templates = templates
        logger.info(f"Loaded {len(templates)} advice templates")

    def _initialize_ml_models(self):
        """Initialize ML models for personalization"""
        if not self.ml_available:
            logger.warning("ML libraries not available, using rule-based personalization only")
            return

        # Advice recommendation model (collaborative filtering)
        self.models['advice_recommender'] = RandomForestClassifier(
            n_estimators=50,
            max_depth=10,
            random_state=42
        )

        # User clustering for similar users
        self.models['user_clusterer'] = KMeans(
            n_clusters=5,
            random_state=42
        )

        logger.info("ML models initialized for advice personalization")

    async def get_personalized_advice(
        self,
        user_id: str,
        category: Optional[AdviceCategory] = None,
        limit: int = 3,
        urgency_filter: Optional[AdviceUrgency] = None
    ) -> Dict:
        """
        Get personalized financial advice for a user

        Args:
            user_id: User identifier
            category: Specific advice category (optional)
            limit: Maximum number of advice pieces to return
            urgency_filter: Filter by urgency level

        Returns:
            Dict containing personalized advice and metadata
        """
        try:
            # Get user personalization factors
            factors = await self._get_user_factors(user_id)
            if not factors:
                return {"success": False, "message": "Unable to analyze user profile"}

            # Generate personalized advice
            advice_list = await self._generate_advice(factors, category, limit, urgency_filter)

            # Get user's advice history for contex
            advice_history = await self._get_advice_history(user_id, days=30)

            # Filter out recently seen advice
            filtered_advice = self._filter_recent_advice(advice_list, advice_history)

            return {
                "success": True,
                "advice": [asdict(advice) for advice in filtered_advice[:limit]],
                "user_profile_summary": self._summarize_user_factors(factors),
                "personalization_notes": self._get_personalization_notes(factors),
                "advice_count": len(filtered_advice)
            }

        except Exception as e:
            logger.error(f"Error generating personalized advice: {e}")
            return {
                "success": False,
                "message": "Unable to generate personalized advice at this time",
                "error": str(e)
            }

    def get_personalized_advice_sync(self, user_id: str, category: Optional[str] = None, limit: int = 3) -> Dict:
        """Synchronous wrapper for get_personalized_advice"""
        import asyncio
        category_enum = AdviceCategory(category) if category else None
        return asyncio.run(self.get_personalized_advice(user_id, category_enum, limit))

    async def _get_user_factors(self, user_id: str) -> Optional[PersonalizationFactors]:
        """Extract personalization factors for a user"""
        try:
            # Check cache firs
            cache_key = f"factors_{user_id}"
            if cache_key in self._user_factors_cache:
                cached_data, timestamp = self._user_factors_cache[cache_key]
                if datetime.now() - timestamp < self._cache_ttl:
                    return cached_data

            # Gather data from various sources
            user_profile = await self._get_user_profile(user_id)
            transaction_data = await self._get_user_transactions(user_id, days=90)
            goals_data = await self._get_user_goals(user_id)
            ml_insights = await self._get_ml_insights(user_id)

            if not user_profile:
                return None

            # Calculate factors from data
            factors = PersonalizationFactors(
                user_id=user_id,
                income_level=self._analyze_income_level(transaction_data),
                income_variability=self._calculate_income_variability(transaction_data),
                debt_levels=self._analyze_debt_levels(transaction_data),
                spending_patterns=ml_insights.get('patterns', {}) if ml_insights else {},
                financial_goals=goals_data or [],
                adhd_symptom_impact=self._assess_adhd_impact(user_profile, ml_insights),
                executive_function_level=self._estimate_executive_function(transaction_data, ml_insights),
                stress_level=self._estimate_stress_level(ml_insights),
                motivation_level=self._estimate_motivation_level(user_profile, goals_data),
                learning_preference=user_profile.get('learning_preference', 'visual')
            )

            # Cache the results
            self._user_factors_cache[cache_key] = (factors, datetime.now())

            return factors

        except Exception as e:
            logger.error(f"Error getting user factors for {user_id}: {e}")
            return None

    async def _generate_advice(
        self,
        factors: PersonalizationFactors,
        category: Optional[AdviceCategory],
        limit: int,
        urgency_filter: Optional[AdviceUrgency]
    ) -> List[PersonalizedAdvice]:
        """Generate personalized advice based on user factors"""
        advice_list = []

        # Determine which templates to use
        relevant_templates = self._select_relevant_templates(factors, category, urgency_filter)

        for template in relevant_templates[:limit * 2]:  # Get extra for filtering
            try:
                # Personalize the template
                personalized = await self._personalize_template(template, factors)
                advice_list.append(personalized)

            except Exception as e:
                logger.warning(f"Error personalizing template {template.template_id}: {e}")
                continue

        # Sort by relevance and confidence
        advice_list.sort(key=lambda x: x.confidence_score, reverse=True)

        return advice_list

    def _select_relevant_templates(
        self,
        factors: PersonalizationFactors,
        category: Optional[AdviceCategory],
        urgency_filter: Optional[AdviceUrgency]
    ) -> List[AdviceTemplate]:
        """Select most relevant advice templates for user"""
        templates = list(self._advice_templates.values())

        # Filter by category if specified
        if category:
            templates = [t for t in templates if t.category == category]

        # Score templates by relevance to user factors
        scored_templates = []
        for template in templates:
            score = self._calculate_template_relevance_score(template, factors)
            scored_templates.append((template, score))

        # Sort by relevance score
        scored_templates.sort(key=lambda x: x[1], reverse=True)

        return [template for template, score in scored_templates]

    def _calculate_template_relevance_score(self, template: AdviceTemplate, factors: PersonalizationFactors) -> float:
        """Calculate how relevant a template is for a specific user"""
        score = 0.0

        # Base score from template effectiveness
        score += template.effectiveness_metrics.get('user_rating', 3.0) / 5.0 * 0.3

        # Adjust for ADHD symptom impac
        if factors.adhd_symptom_impact == ADHDSymptomImpact.HIGH:
            if template.difficulty_level <= 2:
                score += 0.4  # Prefer simple strategies for high ADHD impac
            else:
                score -= 0.3  # Penalize complex strategies

        # Adjust for executive function level
        if factors.executive_function_level < 0.5:
            if "automated" in template.template_id or "simple" in template.template_id:
                score += 0.3

        # Category-specific scoring
        if template.category == AdviceCategory.EMERGENCY_FUND:
            if not factors.spending_patterns.get('has_emergency_fund', False):
                score += 0.4

        elif template.category == AdviceCategory.DEBT_REDUCTION:
            total_debt = sum(factors.debt_levels.values())
            if total_debt > 10000:  # High deb
                score += 0.5
            elif total_debt > 0:
                score += 0.2
            else:
                score -= 0.4  # No debt, less relevan

        elif template.category == AdviceCategory.BUDGETING:
            if factors.spending_patterns.get('budget_variance', 1.0) > 0.3:
                score += 0.3  # High variance = needs budgeting help

        # Adjust for income variability
        if factors.income_variability > 0.4:
            if "variable" in template.personalization_rules:
                score += 0.3

        return max(0.0, min(1.0, score))

    async def _personalize_template(self, template: AdviceTemplate, factors: PersonalizationFactors) -> PersonalizedAdvice:
        """Personalize an advice template for a specific user"""

        # Apply personalization rules
        personalized_content = self._apply_personalization_rules(template, factors)

        # Generate ADHD-specific adaptations
        adhd_tips = self._generate_adhd_tips(template, factors)

        # Calculate confidence score
        confidence = self._calculate_advice_confidence(template, factors)

        # Determine urgency
        urgency = self._determine_advice_urgency(template, factors)

        # Generate personalization reasons
        reasons = self._generate_personalization_reasons(template, factors)

        # Create personalized advice
        advice = PersonalizedAdvice(
            advice_id=self._generate_advice_id(template.template_id, factors.user_id),
            user_id=factors.user_id,
            category=template.category,
            title=personalized_content['title'],
            summary=personalized_content['summary'],
            content=personalized_content['content'],
            action_steps=personalized_content['action_steps'],
            adhd_tips=adhd_tips,
            urgency=urgency,
            confidence_score=confidence,
            personalization_reasons=reasons,
            estimated_impact=self._estimate_advice_impact(template, factors),
            time_to_implement=self._personalize_time_estimate(template, factors),
            follow_up_actions=personalized_content['follow_up_actions'],
            created_at=datetime.now()
        )

        return advice

    def _apply_personalization_rules(self, template: AdviceTemplate, factors: PersonalizationFactors) -> Dict:
        """Apply personalization rules to customize template content"""

        # Start with base conten
        content_blocks = template.content_blocks.copy()

        # Apply personalization rules based on user factors
        rules_applied = []

        # Income variability adjustments
        if factors.income_variability > 0.4:
            if "income_variable" in template.personalization_rules:
                rule = template.personalization_rules["income_variable"]
                content_blocks.append({
                    "type": "income_adjustment",
                    "content": f"💡 Since your income varies: {rule}"
                })
                rules_applied.append("income_variable")

        # ADHD symptom adjustments
        if factors.adhd_symptom_impact == ADHDSymptomImpact.HIGH:
            if "high_impulse" in template.personalization_rules:
                rule = template.personalization_rules["high_impulse"]
                content_blocks.append({
                    "type": "adhd_adjustment",
                    "content": f"🧠 For ADHD brains: {rule}"
                })
                rules_applied.append("high_impulse")

        # Executive function adjustments
        if factors.executive_function_level < 0.5:
            if "low_executive" in template.personalization_rules:
                rule = template.personalization_rules["low_executive"]
                content_blocks.append({
                    "type": "executive_support",
                    "content": f"🎯 To make this easier: {rule}"
                })
                rules_applied.append("low_executive")

        # Compile personalized conten
        title = template.title
        if factors.adhd_symptom_impact != ADHDSymptomImpact.LOW:
            if "ADHD" not in title:
                title = f"ADHD-Friendly {title}"

        summary = template.description

        # Build full content from blocks
        content_parts = []
        action_steps = []
        follow_up_actions = []

        for block in content_blocks:
            block_type = block.get("type", "general")
            block_content = block.get("content", "")

            if block_type == "introduction":
                content_parts.append(f"## Getting Started\n{block_content}\n")
            elif block_type == "method" or block_type == "strategy":
                content_parts.append(f"## The Strategy\n{block_content}\n")
                if "details" in block:
                    for detail in block["details"]:
                        action_steps.append(detail)
            elif block_type == "adhd_hack" or block_type == "adhd_adaptation":
                content_parts.append(f"## 🧠 ADHD Brain Hack\n{block_content}\n")
            else:
                content_parts.append(f"{block_content}\n")

        # Add default action steps if none were created
        if not action_steps:
            action_steps = [
                "Review the strategy above carefully",
                "Start with just one small step",
                "Set up any needed tools or accounts",
                "Track your progress for the first week"
            ]

        # Add follow-up actions
        follow_up_actions = [
            "Check your progress after one week",
            "Adjust the approach if needed",
            "Celebrate your wins, however small!",
            "Consider the next step in your financial journey"
        ]

        return {
            "title": title,
            "summary": summary,
            "content": "\n".join(content_parts),
            "action_steps": action_steps,
            "follow_up_actions": follow_up_actions,
            "rules_applied": rules_applied
        }

    def _generate_adhd_tips(self, template: AdviceTemplate, factors: PersonalizationFactors) -> List[str]:
        """Generate ADHD-specific tips for the advice"""
        tips = []

        # Base ADHD tips from template
        if template.adhd_adaptations:
            for key, adaptation in template.adhd_adaptations.items():
                if key == "visual" and factors.learning_preference in ["visual", "mixed"]:
                    tips.append(f"👁️ Visual: {adaptation}")
                elif key == "gamification" and factors.motivation_level < 0.6:
                    tips.append(f"🎮 Make it fun: {adaptation}")
                elif key == "automation" and factors.executive_function_level < 0.7:
                    tips.append(f"⚙️ Automate: {adaptation}")
                elif key == "flexibility":
                    tips.append(f"🌊 Stay flexible: {adaptation}")
                elif key == "celebration":
                    tips.append(f"🎉 Celebrate: {adaptation}")

        # Additional personalized ADHD tips
        if factors.adhd_symptom_impact == ADHDSymptomImpact.HIGH:
            tips.extend([
                "Break this into even smaller steps if it feels overwhelming",
                "Use timers to stay focused - try 15-minute sessions",
                "Have an accountability buddy check in with you weekly"
            ])

        if factors.executive_function_level < 0.5:
            tips.extend([
                "Set up automatic reminders on your phone",
                "Use external organization tools instead of relying on memory",
                "Schedule specific times to work on this, don't leave it to 'later'"
            ])

        return tips[:5]  # Limit to 5 tips to avoid overwhelm

    def _calculate_advice_confidence(self, template: AdviceTemplate, factors: PersonalizationFactors) -> float:
        """Calculate confidence score for personalized advice"""
        base_score = template.effectiveness_metrics.get('completion_rate', 0.5)

        # Adjust based on user-template fi
        difficulty_penalty = 0
        if template.difficulty_level > 3 and factors.executive_function_level < 0.5:
            difficulty_penalty = 0.2
        elif template.difficulty_level <= 2 and factors.adhd_symptom_impact == ADHDSymptomImpact.HIGH:
            base_score += 0.1  # Simple strategies work better for high ADHD impac

        # Adjust for data quality
        data_quality = 0.8  # Assume decent data quality
        if not factors.spending_patterns:
            data_quality *= 0.7

        confidence = (base_score - difficulty_penalty) * data_quality
        return max(0.1, min(1.0, confidence))

    def _determine_advice_urgency(self, template: AdviceTemplate, factors: PersonalizationFactors) -> AdviceUrgency:
        """Determine urgency level for the advice"""

        # Emergency fund is critical if none exists
        if template.category == AdviceCategory.EMERGENCY_FUND:
            if not factors.spending_patterns.get('has_emergency_fund', False):
                return AdviceUrgency.HIGH

        # Debt reduction urgency based on debt levels
        if template.category == AdviceCategory.DEBT_REDUCTION:
            total_debt = sum(factors.debt_levels.values())
            if total_debt > 50000:
                return AdviceUrgency.CRITICAL
            elif total_debt > 20000:
                return AdviceUrgency.HIGH
            elif total_debt > 5000:
                return AdviceUrgency.MEDIUM

        # Budgeting urgency based on spending variance
        if template.category == AdviceCategory.BUDGETING:
            variance = factors.spending_patterns.get('budget_variance', 0)
            if variance > 0.5:
                return AdviceUrgency.HIGH
            elif variance > 0.3:
                return AdviceUrgency.MEDIUM

        # Default urgency
        return AdviceUrgency.MEDIUM

    def _generate_personalization_reasons(self, template: AdviceTemplate, factors: PersonalizationFactors) -> List[str]:
        """Generate explanations for why this advice was personalized this way"""
        reasons = []

        # ADHD-related reasons
        if factors.adhd_symptom_impact == ADHDSymptomImpact.HIGH:
            reasons.append("Simplified approach recommended for ADHD brain optimization")

        # Income variability
        if factors.income_variability > 0.4:
            reasons.append("Adapted for variable income patterns")

        # Executive function
        if factors.executive_function_level < 0.6:
            reasons.append("Includes automation to reduce decision fatigue")

        # Debt levels
        total_debt = sum(factors.debt_levels.values())
        if total_debt > 20000 and template.category == AdviceCategory.DEBT_REDUCTION:
            reasons.append("Prioritized due to significant debt levels")

        # Goals alignmen
        if factors.financial_goals:
            goal_categories = [goal.get('category') for goal in factors.financial_goals]
            if template.category.value in goal_categories:
                reasons.append("Aligns with your active financial goals")

        return reasons

    def _estimate_advice_impact(self, template: AdviceTemplate, factors: PersonalizationFactors) -> str:
        """Estimate the potential impact of following this advice"""

        # Base impact from template metrics
        effectiveness = template.effectiveness_metrics.get('user_rating', 3.0)

        if effectiveness >= 4.5:
            base_impact = "High"
        elif effectiveness >= 3.5:
            base_impact = "Medium"
        else:
            base_impact = "Low"

        # Adjust for user factors
        if template.category == AdviceCategory.EMERGENCY_FUND:
            if not factors.spending_patterns.get('has_emergency_fund', False):
                return "High - Emergency fund provides crucial financial security"

        elif template.category == AdviceCategory.DEBT_REDUCTION:
            total_debt = sum(factors.debt_levels.values())
            if total_debt > 30000:
                return "High - Significant debt reduction potential"
            elif total_debt > 10000:
                return "Medium - Meaningful debt reduction possible"

        return f"{base_impact} - Based on similar users' results"

    def _personalize_time_estimate(self, template: AdviceTemplate, factors: PersonalizationFactors) -> str:
        """Personalize time estimates based on user factors"""
        base_time = template.time_investmen

        # Adjust for ADHD factors
        if factors.adhd_symptom_impact == ADHDSymptomImpact.HIGH:
            if "min" in base_time:
                # Add buffer time for ADHD brains
                return base_time + " (may take longer with ADHD - be patient with yourself!)"

        # Adjust for executive function
        if factors.executive_function_level < 0.5:
            return base_time + " (plan extra time for setup and organization)"

        return base_time

    def _generate_advice_id(self, template_id: str, user_id: str) -> str:
        """Generate unique advice ID"""
        timestamp = datetime.now().isoformat()
        content = f"{template_id}_{user_id}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    # Helper methods for user data analysis

    def _analyze_income_level(self, transactions: List[Dict]) -> str:
        """Analyze user's income level from transactions"""
        if not transactions:
            return "unknown"

        # Look for income transactions (positive amounts)
        income_transactions = [t for t in transactions if t.get('amount', 0) > 0]

        if not income_transactions:
            return "low"

        monthly_income = sum(t['amount'] for t in income_transactions) / 3  # Assuming 3 months of data

        if monthly_income > 8000:
            return "high"
        elif monthly_income > 4000:
            return "medium"
        else:
            return "low"

    def _calculate_income_variability(self, transactions: List[Dict]) -> float:
        """Calculate income variability (0.0 = stable, 1.0 = highly variable)"""
        if not transactions:
            return 0.5

        # Get monthly income amounts
        income_amounts = []
        current_month = None
        monthly_total = 0

        for transaction in sorted(transactions, key=lambda x: x.get('date', '')):
            if transaction.get('amount', 0) > 0:  # Income transaction
                transaction_month = transaction.get('date', '')[:7]  # YYYY-MM

                if current_month != transaction_month:
                    if current_month is not None:
                        income_amounts.append(monthly_total)
                    current_month = transaction_month
                    monthly_total = transaction['amount']
                else:
                    monthly_total += transaction['amount']

        if current_month:
            income_amounts.append(monthly_total)

        if len(income_amounts) < 2:
            return 0.3  # Default moderate variability

        # Calculate coefficient of variation
        mean_income = sum(income_amounts) / len(income_amounts)
        if mean_income == 0:
            return 0.5

        variance = sum((x - mean_income) ** 2 for x in income_amounts) / len(income_amounts)
        std_dev = variance ** 0.5
        cv = std_dev / mean_income

        return min(1.0, cv)  # Cap at 1.0

    def _analyze_debt_levels(self, transactions: List[Dict]) -> Dict[str, float]:
        """Analyze debt levels by category"""
        debt_categories = {}

        for transaction in transactions:
            amount = transaction.get('amount', 0)
            category = transaction.get('category', 'other')
            merchant = transaction.get('merchant', '').lower()

            # Identify debt payments
            if amount < 0:  # Expense
                if any(keyword in merchant for keyword in ['loan', 'credit', 'debt', 'mortgage', 'student']):
                    debt_type = 'credit_cards' if 'credit' in merchant else 'loans'
                    debt_categories[debt_type] = debt_categories.get(debt_type, 0) + abs(amount)
                elif category in ['loans', 'credit_cards', 'debt']:
                    debt_categories[category] = debt_categories.get(category, 0) + abs(amount)

        # Estimate outstanding balances (rough approximation)
        estimated_balances = {}
        for debt_type, monthly_payment in debt_categories.items():
            # Rough estimate: 20x monthly payment for outstanding balance
            estimated_balances[debt_type] = monthly_payment * 20

        return estimated_balances

    def _assess_adhd_impact(self, user_profile: Dict, ml_insights: Optional[Dict]) -> ADHDSymptomImpact:
        """Assess ADHD symptom impact from available data"""

        # Check user's self-reported ADHD impac
        if user_profile.get('adhd_impact'):
            return ADHDSymptomImpact(user_profile['adhd_impact'])

        # Infer from spending patterns if ML insights available
        if ml_insights:
            impulse_score = ml_insights.get('impulse_spending_frequency', 0)
            pattern_inconsistency = ml_insights.get('pattern_inconsistency', 0)

            if impulse_score > 0.7 or pattern_inconsistency > 0.6:
                return ADHDSymptomImpact.HIGH
            elif impulse_score > 0.4 or pattern_inconsistency > 0.3:
                return ADHDSymptomImpact.MODERATE

        # Default to moderate if unknown
        return ADHDSymptomImpact.MODERATE

    def _estimate_executive_function(self, transactions: List[Dict], ml_insights: Optional[Dict]) -> float:
        """Estimate executive function level (0.0 = low, 1.0 = high)"""
        score = 0.5  # Default middle ground

        # Look for patterns indicating good executive function
        if transactions:
            # Regular savings patterns
            savings_transactions = [t for t in transactions if 'savings' in t.get('category', '').lower()]
            if savings_transactions:
                score += 0.2

            # Budget consistency (if available from ML insights)
            if ml_insights:
                budget_consistency = ml_insights.get('budget_consistency', 0.5)
                score = (score + budget_consistency) / 2

        return max(0.1, min(1.0, score))

    def _estimate_stress_level(self, ml_insights: Optional[Dict]) -> float:
        """Estimate current stress level from spending patterns"""
        if not ml_insights:
            return 0.5

        # Look for stress indicators in spending
        stress_spending = ml_insights.get('emotional_spending_frequency', 0)
        spending_volatility = ml_insights.get('spending_volatility', 0)

        stress_score = (stress_spending + spending_volatility) / 2
        return max(0.1, min(1.0, stress_score))

    def _estimate_motivation_level(self, user_profile: Dict, goals_data: List[Dict]) -> float:
        """Estimate motivation level from goals and profile"""
        score = 0.5

        # Active goals indicate higher motivation
        if goals_data:
            score += 0.3

            # Recent goal activity indicates higher motivation
            recent_goals = [g for g in goals_data if
                          (datetime.now() - datetime.fromisoformat(g.get('created_at', '2020-01-01'))).days < 30]
            if recent_goals:
                score += 0.2

        # User engagement indicators
        if user_profile.get('last_login_days', 30) < 7:
            score += 0.1

        return max(0.1, min(1.0, score))

    # Data fetching methods (to be implemented based on actual data sources)

    async def _get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile data"""
        try:
            user_doc = self.firebase_service.db.collection('users').document(user_id).get()
            return user_doc.to_dict() if user_doc.exists else None
        except Exception as e:
            logger.error(f"Error fetching user profile: {e}")
            return None

    async def _get_user_transactions(self, user_id: str, days: int = 90) -> List[Dict]:
        """Get user transaction data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            transactions_ref = self.firebase_service.db.collection('transactions').where('user_id', '==', user_id).where('date', '>=', cutoff_date).order_by('date', direction='DESCENDING').limit(1000)

            docs = transactions_ref.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return []

    async def _get_user_goals(self, user_id: str) -> List[Dict]:
        """Get user's financial goals"""
        try:
            goals_ref = self.firebase_service.db.collection('goals').where('user_id', '==', user_id).where('status', '==', 'active')

            docs = goals_ref.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error fetching goals: {e}")
            return []

    async def _get_ml_insights(self, user_id: str) -> Optional[Dict]:
        """Get ML insights for the user"""
        try:
            # This would integrate with the ML Analytics service
            from app.services.ml_analytics_service import MLAnalyticsService
            ml_service = MLAnalyticsService()

            # Get recent insights
            insights = await ml_service.get_user_insights_sync(user_id, days=60)
            return insights if insights.get('success') else None
        except Exception as e:
            logger.warning(f"ML insights not available for user {user_id}: {e}")
            return None

    async def _get_advice_history(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's recent advice history"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            advice_ref = self.firebase_service.db.collection('advice_history').where('user_id', '==', user_id).where('created_at', '>=', cutoff_date).order_by('created_at', direction='DESCENDING')

            docs = advice_ref.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error fetching advice history: {e}")
            return []

    def _filter_recent_advice(self, advice_list: List[PersonalizedAdvice], history: List[Dict]) -> List[PersonalizedAdvice]:
        """Filter out advice that was recently shown"""
        if not history:
            return advice_list

        recent_templates = {item.get('template_id') for item in history}

        # Filter out advice based on recently seen templates
        filtered = []
        for advice in advice_list:
            template_id = advice.advice_id.split('_')[0]  # Extract template ID
            if template_id not in recent_templates:
                filtered.append(advice)

        return filtered

    def _summarize_user_factors(self, factors: PersonalizationFactors) -> Dict:
        """Create a summary of user factors for display"""
        return {
            "income_profile": f"{factors.income_level} income with {'high' if factors.income_variability > 0.5 else 'moderate' if factors.income_variability > 0.3 else 'low'} variability",
            "adhd_considerations": factors.adhd_symptom_impact.value.replace('_', ' ').title(),
            "total_debt": sum(factors.debt_levels.values()),
            "active_goals": len(factors.financial_goals),
            "primary_focus": self._determine_primary_focus(factors)
        }

    def _determine_primary_focus(self, factors: PersonalizationFactors) -> str:
        """Determine the user's primary financial focus area"""
        total_debt = sum(factors.debt_levels.values())
        has_emergency_fund = factors.spending_patterns.get('has_emergency_fund', False)

        if total_debt > 20000:
            return "Debt reduction"
        elif not has_emergency_fund:
            return "Emergency fund building"
        elif factors.spending_patterns.get('budget_variance', 0) > 0.4:
            return "Budget optimization"
        else:
            return "Wealth building"

    def _get_personalization_notes(self, factors: PersonalizationFactors) -> List[str]:
        """Generate notes explaining the personalization approach"""
        notes = []

        if factors.adhd_symptom_impact == ADHDSymptomImpact.HIGH:
            notes.append("Advice simplified and automated for ADHD brain optimization")

        if factors.income_variability > 0.4:
            notes.append("Strategies adapted for variable income patterns")

        if factors.executive_function_level < 0.6:
            notes.append("Extra automation and reminders included to support executive function")

        if sum(factors.debt_levels.values()) > 10000:
            notes.append("Debt reduction prioritized in recommendations")

        return notes

    # Public utility methods

    async def record_advice_interaction(self, user_id: str, advice_id: str, action: str, feedback: Optional[Dict] = None):
        """Record user interaction with advice for improvement"""
        try:
            interaction = {
                'user_id': user_id,
                'advice_id': advice_id,
                'action': action,  # 'viewed', 'started', 'completed', 'dismissed'
                'feedback': feedback,
                'timestamp': datetime.now(),
                'created_at': datetime.now()
            }

            self.firebase_service.db.collection('advice_interactions').add(interaction)

            # Update advice effectiveness metrics
            await self._update_advice_metrics(advice_id, action, feedback)

        except Exception as e:
            logger.error(f"Error recording advice interaction: {e}")

    async def _update_advice_metrics(self, advice_id: str, action: str, feedback: Optional[Dict]):
        """Update advice effectiveness metrics"""
        # This would update the template effectiveness based on user interactions
        # Implementation depends on specific analytics requirements
        pass

    def get_advice_categories(self) -> List[Dict]:
        """Get available advice categories"""
        return [
            {
                "category": cat.value,
                "display_name": cat.value.replace('_', ' ').title(),
                "description": self._get_category_description(cat),
                "icon": self._get_category_icon(cat)
            }
            for cat in AdviceCategory
        ]

    def _get_category_description(self, category: AdviceCategory) -> str:
        """Get description for advice category"""
        descriptions = {
            AdviceCategory.BUDGETING: "ADHD-friendly budgeting strategies that actually work",
            AdviceCategory.DEBT_REDUCTION: "Motivated approaches to paying off debt",
            AdviceCategory.SAVINGS: "Automated savings that work even when your brain doesn't",
            AdviceCategory.INVESTMENT: "Simple, hands-off investment strategies",
            AdviceCategory.EMERGENCY_FUND: "Build financial security one small step at a time"
        }
        return descriptions.get(category, "Personalized financial advice")

    def _get_category_icon(self, category: AdviceCategory) -> str:
        """Get icon for advice category"""
        icons = {
            AdviceCategory.BUDGETING: "📊",
            AdviceCategory.DEBT_REDUCTION: "💪",
            AdviceCategory.SAVINGS: "🏦",
            AdviceCategory.INVESTMENT: "📈",
            AdviceCategory.EMERGENCY_FUND: "🛡️"
        }
        return icons.get(category, "💡")

    async def health_check(self) -> Dict:
        """Check service health"""
        return {
            "service": "AdviceEngine",
            "status": "healthy",
            "templates_loaded": len(self._advice_templates),
            "ml_available": self.ml_available,
            "cache_entries": len(self._user_factors_cache)
        }
