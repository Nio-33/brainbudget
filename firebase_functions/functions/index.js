/**
 * Firebase Cloud Functions for BrainBudget Notification System
 * 
 * These functions trigger intelligent, ADHD-friendly notifications based on:
 * - Transaction analysis and spending patterns
 * - Budget thresholds and goals
 * - Scheduled summaries and encouragements
 * - Real-time spending alerts
 */

const functions = require('firebase-functions');
const admin = require('firebase-admin');
const { Timestamp } = require('firebase-admin/firestore');

// Initialize Firebase Admin
admin.initializeApp();

const db = admin.firestore();

/**
 * Trigger notification when a new transaction is added
 */
exports.onTransactionAdded = functions.firestore
    .document('user_transactions/{transactionId}')
    .onCreate(async (snap, context) => {
        try {
            const transaction = snap.data();
            const userId = transaction.user_id;
            
            console.log(`New transaction for user ${userId}: ${transaction.description} - $${transaction.amount}`);
            
            // Analyze spending patterns
            await analyzeSpendingPatterns(userId, transaction);
            
            // Check budget thresholds
            await checkBudgetThresholds(userId, transaction);
            
            // Check for unusual patterns
            await checkUnusualPatterns(userId, transaction);
            
        } catch (error) {
            console.error('Error processing new transaction:', error);
        }
    });

/**
 * Daily scheduled function to send encouragements and check goals
 */
exports.dailyNotificationCheck = functions.pubsub
    .schedule('0 9 * * *') // 9 AM daily
    .timeZone('America/New_York') // Default timezone
    .onRun(async (context) => {
        try {
            console.log('Running daily notification check...');
            
            // Get all active users
            const usersSnapshot = await db.collection('users')
                .where('active', '==', true)
                .get();
            
            const promises = [];
            
            usersSnapshot.forEach(userDoc => {
                const userId = userDoc.id;
                promises.push(processDailyNotifications(userId));
            });
            
            await Promise.all(promises);
            console.log(`Processed daily notifications for ${promises.length} users`);
            
        } catch (error) {
            console.error('Error in daily notification check:', error);
        }
    });

/**
 * Weekly summary function (Sundays at 10 AM)
 */
exports.weeklySummary = functions.pubsub
    .schedule('0 10 * * 0') // Sunday 10 AM
    .timeZone('America/New_York')
    .onRun(async (context) => {
        try {
            console.log('Generating weekly summaries...');
            
            const usersSnapshot = await db.collection('users').get();
            const promises = [];
            
            usersSnapshot.forEach(userDoc => {
                const userId = userDoc.id;
                promises.push(generateWeeklySummary(userId));
            });
            
            await Promise.all(promises);
            console.log(`Generated weekly summaries for ${promises.length} users`);
            
        } catch (error) {
            console.error('Error generating weekly summaries:', error);
        }
    });

/**
 * Cleanup old notification logs (monthly)
 */
exports.cleanupNotificationLogs = functions.pubsub
    .schedule('0 2 1 * *') // 1st of month at 2 AM
    .onRun(async (context) => {
        try {
            const cutoffDate = new Date();
            cutoffDate.setMonth(cutoffDate.getMonth() - 3); // Keep 3 months
            
            const oldLogsQuery = db.collection('notification_logs')
                .where('timestamp', '<', Timestamp.fromDate(cutoffDate));
            
            const snapshot = await oldLogsQuery.get();
            
            const batch = db.batch();
            snapshot.docs.forEach(doc => {
                batch.delete(doc.ref);
            });
            
            await batch.commit();
            console.log(`Cleaned up ${snapshot.size} old notification logs`);
            
        } catch (error) {
            console.error('Error cleaning up notification logs:', error);
        }
    });

/**
 * Analyze spending patterns for a user and transaction
 */
async function analyzeSpendingPatterns(userId, transaction) {
    try {
        // Get user's recent transactions (last 30 days)
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        
        const recentTransactions = await db.collection('user_transactions')
            .where('user_id', '==', userId)
            .where('date', '>=', thirtyDaysAgo.toISOString().split('T')[0])
            .get();
        
        if (recentTransactions.size < 5) {
            return; // Need minimum transactions for analysis
        }
        
        const transactions = recentTransactions.docs.map(doc => doc.data());
        
        // Check for spending spikes
        const todaySpending = transactions
            .filter(t => t.date === transaction.date)
            .reduce((sum, t) => sum + t.amount, 0);
        
        const avgDailySpending = calculateAverageDaily(transactions);
        
        // Alert if today's spending is significantly higher
        if (todaySpending > avgDailySpending * 2 && todaySpending > 50) {
            await sendNotification(userId, 'unusual_pattern', 'spending_spike', {
                amount: todaySpending.toFixed(2),
                category: transaction.category || 'general',
                date: transaction.date
            });
        }
        
    } catch (error) {
        console.error('Error analyzing spending patterns:', error);
    }
}

/**
 * Check if user has exceeded budget thresholds
 */
async function checkBudgetThresholds(userId, transaction) {
    try {
        // Get user's budgets
        const budgetDoc = await db.collection('user_budgets').doc(userId).get();
        
        if (!budgetDoc.exists) {
            return;
        }
        
        const budgets = budgetDoc.data().budgets || {};
        const category = transaction.category || 'Other';
        const categoryBudget = budgets[category];
        
        if (!categoryBudget || !categoryBudget.limit) {
            return;
        }
        
        // Calculate current month spending for this category
        const currentMonth = new Date().toISOString().substring(0, 7); // YYYY-MM
        
        const monthlyTransactions = await db.collection('user_transactions')
            .where('user_id', '==', userId)
            .where('category', '==', category)
            .where('date', '>=', `${currentMonth}-01`)
            .where('date', '<=', `${currentMonth}-31`)
            .get();
        
        const totalSpent = monthlyTransactions.docs
            .map(doc => doc.data().amount)
            .reduce((sum, amount) => sum + amount, 0);
        
        const percentage = Math.round((totalSpent / categoryBudget.limit) * 100);
        
        // Send alerts at different thresholds
        const lastAlertDoc = await db.collection('user_budget_alerts')
            .doc(`${userId}_${category}_${currentMonth}`)
            .get();
        
        const lastAlertPercentage = lastAlertDoc.exists ? 
            lastAlertDoc.data().last_percentage : 0;
        
        // Only send alert if we've crossed a new threshold
        if (percentage >= 80 && lastAlertPercentage < 80) {
            await sendNotification(userId, 'spending_alert', 'approaching', {
                category: category,
                percentage: percentage,
                amount_spent: totalSpent.toFixed(2),
                budget_limit: categoryBudget.limit.toFixed(2)
            });
            
            // Update last alert
            await db.collection('user_budget_alerts')
                .doc(`${userId}_${category}_${currentMonth}`)
                .set({
                    last_percentage: percentage,
                    last_alert_date: new Date(),
                    category: category,
                    user_id: userId
                });
        } else if (percentage >= 100 && lastAlertPercentage < 100) {
            await sendNotification(userId, 'spending_alert', 'exceeded', {
                category: category,
                percentage: percentage,
                amount_spent: totalSpent.toFixed(2),
                budget_limit: categoryBudget.limit.toFixed(2)
            });
            
            await db.collection('user_budget_alerts')
                .doc(`${userId}_${category}_${currentMonth}`)
                .set({
                    last_percentage: percentage,
                    last_alert_date: new Date(),
                    category: category,
                    user_id: userId
                });
        }
        
    } catch (error) {
        console.error('Error checking budget thresholds:', error);
    }
}

/**
 * Check for unusual spending patterns
 */
async function checkUnusualPatterns(userId, transaction) {
    try {
        // Check for new merchants
        const merchantTransactions = await db.collection('user_transactions')
            .where('user_id', '==', userId)
            .where('merchant', '==', transaction.merchant)
            .limit(1)
            .get();
        
        // If this is the first transaction with this merchant
        if (merchantTransactions.size === 1) { // Only the current transaction
            await sendNotification(userId, 'unusual_pattern', 'new_merchant', {
                merchant: transaction.merchant || transaction.description,
                category: transaction.category || 'general',
                amount: transaction.amount.toFixed(2)
            });
        }
        
        // Check for unusually large transactions
        const recentSimilarTransactions = await db.collection('user_transactions')
            .where('user_id', '==', userId)
            .where('category', '==', transaction.category)
            .orderBy('date', 'desc')
            .limit(20)
            .get();
        
        if (recentSimilarTransactions.size >= 5) {
            const amounts = recentSimilarTransactions.docs
                .map(doc => doc.data().amount)
                .filter(amount => amount !== transaction.amount); // Exclude current
            
            const avgAmount = amounts.reduce((sum, amount) => sum + amount, 0) / amounts.length;
            
            // Alert if this transaction is significantly larger
            if (transaction.amount > avgAmount * 3 && transaction.amount > 100) {
                await sendNotification(userId, 'unusual_pattern', 'large_transaction', {
                    amount: transaction.amount.toFixed(2),
                    category: transaction.category || 'general',
                    avg_amount: avgAmount.toFixed(2)
                });
            }
        }
        
    } catch (error) {
        console.error('Error checking unusual patterns:', error);
    }
}

/**
 * Process daily notifications for a user
 */
async function processDailyNotifications(userId) {
    try {
        // Check user notification preferences
        const prefsDoc = await db.collection('user_preferences').doc(userId).get();
        
        if (!prefsDoc.exists) {
            return;
        }
        
        const notificationPrefs = prefsDoc.data().notifications || {};
        
        if (!notificationPrefs.enabled) {
            return;
        }
        
        // Check if we should send encouragement
        const encouragementEnabled = notificationPrefs.types?.encouragement?.enabled !== false;
        
        if (encouragementEnabled) {
            // Get user's recent activity to determine encouragement type
            const recentGoals = await checkRecentGoals(userId);
            
            if (recentGoals.achievements > 0) {
                await sendNotification(userId, 'encouragement', 'achievement', {
                    achievements: recentGoals.achievements
                });
            } else if (recentGoals.streak > 0) {
                await sendNotification(userId, 'goal_achievement', 'streak', {
                    days: recentGoals.streak
                });
            } else {
                await sendNotification(userId, 'encouragement', 'daily');
            }
        }
        
        // Check for goal achievements
        await checkGoalAchievements(userId);
        
    } catch (error) {
        console.error(`Error processing daily notifications for user ${userId}:`, error);
    }
}

/**
 * Generate weekly summary for a user
 */
async function generateWeeklySummary(userId) {
    try {
        const prefsDoc = await db.collection('user_preferences').doc(userId).get();
        
        if (!prefsDoc.exists) {
            return;
        }
        
        const notificationPrefs = prefsDoc.data().notifications || {};
        
        if (!notificationPrefs.enabled || !notificationPrefs.types?.weekly_summary?.enabled) {
            return;
        }
        
        // Get last week's transactions
        const lastWeek = new Date();
        lastWeek.setDate(lastWeek.getDate() - 7);
        
        const weekTransactions = await db.collection('user_transactions')
            .where('user_id', '==', userId)
            .where('date', '>=', lastWeek.toISOString().split('T')[0])
            .get();
        
        if (weekTransactions.size === 0) {
            return;
        }
        
        // Calculate summary statistics
        const transactions = weekTransactions.docs.map(doc => doc.data());
        const totalSpent = transactions.reduce((sum, t) => sum + t.amount, 0);
        
        // Calculate budget success rate
        const successRate = await calculateBudgetSuccessRate(userId, transactions);
        
        // Send appropriate weekly summary
        const templateKey = successRate >= 70 ? 'positive' : 'encouraging';
        
        await sendNotification(userId, 'weekly_summary', templateKey, {
            success_rate: Math.round(successRate),
            total_spent: totalSpent.toFixed(2),
            transaction_count: transactions.length
        });
        
    } catch (error) {
        console.error(`Error generating weekly summary for user ${userId}:`, error);
    }
}

/**
 * Send a notification via the Python notification service
 */
async function sendNotification(userId, type, templateKey, data = {}) {
    try {
        // Log the notification trigger
        await db.collection('notification_triggers').add({
            user_id: userId,
            type: type,
            template_key: templateKey,
            data: data,
            timestamp: new Date(),
            source: 'cloud_function'
        });
        
        console.log(`Triggered notification for user ${userId}: ${type}.${templateKey}`);
        
        // In a real implementation, you would call your Python notification service
        // This could be done via HTTP request to your Flask API or PubSub message
        
    } catch (error) {
        console.error('Error sending notification:', error);
    }
}

/**
 * Helper functions
 */

function calculateAverageDaily(transactions) {
    const dailyTotals = {};
    
    transactions.forEach(t => {
        if (!dailyTotals[t.date]) {
            dailyTotals[t.date] = 0;
        }
        dailyTotals[t.date] += t.amount;
    });
    
    const totals = Object.values(dailyTotals);
    return totals.length > 0 ? totals.reduce((sum, total) => sum + total, 0) / totals.length : 0;
}

async function checkRecentGoals(userId) {
    // Simplified goal checking - would be more complex in real implementation
    try {
        const goalsDoc = await db.collection('user_goals').doc(userId).get();
        
        if (!goalsDoc.exists) {
            return { achievements: 0, streak: 0 };
        }
        
        // This would check actual goal progress
        return { achievements: 0, streak: Math.floor(Math.random() * 7) }; // Mock data
        
    } catch (error) {
        console.error('Error checking recent goals:', error);
        return { achievements: 0, streak: 0 };
    }
}

async function checkGoalAchievements(userId) {
    try {
        // Check if user has achieved any goals recently
        const goalsDoc = await db.collection('user_goals').doc(userId).get();
        
        if (goalsDoc.exists) {
            const goals = goalsDoc.data().goals || {};
            
            // Check each goal for completion
            for (const [goalId, goal] of Object.entries(goals)) {
                if (goal.status === 'completed' && !goal.celebration_sent) {
                    await sendNotification(userId, 'goal_achievement', 'milestone', {
                        goal_name: goal.name || 'Your goal'
                    });
                    
                    // Mark celebration as sent
                    await db.collection('user_goals').doc(userId).update({
                        [`goals.${goalId}.celebration_sent`]: true
                    });
                }
            }
        }
        
    } catch (error) {
        console.error('Error checking goal achievements:', error);
    }
}

async function calculateBudgetSuccessRate(userId, transactions) {
    try {
        // Get user's budgets
        const budgetDoc = await db.collection('user_budgets').doc(userId).get();
        
        if (!budgetDoc.exists) {
            return 50; // Default middle success rate
        }
        
        const budgets = budgetDoc.data().budgets || {};
        
        // Calculate success rate based on staying within budgets
        let categorySuccesses = 0;
        let totalCategories = 0;
        
        for (const [category, budget] of Object.entries(budgets)) {
            if (!budget.limit) continue;
            
            const categorySpending = transactions
                .filter(t => t.category === category)
                .reduce((sum, t) => sum + t.amount, 0);
            
            totalCategories++;
            if (categorySpending <= budget.limit) {
                categorySuccesses++;
            }
        }
        
        return totalCategories > 0 ? (categorySuccesses / totalCategories) * 100 : 75;
        
    } catch (error) {
        console.error('Error calculating budget success rate:', error);
        return 50;
    }
}