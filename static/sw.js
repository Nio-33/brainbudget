/**
 * Service Worker for BrainBudget PWA
 * Provides offline functionality and caching for user-friendly experience
 */

const CACHE_NAME = 'brainbudget-v1.0.0';
const OFFLINE_URL = '/offline';

// Files to cache immediately when service worker installs
const STATIC_CACHE_FILES = [
    '/',
    '/upload',
    '/dashboard', 
    '/settings',
    '/static/css/main.css',
    '/static/js/core.js',
    '/static/js/navigation.js',
    '/static/js/upload.js',
    '/static/js/charts.js',
    '/static/manifest.json',
    // Tailwind CSS CDN
    'https://cdn.tailwindcss.com',
    // Chart.js CDN
    'https://cdn.jsdelivr.net/npm/chart.js'
];

// Files to cache on first visit
const RUNTIME_CACHE_FILES = [
    '/analysis',
    '/api/dashboard',
    '/api/settings'
];

// Install event - cache essential files
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static files');
                return cache.addAll(STATIC_CACHE_FILES);
            })
            .then(() => {
                console.log('[SW] Service worker installed successfully');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Failed to cache static files:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== CACHE_NAME) {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('[SW] Service worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-HTTP requests
    if (!request.url.startsWith('http')) {
        return;
    }
    
    // Handle navigation requests (page loads)
    if (request.mode === 'navigate') {
        event.respondWith(
            handleNavigationRequest(request)
        );
        return;
    }
    
    // Handle API requests
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            handleApiRequest(request)
        );
        return;
    }
    
    // Handle static assets
    event.respondWith(
        handleStaticRequest(request)
    );
});

// Handle navigation requests (HTML pages)
async function handleNavigationRequest(request) {
    try {
        // Try network first for fresh content
        const networkResponse = await fetch(request);
        
        // Cache the response for offline use
        const cache = await caches.open(CACHE_NAME);
        cache.put(request, networkResponse.clone());
        
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network failed for navigation, checking cache...');
        
        // Try to get from cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page as fallback
        const offlineResponse = await caches.match(OFFLINE_URL);
        if (offlineResponse) {
            return offlineResponse;
        }
        
        // Last resort - return a basic offline message
        return new Response(
            createOfflineHTML(),
            {
                status: 200,
                headers: { 'Content-Type': 'text/html' }
            }
        );
    }
}

// Handle API requests with background sync capabilities
async function handleApiRequest(request) {
    try {
        // Always try network first for API requests
        const networkResponse = await fetch(request);
        
        // Cache GET requests for offline access
        if (request.method === 'GET' && networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[SW] API request failed, checking cache...');
        
        // For GET requests, try cache
        if (request.method === 'GET') {
            const cachedResponse = await caches.match(request);
            if (cachedResponse) {
                // Add offline indicator header
                const headers = new Headers(cachedResponse.headers);
                headers.set('X-Served-By', 'service-worker-cache');
                
                return new Response(cachedResponse.body, {
                    status: cachedResponse.status,
                    statusText: cachedResponse.statusText,
                    headers: headers
                });
            }
        }
        
        // Return meaningful error for offline state
        return new Response(
            JSON.stringify({
                error: true,
                message: "You're offline right now. Don't worry, we'll sync your data when you're back online! 📡",
                offline: true
            }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Handle static assets (CSS, JS, images)
async function handleStaticRequest(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        // Serve from cache immediately
        return cachedResponse;
    }
    
    try {
        // Fetch from network and cache
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[SW] Failed to fetch static asset:', request.url);
        
        // Return empty response for missing assets to prevent broken layout
        return new Response('', {
            status: 404,
            statusText: 'Not Found'
        });
    }
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync triggered:', event.tag);
    
    if (event.tag === 'upload-statement') {
        event.waitUntil(syncUploadData());
    } else if (event.tag === 'settings-update') {
        event.waitUntil(syncSettingsData());
    }
});

// Sync uploaded statements when back online
async function syncUploadData() {
    try {
        console.log('[SW] Syncing upload data...');
        
        // Get pending uploads from IndexedDB
        const pendingUploads = await getPendingUploads();
        
        for (const upload of pendingUploads) {
            try {
                const response = await fetch('/api/upload/statement', {
                    method: 'POST',
                    body: upload.formData
                });
                
                if (response.ok) {
                    await removePendingUpload(upload.id);
                    console.log('[SW] Upload synced successfully:', upload.id);
                } else {
                    console.error('[SW] Failed to sync upload:', upload.id);
                }
            } catch (error) {
                console.error('[SW] Error syncing upload:', error);
            }
        }
    } catch (error) {
        console.error('[SW] Background sync failed:', error);
    }
}

// Sync settings when back online
async function syncSettingsData() {
    try {
        console.log('[SW] Syncing settings data...');
        
        // Implementation for syncing settings
        // This would typically involve reading from IndexedDB and posting to API
    } catch (error) {
        console.error('[SW] Settings sync failed:', error);
    }
}

// Push notification handler with ADHD-friendly messaging
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');
    
    // Default ADHD-friendly notification
    let notificationData = {
        title: '🧠💰 BrainBudget',
        body: 'You have a gentle update about your finances!',
        icon: '/static/icons/brainbudget-icon-192.png',
        badge: '/static/icons/brainbudget-badge.png',
        tag: 'brainbudget-general',
        requireInteraction: false,
        silent: false,
        vibrate: [200, 100, 200], // Gentle vibration pattern
        data: {
            url: '/dashboard',
            type: 'general',
            timestamp: Date.now()
        }
    };
    
    // Parse notification payload if available
    if (event.data) {
        try {
            const payload = event.data.json();
            console.log('[SW] Push payload:', payload);
            
            // Override with payload data
            if (payload.notification) {
                notificationData.title = payload.notification.title || notificationData.title;
                notificationData.body = payload.notification.body || notificationData.body;
                notificationData.icon = payload.notification.icon || notificationData.icon;
            }
            
            // Handle data payload
            if (payload.data) {
                notificationData.data = { ...notificationData.data, ...payload.data };
            }
            
            // Set notification type-specific properties
            const notificationType = payload.data?.type || 'general';
            notificationData = configureNotificationByType(notificationData, notificationType);
            
        } catch (error) {
            console.error('[SW] Error parsing push payload:', error);
        }
    }
    
    event.waitUntil(
        showBrainBudgetNotification(notificationData)
    );
});

// Configure notification based on type for ADHD-friendly experience
function configureNotificationByType(baseConfig, type) {
    const typeConfigs = {
        'spending_alert': {
            tag: 'spending-alert',
            requireInteraction: true, // Important financial alerts need attention
            vibrate: [300, 100, 300, 100, 300], // More noticeable vibration
            actions: [
                {
                    action: 'view-spending',
                    title: '💳 Check Spending',
                    icon: '/static/icons/action-spending.png'
                },
                {
                    action: 'adjust-budget',
                    title: '⚖️ Adjust Budget',
                    icon: '/static/icons/action-budget.png'
                }
            ]
        },
        'goal_achievement': {
            tag: 'goal-celebration',
            requireInteraction: false,
            vibrate: [100, 50, 100, 50, 100, 50, 200], // Celebratory vibration
            actions: [
                {
                    action: 'celebrate',
                    title: '🎉 Celebrate!',
                    icon: '/static/icons/action-celebrate.png'
                },
                {
                    action: 'set-new-goal',
                    title: '🎯 New Goal',
                    icon: '/static/icons/action-goal.png'
                }
            ]
        },
        'weekly_summary': {
            tag: 'weekly-summary',
            requireInteraction: false,
            vibrate: [200, 100, 200], // Standard gentle vibration
            actions: [
                {
                    action: 'view-summary',
                    title: '📊 View Summary',
                    icon: '/static/icons/action-summary.png'
                },
                {
                    action: 'dismiss',
                    title: '👍 Got it',
                    icon: '/static/icons/action-dismiss.png'
                }
            ]
        },
        'unusual_pattern': {
            tag: 'pattern-alert',
            requireInteraction: false,
            vibrate: [200, 100, 200], // Gentle attention-getter
            actions: [
                {
                    action: 'review-transactions',
                    title: '🔍 Review',
                    icon: '/static/icons/action-review.png'
                },
                {
                    action: 'dismiss',
                    title: '✅ All good',
                    icon: '/static/icons/action-dismiss.png'
                }
            ]
        },
        'encouragement': {
            tag: 'encouragement',
            requireInteraction: false,
            vibrate: [100, 50, 100], // Very gentle vibration
            silent: false,
            actions: [
                {
                    action: 'view-progress',
                    title: '💪 See Progress',
                    icon: '/static/icons/action-progress.png'
                },
                {
                    action: 'dismiss',
                    title: '💜 Thanks',
                    icon: '/static/icons/action-thanks.png'
                }
            ]
        },
        'bill_reminder': {
            tag: 'bill-reminder',
            requireInteraction: true, // Bills are important
            vibrate: [300, 200, 300], // Attention-getting but not harsh
            actions: [
                {
                    action: 'pay-bill',
                    title: '💰 Handle Bill',
                    icon: '/static/icons/action-pay.png'
                },
                {
                    action: 'remind-later',
                    title: '⏰ Remind Later',
                    icon: '/static/icons/action-snooze.png'
                }
            ]
        }
    };
    
    const typeConfig = typeConfigs[type] || {};
    
    return {
        ...baseConfig,
        ...typeConfig,
        data: {
            ...baseConfig.data,
            type: type
        }
    };
}

// Show notification with error handling and accessibility
async function showBrainBudgetNotification(config) {
    try {
        // Check if notifications are still enabled
        if (Notification.permission !== 'granted') {
            console.log('[SW] Notifications not granted, skipping display');
            return;
        }
        
        // Show the notification
        await self.registration.showNotification(config.title, {
            body: config.body,
            icon: config.icon,
            badge: config.badge,
            tag: config.tag,
            requireInteraction: config.requireInteraction,
            silent: config.silent,
            vibrate: config.vibrate,
            actions: config.actions || [],
            data: config.data,
            timestamp: Date.now(),
            // Accessibility improvements
            lang: 'en',
            dir: 'ltr'
        });
        
        console.log('[SW] Notification displayed successfully');
        
        // Track notification display for analytics
        await trackNotificationEvent('displayed', config.data?.type, config.data);
        
    } catch (error) {
        console.error('[SW] Error displaying notification:', error);
        
        // Fallback for older browsers - show basic notification
        try {
            await self.registration.showNotification(config.title, {
                body: config.body,
                icon: config.icon,
                tag: 'brainbudget-fallback'
            });
        } catch (fallbackError) {
            console.error('[SW] Fallback notification also failed:', fallbackError);
        }
    }
}

// Enhanced notification click handler for ADHD-friendly interactions
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked:', event.action);
    
    event.notification.close();
    
    const action = event.action;
    const notificationData = event.notification.data || {};
    const type = notificationData.type || 'general';
    
    // Track notification interaction
    trackNotificationEvent('clicked', type, { action, ...notificationData });
    
    // Handle different actions
    const actionPromise = handleNotificationAction(action, type, notificationData);
    
    event.waitUntil(actionPromise);
});

// Handle notification actions with appropriate responses
async function handleNotificationAction(action, type, data) {
    try {
        // Default URL routing based on notification type
        const defaultUrls = {
            'spending_alert': '/dashboard?tab=spending',
            'goal_achievement': '/dashboard?tab=goals',
            'weekly_summary': '/dashboard?tab=summary',
            'unusual_pattern': '/dashboard?tab=transactions',
            'encouragement': '/dashboard',
            'bill_reminder': '/dashboard?tab=bills',
            'general': '/dashboard'
        };
        
        let targetUrl = data.url || defaultUrls[type] || '/dashboard';
        
        // Handle specific actions
        switch (action) {
            case 'view-spending':
            case 'view-dashboard':
                targetUrl = '/dashboard?tab=spending';
                break;
                
            case 'adjust-budget':
                targetUrl = '/settings?tab=budgets';
                break;
                
            case 'celebrate':
                targetUrl = '/dashboard?tab=goals&celebrate=true';
                break;
                
            case 'set-new-goal':
                targetUrl = '/settings?tab=goals&action=new';
                break;
                
            case 'view-summary':
                targetUrl = '/dashboard?tab=summary';
                break;
                
            case 'review-transactions':
                targetUrl = '/dashboard?tab=transactions&highlight=unusual';
                break;
                
            case 'view-progress':
                targetUrl = '/dashboard?tab=progress';
                break;
                
            case 'pay-bill':
                targetUrl = '/dashboard?tab=bills&action=pay';
                break;
                
            case 'remind-later':
                // Schedule a reminder for later (this would integrate with the notification system)
                await scheduleReminder(data);
                return; // Don't open window for reminder scheduling
                
            case 'dismiss':
                // Just track the dismissal - no window opening needed
                return;
                
            default:
                // No action specified - open dashboard
                break;
        }
        
        // Open the appropriate window/tab
        const client = await openOrFocusWindow(targetUrl);
        
        // Send message to client with notification context
        if (client) {
            client.postMessage({
                type: 'NOTIFICATION_CLICKED',
                notification: { action, type, data },
                url: targetUrl
            });
        }
        
    } catch (error) {
        console.error('[SW] Error handling notification action:', error);
        
        // Fallback - just open dashboard
        await openOrFocusWindow('/dashboard');
    }
}

// Open window or focus existing one
async function openOrFocusWindow(url) {
    try {
        // Check if there's already a window open with this URL
        const clients = await self.clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        });
        
        // Look for existing window with the same origin
        for (const client of clients) {
            const clientUrl = new URL(client.url);
            const targetUrl = new URL(url, self.location.origin);
            
            if (clientUrl.origin === targetUrl.origin) {
                // Focus existing window and navigate if needed
                if (clientUrl.pathname !== targetUrl.pathname || 
                    clientUrl.search !== targetUrl.search) {
                    client.navigate(url);
                }
                return client.focus();
            }
        }
        
        // No existing window found - open new one
        return await self.clients.openWindow(url);
        
    } catch (error) {
        console.error('[SW] Error opening/focusing window:', error);
        
        // Fallback - try to open new window
        try {
            return await self.clients.openWindow(url);
        } catch (fallbackError) {
            console.error('[SW] Fallback window opening failed:', fallbackError);
            return null;
        }
    }
}

// Schedule a reminder for later (integrates with notification system)
async function scheduleReminder(data) {
    try {
        // This would typically integrate with your backend to schedule a reminder
        console.log('[SW] Scheduling reminder for:', data);
        
        // For now, just set a simple timeout reminder (not persistent across browser restarts)
        // In production, this would save to IndexedDB and integrate with the notification service
        
        const reminderTime = 1000 * 60 * 60 * 2; // 2 hours from now
        
        setTimeout(async () => {
            await showBrainBudgetNotification({
                title: '🔔 Gentle Reminder',
                body: 'You asked me to remind you about your bill. No pressure! 💙',
                icon: '/static/icons/brainbudget-icon-192.png',
                badge: '/static/icons/brainbudget-badge.png',
                tag: 'reminder-' + Date.now(),
                data: {
                    type: 'bill_reminder',
                    url: '/dashboard?tab=bills',
                    isReminder: true,
                    originalData: data
                }
            });
        }, reminderTime);
        
        // Show confirmation that reminder is set
        await showBrainBudgetNotification({
            title: '⏰ Reminder Set',
            body: 'I\'ll gently remind you about this in 2 hours. You\'ve got this! 💪',
            icon: '/static/icons/brainbudget-icon-192.png',
            tag: 'reminder-confirmation',
            requireInteraction: false,
            vibrate: [100, 50, 100],
            data: {
                type: 'encouragement',
                url: '/dashboard'
            }
        });
        
    } catch (error) {
        console.error('[SW] Error scheduling reminder:', error);
    }
}

// Track notification events for analytics and improvement
async function trackNotificationEvent(eventType, notificationType, data = {}) {
    try {
        const eventData = {
            event: eventType,
            notification_type: notificationType,
            timestamp: Date.now(),
            user_agent: navigator.userAgent,
            data: data
        };
        
        // Store event in IndexedDB for later sync
        await storeAnalyticsEvent(eventData);
        
        console.log('[SW] Tracked notification event:', eventType, notificationType);
        
    } catch (error) {
        console.error('[SW] Error tracking notification event:', error);
    }
}

// Store analytics events in IndexedDB (simplified implementation)
async function storeAnalyticsEvent(eventData) {
    // This would typically use IndexedDB to store analytics events
    // For now, just log to console
    console.log('[SW] Analytics event:', eventData);
}

// Message handler for communication with main thread
self.addEventListener('message', (event) => {
    console.log('[SW] Message received:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// Utility functions for IndexedDB operations (simplified)
async function getPendingUploads() {
    // This would typically use IndexedDB to get pending uploads
    // For now, return empty array
    return [];
}

async function removePendingUpload(id) {
    // This would typically remove the upload from IndexedDB
    console.log('[SW] Removing pending upload:', id);
}

// Create offline HTML page
function createOfflineHTML() {
    return `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>You're Offline - BrainBudget</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body { font-family: Inter, system-ui, sans-serif; }
            </style>
        </head>
        <body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
            <div class="max-w-md w-full bg-white rounded-2xl p-8 shadow-sm text-center">
                <div class="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <span class="text-3xl">📡</span>
                </div>
                <h1 class="text-2xl font-bold text-gray-800 mb-4">You're offline right now</h1>
                <p class="text-gray-600 mb-6">
                    Don't worry! BrainBudget works offline too. Your data is safe and will sync when you're back online.
                </p>
                <div class="space-y-3">
                    <button onclick="location.reload()" class="w-full bg-blue-500 text-white py-3 rounded-xl font-medium hover:bg-blue-600 transition-colors">
                        Try Again
                    </button>
                    <button onclick="history.back()" class="w-full border border-gray-300 text-gray-700 py-3 rounded-xl font-medium hover:bg-gray-50 transition-colors">
                        Go Back
                    </button>
                </div>
            </div>
        </body>
        </html>
    `;
}

console.log('[SW] Service worker script loaded');