/**
 * BrainBudget Notification System - Frontend
 * 
 * User-friendly notification management with:
 * - Gentle permission requests with clear benefits
 * - Service worker integration for background notifications
 * - In-app notification center
 * - User-friendly notification settings
 */

class BrainBudgetNotifications {
    constructor() {
        this.fcmToken = null;
        this.isSupported = this.checkSupport();
        this.registrationAttempted = false;
        this.notificationCenter = null;
        
        // Firebase config (will be injected from backend)
        this.firebaseConfig = window.firebaseConfig || {};
        
        this.init();
    }
    
    init() {
        if (!this.isSupported) {
            console.log('Notifications not supported in this browser');
            return;
        }
        
        // Initialize notification center UI
        this.initNotificationCenter();
        
        // Check current permission status
        this.checkPermissionStatus();
        
        // Set up service worker message handling
        this.setupServiceWorkerMessaging();
        
        // Initialize Firebase messaging if available
        if (window.firebase && window.firebase.messaging) {
            this.initFirebaseMessaging();
        }
        
        // Load user notification preferences
        this.loadNotificationPreferences();
    }
    
    checkSupport() {
        return 'Notification' in window && 
               'serviceWorker' in navigator && 
               'PushManager' in window;
    }
    
    checkPermissionStatus() {
        if (!this.isSupported) return;
        
        const permission = Notification.permission;
        
        switch (permission) {
            case 'granted':
                console.log('Notifications are enabled');
                this.showNotificationStatus('enabled');
                break;
            case 'denied':
                console.log('Notifications are blocked');
                this.showNotificationStatus('blocked');
                break;
            case 'default':
                console.log('Notification permission not requested');
                this.showNotificationStatus('not-requested');
                break;
        }
    }
    
    async requestPermission() {
        if (!this.isSupported) {
            this.showNotificationError('Your browser doesn\'t support notifications. That\'s okay - you can still use BrainBudget without them!');
            return false;
        }
        
        if (this.registrationAttempted) {
            return false; // Don't spam permission requests
        }
        
        this.registrationAttempted = true;
        
        try {
            // Show user-friendly explanation modal first
            const userConsent = await this.showPermissionExplanation();
            
            if (!userConsent) {
                return false;
            }
            
            // Request permission
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                this.showSuccessMessage('🎉 Great! You\'ll get gentle reminders to help manage your money.');
                await this.registerForNotifications();
                return true;
            } else if (permission === 'denied') {
                this.showNotificationError('No worries! You can still use all of BrainBudget\'s features. You can always enable notifications later in your browser settings if you change your mind.');
                return false;
            }
            
        } catch (error) {
            console.error('Error requesting notification permission:', error);
            this.showNotificationError('Something went wrong with notifications, but don\'t worry - BrainBudget works perfectly without them!');
        }
        
        return false;
    }
    
    showPermissionExplanation() {
        return new Promise((resolve) => {
            // Create user-friendly explanation modal
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4';
            modal.innerHTML = `
                <div class="bg-white rounded-2xl p-8 max-w-md mx-auto shadow-2xl transform">
                    <div class="text-center mb-6">
                        <div class="w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                            <span class="text-2xl">🔔</span>
                        </div>
                        <h3 class="text-2xl font-bold text-text-primary mb-3">
                            Gentle Financial Reminders
                        </h3>
                        <p class="text-text-secondary leading-relaxed">
                            Let BrainBudget send you kind, helpful notifications about your money. Perfect for busy people who sometimes forget things!
                        </p>
                    </div>
                    
                    <div class="bg-primary-50 rounded-xl p-4 mb-6">
                        <h4 class="font-semibold text-text-primary mb-3 flex items-center">
                            <span class="mr-2">✨</span> What you'll get:
                        </h4>
                        <ul class="text-sm text-text-secondary space-y-2">
                            <li class="flex items-center">
                                <span class="text-success-500 mr-2">💚</span>
                                Gentle budget reminders (not scary alerts!)
                            </li>
                            <li class="flex items-center">
                                <span class="text-success-500 mr-2">🎯</span>
                                Celebration when you hit your goals
                            </li>
                            <li class="flex items-center">
                                <span class="text-success-500 mr-2">📊</span>
                                Weekly spending summaries
                            </li>
                            <li class="flex items-center">
                                <span class="text-success-500 mr-2">🌟</span>
                                Encouraging messages on tough days
                            </li>
                        </ul>
                    </div>
                    
                    <div class="bg-orange-50 rounded-xl p-4 mb-6">
                        <p class="text-sm text-orange-800 flex items-start">
                            <span class="text-orange-500 mr-2 mt-0.5">🛡️</span>
                            <span><strong>Privacy Promise:</strong> We'll never spam you or sell your data. You can change your mind anytime in settings.</span>
                        </p>
                    </div>
                    
                    <div class="flex flex-col sm:flex-row gap-3">
                        <button id="enable-notifications" class="flex-1 bg-primary-500 text-white font-semibold py-3 px-6 rounded-xl hover:bg-primary-600 gentle-transition">
                            Yes, help me stay on track! 🎯
                        </button>
                        <button id="skip-notifications" class="flex-1 border-2 border-gray-200 text-text-secondary font-semibold py-3 px-6 rounded-xl hover:bg-gray-50 gentle-transition">
                            Maybe later
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Handle button clicks
            modal.querySelector('#enable-notifications').onclick = () => {
                document.body.removeChild(modal);
                resolve(true);
            };
            
            modal.querySelector('#skip-notifications').onclick = () => {
                document.body.removeChild(modal);
                resolve(false);
            };
            
            // Close on backdrop click
            modal.onclick = (e) => {
                if (e.target === modal) {
                    document.body.removeChild(modal);
                    resolve(false);
                }
            };
        });
    }
    
    async registerForNotifications() {
        try {
            // Register service worker
            const registration = await navigator.serviceWorker.register('/sw.js');
            console.log('Service Worker registered:', registration);
            
            // Initialize Firebase messaging
            if (window.firebase && window.firebase.messaging) {
                const messaging = firebase.messaging();
                
                // Set VAPID key
                if (this.firebaseConfig.vapidKey) {
                    messaging.usePublicVapidKey(this.firebaseConfig.vapidKey);
                }
                
                // Get FCM token
                const token = await messaging.getToken({ 
                    serviceWorkerRegistration: registration 
                });
                
                if (token) {
                    console.log('FCM Token:', token);
                    this.fcmToken = token;
                    await this.sendTokenToServer(token);
                    
                    // Set up token refresh
                    messaging.onTokenRefresh(async () => {
                        const refreshedToken = await messaging.getToken();
                        await this.sendTokenToServer(refreshedToken);
                    });
                    
                    // Handle foreground messages
                    messaging.onMessage((payload) => {
                        this.handleForegroundNotification(payload);
                    });
                }
            }
            
        } catch (error) {
            console.error('Error registering for notifications:', error);
            this.showNotificationError('Had a little trouble setting up notifications, but everything else works great!');
        }
    }
    
    async sendTokenToServer(token) {
        try {
            const response = await fetch('/api/notifications/register-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                },
                body: JSON.stringify({
                    token: token,
                    device_info: {
                        userAgent: navigator.userAgent,
                        platform: navigator.platform,
                        language: navigator.language,
                        timestamp: new Date().toISOString()
                    }
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('FCM token registered successfully');
            } else {
                throw new Error(result.error || 'Failed to register token');
            }
            
        } catch (error) {
            console.error('Error sending token to server:', error);
        }
    }
    
    async getAuthToken() {
        // This would get the current user's Firebase auth token
        if (window.firebase && window.firebase.auth && firebase.auth().currentUser) {
            return await firebase.auth().currentUser.getIdToken();
        }
        return null;
    }
    
    handleForegroundNotification(payload) {
        console.log('Foreground notification:', payload);
        
        // Show in-app notification
        this.showInAppNotification({
            title: payload.notification?.title || payload.data?.title,
            body: payload.notification?.body || payload.data?.body,
            action: payload.data?.action,
            type: payload.data?.type
        });
        
        // Add to notification center
        this.addToNotificationCenter(payload);
    }
    
    showInAppNotification(notification) {
        // Create floating notification
        const notificationEl = document.createElement('div');
        notificationEl.className = `
            fixed top-4 right-4 bg-white rounded-2xl shadow-2xl p-6 max-w-sm z-50 
            transform translate-x-full transition-transform duration-500 ease-out
            border-l-4 border-primary-500
        `;
        
        notificationEl.innerHTML = `
            <div class="flex items-start space-x-3">
                <div class="flex-shrink-0">
                    <div class="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center">
                        <span class="text-white text-lg">🧠</span>
                    </div>
                </div>
                <div class="flex-1 min-w-0">
                    <h4 class="font-semibold text-text-primary mb-1 text-sm">
                        ${notification.title}
                    </h4>
                    <p class="text-text-secondary text-sm leading-relaxed">
                        ${notification.body}
                    </p>
                    ${notification.action ? `
                        <button class="mt-3 text-primary-500 hover:text-primary-600 text-sm font-medium gentle-transition">
                            ${notification.action}
                        </button>
                    ` : ''}
                </div>
                <button class="flex-shrink-0 text-text-muted hover:text-text-secondary gentle-transition" onclick="this.closest('.fixed').remove()">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        
        document.body.appendChild(notificationEl);
        
        // Animate in
        requestAnimationFrame(() => {
            notificationEl.style.transform = 'translateX(0)';
        });
        
        // Auto-remove after 8 seconds (longer for comfortable reading)
        setTimeout(() => {
            if (notificationEl.parentNode) {
                notificationEl.style.transform = 'translateX(full)';
                setTimeout(() => {
                    if (notificationEl.parentNode) {
                        notificationEl.remove();
                    }
                }, 500);
            }
        }, 8000);
    }
    
    initNotificationCenter() {
        // Create notification center button in navigation
        const nav = document.querySelector('nav .hidden.md\\:flex');
        if (nav) {
            const notificationButton = document.createElement('button');
            notificationButton.className = 'relative text-text-secondary hover:text-primary-500 gentle-transition focus-ring rounded p-2';
            notificationButton.innerHTML = `
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
                </svg>
                <span id="notification-badge" class="absolute -top-1 -right-1 bg-primary-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center hidden">0</span>
            `;
            
            notificationButton.onclick = () => this.toggleNotificationCenter();
            nav.appendChild(notificationButton);
        }
        
        this.createNotificationCenter();
    }
    
    createNotificationCenter() {
        const centerHTML = `
            <div id="notification-center" class="fixed inset-y-0 right-0 w-80 bg-white shadow-2xl transform translate-x-full transition-transform duration-300 z-40 hidden">
                <div class="h-full flex flex-col">
                    <!-- Header -->
                    <div class="bg-gradient-to-r from-primary-500 to-primary-600 p-6 text-white">
                        <div class="flex items-center justify-between">
                            <h3 class="font-semibold flex items-center">
                                <span class="mr-2">🔔</span>
                                Your Updates
                            </h3>
                            <button id="close-notification-center" class="text-primary-100 hover:text-white gentle-transition">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                            </button>
                        </div>
                        <p class="text-primary-100 text-sm mt-1">Gentle reminders for your financial journey</p>
                    </div>
                    
                    <!-- Content -->
                    <div class="flex-1 overflow-y-auto">
                        <div id="notification-list" class="p-4 space-y-3">
                            <div class="text-center text-text-muted py-8">
                                <div class="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                                    <span class="text-2xl">💫</span>
                                </div>
                                <p class="font-medium mb-2">All caught up!</p>
                                <p class="text-sm">No new notifications right now.</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Footer -->
                    <div class="border-t border-gray-100 p-4">
                        <div class="flex space-x-2">
                            <button id="mark-all-read" class="flex-1 text-sm text-text-secondary hover:text-primary-500 gentle-transition">
                                Mark all read
                            </button>
                            <button id="notification-settings" class="flex-1 text-sm text-primary-500 hover:text-primary-600 gentle-transition">
                                Settings
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Backdrop -->
            <div id="notification-backdrop" class="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 hidden"></div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', centerHTML);
        
        // Set up event listeners
        document.getElementById('close-notification-center').onclick = () => this.closeNotificationCenter();
        document.getElementById('notification-backdrop').onclick = () => this.closeNotificationCenter();
        document.getElementById('notification-settings').onclick = () => this.openNotificationSettings();
        document.getElementById('mark-all-read').onclick = () => this.markAllNotificationsRead();
    }
    
    toggleNotificationCenter() {
        const center = document.getElementById('notification-center');
        const backdrop = document.getElementById('notification-backdrop');
        
        if (center.classList.contains('hidden')) {
            center.classList.remove('hidden');
            backdrop.classList.remove('hidden');
            requestAnimationFrame(() => {
                center.style.transform = 'translateX(0)';
            });
            this.loadNotificationHistory();
        } else {
            this.closeNotificationCenter();
        }
    }
    
    closeNotificationCenter() {
        const center = document.getElementById('notification-center');
        const backdrop = document.getElementById('notification-backdrop');
        
        center.style.transform = 'translateX(full)';
        setTimeout(() => {
            center.classList.add('hidden');
            backdrop.classList.add('hidden');
        }, 300);
    }
    
    async loadNotificationHistory() {
        try {
            const response = await fetch('/api/notifications/history?limit=20', {
                headers: {
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                }
            });
            
            const data = await response.json();
            
            if (data.notifications) {
                this.displayNotifications(data.notifications);
            }
            
        } catch (error) {
            console.error('Error loading notification history:', error);
        }
    }
    
    displayNotifications(notifications) {
        const listEl = document.getElementById('notification-list');
        
        if (notifications.length === 0) {
            listEl.innerHTML = `
                <div class="text-center text-text-muted py-8">
                    <div class="w-16 h-16 bg-primary-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <span class="text-2xl">💫</span>
                    </div>
                    <p class="font-medium mb-2">All caught up!</p>
                    <p class="text-sm">No notifications yet.</p>
                </div>
            `;
            return;
        }
        
        const notificationsHTML = notifications.map(notification => `
            <div class="bg-gray-50 rounded-xl p-4 hover:bg-gray-100 gentle-transition">
                <div class="flex items-start space-x-3">
                    <div class="flex-shrink-0">
                        <div class="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center">
                            ${this.getNotificationIcon(notification.type)}
                        </div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-text-primary mb-1">
                            ${notification.template_key || notification.type}
                        </p>
                        <p class="text-xs text-text-secondary">
                            ${this.formatNotificationTime(notification.timestamp)}
                        </p>
                    </div>
                </div>
            </div>
        `).join('');
        
        listEl.innerHTML = notificationsHTML;
    }
    
    getNotificationIcon(type) {
        const icons = {
            'spending_alert': '💰',
            'unusual_pattern': '🔍', 
            'goal_achievement': '🎉',
            'weekly_summary': '📊',
            'bill_reminder': '📅',
            'encouragement': '💜'
        };
        return icons[type] || '📱';
    }
    
    formatNotificationTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 60) {
            return `${minutes}m ago`;
        } else if (hours < 24) {
            return `${hours}h ago`;
        } else {
            return `${days}d ago`;
        }
    }
    
    setupServiceWorkerMessaging() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', event => {
                if (event.data && event.data.type === 'NOTIFICATION_CLICKED') {
                    // Handle notification clicks
                    this.handleNotificationClick(event.data.notification);
                }
            });
        }
    }
    
    handleNotificationClick(notification) {
        // Navigate to relevant page based on notification type
        const routes = {
            'spending_alert': '/dashboard',
            'goal_achievement': '/dashboard',
            'weekly_summary': '/dashboard',
            'unusual_pattern': '/dashboard',
            'encouragement': '/dashboard'
        };
        
        const route = routes[notification.type] || '/dashboard';
        window.location.href = route;
    }
    
    openNotificationSettings() {
        window.location.href = '/settings#notifications';
        this.closeNotificationCenter();
    }
    
    markAllNotificationsRead() {
        // Clear notification badge
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = '0';
            badge.classList.add('hidden');
        }
        
        this.showSuccessMessage('All notifications marked as read!');
    }
    
    async loadNotificationPreferences() {
        try {
            const response = await fetch('/api/notifications/preferences', {
                headers: {
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                const preferences = await response.json();
                console.log('Notification preferences loaded:', preferences);
                
                // Update UI based on preferences
                this.updateUIFromPreferences(preferences);
            }
            
        } catch (error) {
            console.error('Error loading notification preferences:', error);
        }
    }
    
    updateUIFromPreferences(preferences) {
        // This would update various UI elements based on user preferences
        console.log('Updating UI from preferences:', preferences);
    }
    
    showNotificationStatus(status) {
        // Update notification status indicator if it exists
        const indicator = document.getElementById('notification-status');
        if (indicator) {
            indicator.textContent = status;
            indicator.className = `notification-status ${status}`;
        }
    }
    
    showSuccessMessage(message) {
        // Use existing toast system
        if (window.showSuccessToast) {
            window.showSuccessToast(message);
        } else {
            console.log('Success:', message);
        }
    }
    
    showNotificationError(message) {
        // Use existing toast system  
        if (window.showErrorToast) {
            window.showErrorToast(message);
        } else {
            console.error('Notification Error:', message);
        }
    }
    
    // Public methods
    
    async sendTestNotification(type = 'encouragement') {
        try {
            const response = await fetch('/api/notifications/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                },
                body: JSON.stringify({ type })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage('Test notification sent! Check your notifications.');
            } else {
                this.showNotificationError('Could not send test notification. Please try again.');
            }
            
        } catch (error) {
            console.error('Error sending test notification:', error);
            this.showNotificationError('Something went wrong sending the test notification.');
        }
    }
    
    async updatePreferences(preferences) {
        try {
            const response = await fetch('/api/notifications/preferences', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                },
                body: JSON.stringify(preferences)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage('Notification preferences updated successfully!');
                return true;
            } else {
                this.showNotificationError('Failed to update preferences. Please try again.');
                return false;
            }
            
        } catch (error) {
            console.error('Error updating preferences:', error);
            this.showNotificationError('Something went wrong updating your preferences.');
            return false;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.brainBudgetNotifications = new BrainBudgetNotifications();
});

// Add to global scope for easy access
window.BrainBudgetNotifications = BrainBudgetNotifications;