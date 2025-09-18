/**
 * Plaid Link integration for BrainBudget
 * User-friendly bank account connection with step-by-step guidance
 */

class BrainBudgetPlaidLink {
    constructor(options = {}) {
        this.onSuccess = options.onSuccess || this.defaultOnSuccess;
        this.onExit = options.onExit || this.defaultOnExit;
        this.onEvent = options.onEvent || this.defaultOnEvent;
        
        // User-friendly configuration
        this.showUI = {
            progressSteps: true,
            encouragingMessages: true,
            securityReminders: true,
            skipOption: true
        };
        
        // Plaid Link handler
        this.linkHandler = null;
        this.linkToken = null;
        
        // Connection state
        this.isConnecting = false;
        this.currentStep = 1;
        this.totalSteps = 4;
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    /**
     * Initialize Plaid Link
     */
    async init() {
        try {
            // Check if Plaid Link script is loaded
            if (typeof Plaid === 'undefined') {
                await this.loadPlaidScript();
            }
            
            // Set up event listeners
            this.setupEventListeners();
            
            console.log('BrainBudget Plaid Link initialized');
            
        } catch (error) {
            console.error('Failed to initialize Plaid Link:', error);
            this.showMessage('error', 'Banking connection setup failed. You can still upload statements manually! 📄');
        }
    }
    
    /**
     * Load Plaid Link script dynamically
     */
    loadPlaidScript() {
        return new Promise((resolve, reject) => {
            if (typeof Plaid !== 'undefined') {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = 'https://cdn.plaid.com/link/v2/stable/link-initialize.js';
            script.async = true;
            script.onload = resolve;
            script.onerror = reject;
            
            document.head.appendChild(script);
        });
    }
    
    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Connect bank account buttons
        document.querySelectorAll('.connect-bank-btn').forEach(btn => {
            btn.addEventListener('click', () => this.startBankConnection());
        });
        
        // Skip banking connection buttons  
        document.querySelectorAll('.skip-banking-btn').forEach(btn => {
            btn.addEventListener('click', () => this.showSkipConfirmation());
        });
        
        // Manual upload fallback
        document.querySelectorAll('.manual-upload-btn').forEach(btn => {
            btn.addEventListener('click', () => this.redirectToManualUpload());
        });
    }
    
    /**
     * Start the bank connection process
     */
    async startBankConnection() {
        if (this.isConnecting) {
            return; // Prevent multiple simultaneous connections
        }
        
        this.isConnecting = true;
        this.updateProgress(1, "Getting ready to connect your bank...");
        
        try {
            // Show user-friendly onboarding
            if (this.showUI.progressSteps) {
                this.showConnectionSteps();
            }
            
            // Get link token from backend
            const linkToken = await this.createLinkToken();
            
            if (!linkToken) {
                throw new Error('Failed to create link token');
            }
            
            this.linkToken = linkToken;
            this.updateProgress(2, "Setting up secure connection...");
            
            // Initialize Plaid Link
            await this.initializePlaidLink();
            
            this.updateProgress(3, "Ready to connect! Click to choose your bank.");
            
            // Open Plaid Link
            this.linkHandler.open();
            
        } catch (error) {
            console.error('Error starting bank connection:', error);
            this.handleConnectionError(error);
        }
    }
    
    /**
     * Create link token from backend
     */
    async createLinkToken() {
        try {
            const response = await fetch('/api/plaid/link/token/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    user_name: this.getCurrentUserName()
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to create link token');
            }
            
            return data.link_token;
            
        } catch (error) {
            console.error('Error creating link token:', error);
            throw error;
        }
    }
    
    /**
     * Initialize Plaid Link with token
     */
    async initializePlaidLink() {
        const config = {
            token: this.linkToken,
            onSuccess: (public_token, metadata) => this.onSuccess(public_token, metadata),
            onExit: (err, metadata) => this.onExit(err, metadata),
            onEvent: (eventName, metadata) => this.onEvent(eventName, metadata),
            env: this.getPlaidEnvironment(),
            product: ['transactions'],
            countryCodes: ['US'],
        };
        
        this.linkHandler = Plaid.create(config);
    }
    
    /**
     * Handle successful bank connection
     */
    async defaultOnSuccess(public_token, metadata) {
        this.updateProgress(4, "Connected! Setting up your account...");
        
        try {
            // Send public token to backend for exchange
            const response = await fetch('/api/plaid/link/token/exchange', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    public_token: public_token,
                    accounts: metadata.accounts,
                    institution: metadata.institution
                })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to complete connection');
            }
            
            // Show success message with encouraging tone
            this.showSuccessMessage(data, metadata);
            
            // Redirect to dashboard or continue onboarding
            setTimeout(() => {
                window.location.href = '/dashboard?connected=true';
            }, 3000);
            
        } catch (error) {
            console.error('Error completing bank connection:', error);
            this.handleConnectionError(error);
        } finally {
            this.isConnecting = false;
        }
    }
    
    /**
     * Handle when user exits Plaid Link
     */
    defaultOnExit(err, metadata) {
        this.isConnecting = false;
        
        if (err != null) {
            console.error('Plaid Link error:', err);
            this.showMessage('error', this.getPlaidErrorMessage(err));
        } else {
            // User exited voluntarily
            this.showMessage('info', "No problem! You can always connect your bank later or upload statements manually. 👋");
        }
        
        // Hide progress if shown
        this.hideProgress();
    }
    
    /**
     * Handle Plaid Link events for analytics and UX
     */
    defaultOnEvent(eventName, metadata) {
        console.log('Plaid Link event:', eventName, metadata);
        
        // User-friendly progress updates based on events
        switch (eventName) {
            case 'OPEN':
                this.showMessage('info', "Great! Now choose your bank from the list. 🏦");
                break;
            case 'SEARCH_INSTITUTION':
                this.showMessage('info', "Perfect! Search for your bank name. 🔍");
                break;
            case 'SELECT_INSTITUTION':
                this.showMessage('info', "Excellent choice! Now enter your login info. 🔑");
                break;
            case 'SUBMIT_CREDENTIALS':
                this.showMessage('info', "Checking your credentials securely... 🔒");
                break;
            case 'SUBMIT_MFA':
                this.showMessage('info', "Almost there! Just verifying it's really you. ✅");
                break;
            case 'TRANSITION_VIEW':
                if (metadata.view_name === 'CONNECTED') {
                    this.showMessage('success', "Amazing! Your bank is now connected! 🎉");
                }
                break;
        }
    }
    
    /**
     * Show user-friendly connection steps
     */
    showConnectionSteps() {
        const modal = document.createElement('div');
        modal.className = 'plaid-steps-modal fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-8 max-w-md mx-4 text-center">
                <div class="text-4xl mb-4">🏦</div>
                <h2 class="text-2xl font-bold mb-4 text-gray-900">Let's Connect Your Bank!</h2>
                <div class="space-y-4 text-left mb-6">
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
                        <span>Choose your bank from the list</span>
                    </div>
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
                        <span>Log in with your online banking info</span>
                    </div>
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
                        <span>Select which accounts to connect</span>
                    </div>
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center text-sm font-bold">✓</div>
                        <span>Start getting insights automatically!</span>
                    </div>
                </div>
                <div class="bg-blue-50 p-4 rounded-lg mb-6">
                    <div class="text-blue-800 text-sm">
                        🔒 <strong>Your info is secure:</strong> We use bank-level encryption and never store your login details.
                    </div>
                </div>
                <div class="flex space-x-3">
                    <button class="flex-1 bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 transition-colors" onclick="this.closest('.plaid-steps-modal').remove()">
                        Let's Do This! 🚀
                    </button>
                    <button class="flex-1 bg-gray-200 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-300 transition-colors" onclick="this.closest('.plaid-steps-modal').remove(); window.brainBudgetPlaid.showSkipConfirmation()">
                        Maybe Later
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Remove on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }
    
    /**
     * Show skip confirmation dialog
     */
    showSkipConfirmation() {
        const modal = document.createElement('div');
        modal.className = 'plaid-skip-modal fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-8 max-w-md mx-4 text-center">
                <div class="text-4xl mb-4">📄</div>
                <h2 class="text-2xl font-bold mb-4 text-gray-900">No Problem!</h2>
                <p class="text-gray-600 mb-6">
                    You can always connect your bank later. For now, you can upload bank statements 
                    manually and still get amazing AI insights about your spending!
                </p>
                <div class="flex space-x-3">
                    <button class="flex-1 bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 transition-colors" onclick="window.location.href='/upload'">
                        Upload Statement 📋
                    </button>
                    <button class="flex-1 bg-gray-200 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-300 transition-colors" onclick="this.closest('.plaid-skip-modal').remove()">
                        Go Back
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Remove on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }
    
    /**
     * Show success message after connection
     */
    showSuccessMessage(data, metadata) {
        const accountCount = data.accounts ? data.accounts.length : 0;
        const institutionName = metadata.institution.name;
        
        this.showMessage('success', 
            `🎉 Success! Connected ${accountCount} accounts from ${institutionName}. ` +
            `Your transactions will sync automatically from now on!`
        );
    }
    
    /**
     * Handle connection errors with user-friendly messages
     */
    handleConnectionError(error) {
        const friendlyMessage = this.getErrorMessage(error);
        this.showMessage('error', friendlyMessage);
        this.hideProgress();
        this.isConnecting = false;
    }
    
    /**
     * Get user-friendly error message
     */
    getErrorMessage(error) {
        const errorStr = error.message.toLowerCase();
        
        const errorMessages = {
            'invalid_credentials': "Login info didn't match. Double-check and try again! 🔑",
            'invalid_mfa': "Verification code didn't work. Try getting a new one! 🔢", 
            'item_login_required': "Your bank needs you to log in again. Let's reconnect! 🔄",
            'institution_down': "Your bank's systems are having issues. Try again in a few minutes! ⏰",
            'rate_limit': "We're going a bit fast! Let's wait a moment and try again. ☕",
            'network': "Connection issue! Check your internet and try again. 📶",
            'invalid_link_token': "Session expired. Let's start fresh! 🔄"
        };
        
        for (const [key, message] of Object.entries(errorMessages)) {
            if (errorStr.includes(key)) {
                return message;
            }
        }
        
        return "Something didn't work as expected. No worries - you can try again or upload a statement instead! 💪";
    }
    
    /**
     * Get Plaid-specific error message
     */
    getPlaidErrorMessage(plaidError) {
        if (plaidError.error_code) {
            return this.getErrorMessage({ message: plaidError.error_code });
        }
        return "Connection was cancelled. You can try again anytime! 👋";
    }
    
    /**
     * Update progress indicator
     */
    updateProgress(step, message) {
        this.currentStep = step;
        
        // Update progress bar if it exists
        const progressBar = document.querySelector('.plaid-progress-bar');
        if (progressBar) {
            const percentage = (step / this.totalSteps) * 100;
            progressBar.style.width = `${percentage}%`;
        }
        
        // Update progress text
        const progressText = document.querySelector('.plaid-progress-text');
        if (progressText) {
            progressText.textContent = message;
        }
        
        // Show progress container
        const progressContainer = document.querySelector('.plaid-progress-container');
        if (progressContainer) {
            progressContainer.classList.remove('hidden');
        }
        
        console.log(`Plaid Progress ${step}/${this.totalSteps}: ${message}`);
    }
    
    /**
     * Hide progress indicator
     */
    hideProgress() {
        const progressContainer = document.querySelector('.plaid-progress-container');
        if (progressContainer) {
            progressContainer.classList.add('hidden');
        }
    }
    
    /**
     * Show message to user
     */
    showMessage(type, message) {
        // Use existing toast system if available
        if (typeof showToast === 'function') {
            if (type === 'error') {
                showErrorToast(message);
            } else if (type === 'success') {
                showSuccessToast(message);
            } else {
                showInfoToast(message);
            }
            return;
        }
        
        // Fallback: create simple toast
        const toast = document.createElement('div');
        toast.className = `plaid-toast fixed top-4 right-4 p-4 rounded-lg text-white z-50 max-w-sm ${
            type === 'error' ? 'bg-red-500' : 
            type === 'success' ? 'bg-green-500' : 
            'bg-blue-500'
        }`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }
    
    /**
     * Redirect to manual upload as fallback
     */
    redirectToManualUpload() {
        window.location.href = '/upload';
    }
    
    /**
     * Get current user's auth token
     */
    getAuthToken() {
        // This would integrate with your existing auth system
        // For Firebase, you'd get the ID token
        if (typeof firebase !== 'undefined' && firebase.auth && firebase.auth().currentUser) {
            return firebase.auth().currentUser.accessToken;
        }
        return localStorage.getItem('authToken') || '';
    }
    
    /**
     * Get current user's name for personalization
     */
    getCurrentUserName() {
        if (typeof firebase !== 'undefined' && firebase.auth && firebase.auth().currentUser) {
            return firebase.auth().currentUser.displayName || 'User';
        }
        return localStorage.getItem('userName') || 'User';
    }
    
    /**
     * Get Plaid environment based on current app environment
     */
    getPlaidEnvironment() {
        // Detect environment from hostname or config
        const hostname = window.location.hostname;
        
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'sandbox';
        }
        if (hostname.includes('staging') || hostname.includes('dev')) {
            return 'development';
        }
        return 'production';
    }
}

// Initialize Plaid Link when script loads
const brainBudgetPlaid = new BrainBudgetPlaidLink();

// Export for global access
window.brainBudgetPlaid = brainBudgetPlaid;
window.BrainBudgetPlaidLink = BrainBudgetPlaidLink;