/**
 * Notification Settings Management for BrainBudget
 * ADHD-friendly notification preference handling
 */

class NotificationSettingsManager {
    constructor() {
        this.currentPreferences = {};
        this.hasUnsavedChanges = false;
        
        this.init();
    }
    
    init() {
        // Load current preferences
        this.loadPreferences();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Check notification permission status
        this.checkNotificationPermission();
    }
    
    setupEventListeners() {
        // Master toggle
        document.getElementById('notifications-master-toggle')?.addEventListener('change', (e) => {
            this.handleMasterToggle(e.target.checked);
        });
        
        // Individual notification type toggles
        document.querySelectorAll('.notification-type-toggle').forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                this.handleTypeToggle(e.target.dataset.type, e.target.checked);
            });
        });
        
        // Notification thresholds and settings
        document.querySelectorAll('.notification-threshold, .notification-setting').forEach(select => {
            select.addEventListener('change', (e) => {
                this.handleSettingChange(e.target);
            });
        });
        
        // Quiet hours
        document.getElementById('quiet-hours-toggle')?.addEventListener('change', (e) => {
            this.handleQuietHoursToggle(e.target.checked);
        });
        
        document.getElementById('quiet-hours-start')?.addEventListener('change', (e) => {
            this.handleQuietHoursChange();
        });
        
        document.getElementById('quiet-hours-end')?.addEventListener('change', (e) => {
            this.handleQuietHoursChange();
        });
        
        // Communication tone
        document.querySelectorAll('input[name="notification-tone"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.handleToneChange(e.target.value);
                }
            });
        });
        
        // Daily limit
        document.getElementById('daily-notification-limit')?.addEventListener('change', (e) => {
            this.handleDailyLimitChange(e.target.value);
        });
        
        // Permission request
        document.getElementById('enable-notifications-btn')?.addEventListener('click', () => {
            this.requestNotificationPermission();
        });
        
        // Test buttons
        document.getElementById('test-encouragement')?.addEventListener('click', () => {
            this.sendTestNotification('encouragement');
        });
        
        document.getElementById('test-spending-alert')?.addEventListener('click', () => {
            this.sendTestNotification('spending_alert');
        });
        
        document.getElementById('test-goal-celebration')?.addEventListener('click', () => {
            this.sendTestNotification('goal_achievement');
        });
        
        // Action buttons
        document.getElementById('save-notification-settings')?.addEventListener('click', () => {
            this.savePreferences();
        });
        
        document.getElementById('reset-notification-settings')?.addEventListener('click', () => {
            this.resetToDefaults();
        });
        
        document.getElementById('snooze-notifications')?.addEventListener('click', () => {
            this.snoozeNotifications();
        });
        
        document.getElementById('disable-all-notifications')?.addEventListener('click', () => {
            this.disableAllNotifications();
        });
        
        // Track changes for unsaved indicator
        document.addEventListener('change', (e) => {
            if (e.target.closest('#notifications-tab')) {
                this.markAsChanged();
            }
        });
    }
    
    async loadPreferences() {
        try {
            if (!window.brainBudgetNotifications) {
                console.warn('BrainBudget notifications not initialized');
                return;
            }
            
            const response = await fetch('/api/notifications/preferences', {
                headers: {
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                this.currentPreferences = await response.json();
                this.updateUIFromPreferences();
            } else {
                console.error('Failed to load notification preferences');
                this.loadDefaults();
            }
            
        } catch (error) {
            console.error('Error loading notification preferences:', error);
            this.loadDefaults();
        }
    }
    
    loadDefaults() {
        this.currentPreferences = {
            enabled: true,
            types: {
                spending_alert: { enabled: true, threshold: 80 },
                goal_achievement: { enabled: true },
                weekly_summary: { enabled: true, day: 'sunday', time: '09:00' },
                unusual_pattern: { enabled: false },
                encouragement: { enabled: true },
                bill_reminder: { enabled: false }
            },
            quiet_hours: { enabled: true, start: 22, end: 8 },
            tone: 'gentle',
            max_daily: 10
        };
        this.updateUIFromPreferences();
    }
    
    updateUIFromPreferences() {
        const prefs = this.currentPreferences;
        
        // Master toggle
        const masterToggle = document.getElementById('notifications-master-toggle');
        if (masterToggle) {
            masterToggle.checked = prefs.enabled !== false;
        }
        
        // Individual type toggles
        Object.entries(prefs.types || {}).forEach(([type, settings]) => {
            const toggle = document.querySelector(`[data-type="${type}"]`);
            if (toggle) {
                toggle.checked = settings.enabled !== false;
            }
            
            // Update specific settings
            if (type === 'spending_alert' && settings.threshold) {
                const thresholdSelect = document.querySelector(`select[data-type="${type}"]`);
                if (thresholdSelect) {
                    thresholdSelect.value = settings.threshold;
                }
            }
            
            if (type === 'weekly_summary') {
                const daySelect = document.querySelector('[data-type="weekly_summary"][data-setting="day"]');
                const timeSelect = document.querySelector('[data-type="weekly_summary"][data-setting="time"]');
                if (daySelect) daySelect.value = settings.day || 'sunday';
                if (timeSelect) timeSelect.value = settings.time || '09:00';
            }
        });
        
        // Quiet hours
        const quietHoursToggle = document.getElementById('quiet-hours-toggle');
        const quietHoursStart = document.getElementById('quiet-hours-start');
        const quietHoursEnd = document.getElementById('quiet-hours-end');
        
        if (quietHoursToggle) {
            quietHoursToggle.checked = prefs.quiet_hours?.enabled !== false;
        }
        if (quietHoursStart) {
            quietHoursStart.value = prefs.quiet_hours?.start || 22;
        }
        if (quietHoursEnd) {
            quietHoursEnd.value = prefs.quiet_hours?.end || 8;
        }
        
        // Communication tone
        const toneRadio = document.querySelector(`input[name="notification-tone"][value="${prefs.tone || 'gentle'}"]`);
        if (toneRadio) {
            toneRadio.checked = true;
        }
        
        // Daily limit
        const dailyLimit = document.getElementById('daily-notification-limit');
        if (dailyLimit) {
            dailyLimit.value = prefs.max_daily || 10;
        }
        
        this.hasUnsavedChanges = false;
        this.updateSaveButton();
    }
    
    async checkNotificationPermission() {
        const permissionStatus = document.getElementById('notification-permission-status');
        const enableBtn = document.getElementById('enable-notifications-btn');
        
        if (!permissionStatus) return;
        
        if ('Notification' in window) {
            const permission = Notification.permission;
            
            switch (permission) {
                case 'granted':
                    permissionStatus.innerHTML = `
                        <div class="p-4 bg-success-50 border border-success-200 rounded-xl">
                            <div class="flex items-center">
                                <span class="text-2xl mr-3">✅</span>
                                <div>
                                    <h3 class="font-medium text-success-800">Notifications Enabled</h3>
                                    <p class="text-sm text-success-600">You'll receive gentle reminders from BrainBudget</p>
                                </div>
                            </div>
                        </div>
                    `;
                    break;
                    
                case 'denied':
                    permissionStatus.innerHTML = `
                        <div class="p-4 bg-red-50 border border-red-200 rounded-xl">
                            <div class="flex items-center justify-between">
                                <div class="flex items-center">
                                    <span class="text-2xl mr-3">🚫</span>
                                    <div>
                                        <h3 class="font-medium text-red-800">Notifications Blocked</h3>
                                        <p class="text-sm text-red-600">Enable in your browser settings to receive reminders</p>
                                    </div>
                                </div>
                                <button onclick="this.textContent='Check your browser address bar 👆'" class="text-xs bg-red-100 text-red-700 px-3 py-1 rounded-lg">
                                    Help
                                </button>
                            </div>
                        </div>
                    `;
                    break;
                    
                case 'default':
                default:
                    // Keep the existing enable button
                    break;
            }
        } else {
            permissionStatus.innerHTML = `
                <div class="p-4 bg-gray-50 border border-gray-200 rounded-xl">
                    <div class="flex items-center">
                        <span class="text-2xl mr-3">📱</span>
                        <div>
                            <h3 class="font-medium text-gray-800">Browser Doesn't Support Notifications</h3>
                            <p class="text-sm text-gray-600">You can still use all BrainBudget features without notifications</p>
                        </div>
                    </div>
                </div>
            `;
        }
    }
    
    async requestNotificationPermission() {
        if (window.brainBudgetNotifications) {
            const granted = await window.brainBudgetNotifications.requestPermission();
            if (granted) {
                this.checkNotificationPermission();
                this.showSuccessMessage('🎉 Great! You\'ll now get gentle financial reminders.');
            }
        }
    }
    
    handleMasterToggle(enabled) {
        this.currentPreferences.enabled = enabled;
        
        // Update UI state
        const notificationCards = document.querySelectorAll('.notification-type-card');
        notificationCards.forEach(card => {
            card.style.opacity = enabled ? '1' : '0.5';
        });
        
        this.markAsChanged();
    }
    
    handleTypeToggle(type, enabled) {
        if (!this.currentPreferences.types) {
            this.currentPreferences.types = {};
        }
        
        if (!this.currentPreferences.types[type]) {
            this.currentPreferences.types[type] = {};
        }
        
        this.currentPreferences.types[type].enabled = enabled;
        this.markAsChanged();
    }
    
    handleSettingChange(element) {
        const type = element.dataset.type;
        const setting = element.dataset.setting;
        const value = element.value;
        
        if (!this.currentPreferences.types) {
            this.currentPreferences.types = {};
        }
        
        if (!this.currentPreferences.types[type]) {
            this.currentPreferences.types[type] = {};
        }
        
        if (setting) {
            this.currentPreferences.types[type][setting] = value;
        } else if (element.classList.contains('notification-threshold')) {
            this.currentPreferences.types[type].threshold = parseInt(value);
        }
        
        this.markAsChanged();
    }
    
    handleQuietHoursToggle(enabled) {
        if (!this.currentPreferences.quiet_hours) {
            this.currentPreferences.quiet_hours = {};
        }
        
        this.currentPreferences.quiet_hours.enabled = enabled;
        this.markAsChanged();
    }
    
    handleQuietHoursChange() {
        const start = document.getElementById('quiet-hours-start')?.value;
        const end = document.getElementById('quiet-hours-end')?.value;
        
        if (!this.currentPreferences.quiet_hours) {
            this.currentPreferences.quiet_hours = {};
        }
        
        this.currentPreferences.quiet_hours.start = parseInt(start);
        this.currentPreferences.quiet_hours.end = parseInt(end);
        this.markAsChanged();
    }
    
    handleToneChange(tone) {
        this.currentPreferences.tone = tone;
        this.markAsChanged();
    }
    
    handleDailyLimitChange(limit) {
        this.currentPreferences.max_daily = limit === 'unlimited' ? 999 : parseInt(limit);
        this.markAsChanged();
    }
    
    markAsChanged() {
        this.hasUnsavedChanges = true;
        this.updateSaveButton();
    }
    
    updateSaveButton() {
        const saveBtn = document.getElementById('save-notification-settings');
        if (saveBtn) {
            if (this.hasUnsavedChanges) {
                saveBtn.textContent = '💾 Save Changes';
                saveBtn.classList.add('bg-warning-500', 'hover:bg-warning-600');
                saveBtn.classList.remove('bg-primary-500', 'hover:bg-primary-600');
            } else {
                saveBtn.textContent = '💾 Save Preferences';
                saveBtn.classList.add('bg-primary-500', 'hover:bg-primary-600');
                saveBtn.classList.remove('bg-warning-500', 'hover:bg-warning-600');
            }
        }
    }
    
    async savePreferences() {
        try {
            const saveBtn = document.getElementById('save-notification-settings');
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = '💾 Saving...';
            }
            
            if (!window.brainBudgetNotifications) {
                throw new Error('Notification system not initialized');
            }
            
            const success = await window.brainBudgetNotifications.updatePreferences(this.currentPreferences);
            
            if (success) {
                this.hasUnsavedChanges = false;
                this.updateSaveButton();
                this.showSuccessMessage('✅ Your notification preferences have been saved!');
            } else {
                throw new Error('Failed to save preferences');
            }
            
        } catch (error) {
            console.error('Error saving preferences:', error);
            this.showErrorMessage('Sorry, we couldn\'t save your preferences. Please try again in a moment.');
        } finally {
            const saveBtn = document.getElementById('save-notification-settings');
            if (saveBtn) {
                saveBtn.disabled = false;
                this.updateSaveButton();
            }
        }
    }
    
    resetToDefaults() {
        const confirmed = confirm('This will reset all your notification preferences to the ADHD-friendly defaults. Are you sure?');
        
        if (confirmed) {
            this.loadDefaults();
            this.markAsChanged();
            this.showSuccessMessage('🔄 Notification settings reset to gentle defaults.');
        }
    }
    
    async sendTestNotification(type) {
        try {
            if (!window.brainBudgetNotifications) {
                throw new Error('Notification system not initialized');
            }
            
            await window.brainBudgetNotifications.sendTestNotification(type);
            this.showSuccessMessage('📱 Test notification sent! Check your notifications.');
            
        } catch (error) {
            console.error('Error sending test notification:', error);
            this.showErrorMessage('Could not send test notification. Make sure notifications are enabled in your browser.');
        }
    }
    
    async snoozeNotifications() {
        try {
            // This would typically call the backend to set a temporary snooze
            const snoozeUntil = new Date();
            snoozeUntil.setHours(snoozeUntil.getHours() + 24);
            
            // Store snooze in localStorage as a simple implementation
            localStorage.setItem('brainbudget_notifications_snoozed', snoozeUntil.toISOString());
            
            this.showSuccessMessage('😴 Notifications snoozed for 24 hours. Rest well!');
            
            // Update UI
            const snoozeBtn = document.getElementById('snooze-notifications');
            if (snoozeBtn) {
                snoozeBtn.textContent = '✅ Snoozed for 24h';
                snoozeBtn.disabled = true;
            }
            
        } catch (error) {
            console.error('Error snoozing notifications:', error);
            this.showErrorMessage('Could not snooze notifications. Please try again.');
        }
    }
    
    async disableAllNotifications() {
        const confirmed = confirm('This will turn off ALL notifications from BrainBudget. You can re-enable them anytime. Are you sure?');
        
        if (confirmed) {
            this.currentPreferences.enabled = false;
            await this.savePreferences();
            
            this.showSuccessMessage('⏸️ All notifications disabled. Take care of yourself!');
        }
    }
    
    async getAuthToken() {
        // This would get the current user's Firebase auth token
        if (window.firebase && window.firebase.auth && firebase.auth().currentUser) {
            return await firebase.auth().currentUser.getIdToken();
        }
        return null;
    }
    
    showSuccessMessage(message) {
        // Use the existing toast system if available
        if (window.showSuccessToast) {
            window.showSuccessToast(message);
        } else {
            alert(message);
        }
    }
    
    showErrorMessage(message) {
        // Use the existing toast system if available
        if (window.showErrorToast) {
            window.showErrorToast(message);
        } else {
            alert(message);
        }
    }
}

// Initialize when DOM is ready and we're on the settings page
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('notifications-tab')) {
        window.notificationSettingsManager = new NotificationSettingsManager();
    }
});

// Handle tab switching
document.addEventListener('click', (e) => {
    if (e.target.matches('[data-tab="notifications"]')) {
        // Initialize notification settings manager if not already done
        if (!window.notificationSettingsManager && document.getElementById('notifications-tab')) {
            window.notificationSettingsManager = new NotificationSettingsManager();
        }
    }
});

// CSS for improved styling
const style = document.createElement('style');
style.textContent = `
    .notification-threshold, .notification-setting {
        padding: 0.5rem;
        border: 1px solid #e5e7eb;
        border-radius: 0.75rem;
        font-size: 0.875rem;
        background: white;
        width: auto;
        min-width: 120px;
    }
    
    .notification-threshold:focus, .notification-setting:focus {
        outline: none;
        border-color: #4A90E2;
        box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
    }
    
    .notification-type-card.disabled {
        opacity: 0.5;
        pointer-events: none;
    }
    
    .has-unsaved-changes {
        position: relative;
    }
    
    .has-unsaved-changes::after {
        content: '';
        position: absolute;
        top: -2px;
        right: -2px;
        width: 8px;
        height: 8px;
        background: #f59e0b;
        border-radius: 50%;
    }
    
    @media (max-width: 640px) {
        .notification-type-card {
            padding: 1rem;
        }
        
        .notification-type-card .ml-16 {
            margin-left: 0;
            margin-top: 1rem;
        }
    }
`;

document.head.appendChild(style);