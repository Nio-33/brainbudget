/**
 * Service Worker for BrainBudget PWA
 * Provides offline functionality and caching for ADHD-friendly experience
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
                const response = await fetch('/api/upload', {
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

// Push notification handler
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');
    
    const options = {
        body: 'You have new insights about your spending!',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        tag: 'spending-insight',
        requireInteraction: false,
        actions: [
            {
                action: 'view-dashboard',
                title: 'View Dashboard',
                icon: '/static/icons/action-dashboard.png'
            },
            {
                action: 'dismiss',
                title: 'Not Now',
                icon: '/static/icons/action-dismiss.png'
            }
        ],
        data: {
            url: '/dashboard'
        }
    };
    
    if (event.data) {
        try {
            const payload = event.data.json();
            options.body = payload.message || options.body;
            options.data.url = payload.url || options.data.url;
        } catch (error) {
            console.error('[SW] Error parsing push payload:', error);
        }
    }
    
    event.waitUntil(
        self.registration.showNotification('BrainBudget', options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked');
    
    event.notification.close();
    
    const action = event.action;
    const url = event.notification.data?.url || '/dashboard';
    
    if (action === 'view-dashboard' || !action) {
        event.waitUntil(
            clients.openWindow(url)
        );
    }
    // 'dismiss' action doesn't need handling - notification is already closed
});

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