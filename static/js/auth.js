/**
 * BrainBudget Real Firebase Authentication
 * Production-ready authentication with real Firebase integration
 */

import { 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword, 
    signOut,
    sendPasswordResetEmail,
    onAuthStateChanged,
    updateProfile
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js';

import { 
    doc, 
    setDoc, 
    getDoc 
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js';

class BrainBudgetAuth {
    constructor() {
        this.auth = null;
        this.db = null;
        this.currentUser = null;
        
        // Wait for Firebase to be initialized
        this.waitForFirebase();
    }
    
    async waitForFirebase() {
        const maxAttempts = 20;
        let attempts = 0;
        
        const checkFirebase = () => {
            if (window.firebase && window.firebase.auth && window.firebase.db) {
                this.auth = window.firebase.auth;
                this.db = window.firebase.db;
                this.init();
            } else if (attempts < maxAttempts) {
                attempts++;
                setTimeout(checkFirebase, 100);
            } else {
                console.error('Firebase failed to initialize');
                this.showError('Authentication system failed to load. Please refresh the page.');
            }
        };
        
        checkFirebase();
    }
    
    init() {
        console.log('🔥 Initializing BrainBudget Authentication');
        
        // Listen for auth state changes
        onAuthStateChanged(this.auth, (user) => {
            this.handleAuthStateChange(user);
        });
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log('✅ Authentication system ready');
    }
    
    setupEventListeners() {
        // Login form
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
        
        // Signup form
        const signupForm = document.getElementById('signupForm');
        if (signupForm) {
            signupForm.addEventListener('submit', (e) => this.handleSignup(e));
        }
        
        // Password reset
        const resetForm = document.getElementById('resetForm');
        if (resetForm) {
            resetForm.addEventListener('submit', (e) => this.handlePasswordReset(e));
        }
        
        // Logout buttons
        const logoutBtns = document.querySelectorAll('[data-logout]');
        logoutBtns.forEach(btn => {
            btn.addEventListener('click', () => this.handleLogout());
        });
        
        // Google sign in
        const googleBtn = document.getElementById('googleSignIn');
        if (googleBtn) {
            googleBtn.addEventListener('click', () => this.handleGoogleSignIn());
        }
    }
    
    async handleLogin(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const rememberMe = document.getElementById('rememberMe')?.checked;
        
        if (!email || !password) {
            this.showError('Please fill in all fields! 📝');
            return;
        }
        
        this.showLoading('Signing you in... 🔑');
        
        try {
            const userCredential = await signInWithEmailAndPassword(this.auth, email, password);
            const user = userCredential.user;
            
            // Set session persistence
            if (rememberMe) {
                // Firebase handles persistence automatically
            }
            
            this.showSuccess('Welcome back! 🎉');
            
            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
            
        } catch (error) {
            console.error('Login error:', error);
            this.showError(this.getAuthErrorMessage(error));
        }
    }
    
    async handleSignup(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword')?.value;
        const firstName = document.getElementById('firstName')?.value;
        const lastName = document.getElementById('lastName')?.value;
        
        if (!email || !password) {
            this.showError('Please fill in all required fields! 📝');
            return;
        }
        
        if (confirmPassword && password !== confirmPassword) {
            this.showError('Passwords don\'t match! 🔒');
            return;
        }
        
        if (!this.validatePassword(password)) {
            this.showError('Password must be at least 8 characters with uppercase, lowercase, and numbers! 💪');
            return;
        }
        
        this.showLoading('Creating your account... ✨');
        
        try {
            const userCredential = await createUserWithEmailAndPassword(this.auth, email, password);
            const user = userCredential.user;
            
            // Update user profile
            if (firstName || lastName) {
                await updateProfile(user, {
                    displayName: `${firstName || ''} ${lastName || ''}`.trim()
                });
            }
            
            // Create user document in Firestore
            await this.createUserDocument(user, { firstName, lastName });
            
            this.showSuccess('Account created successfully! Welcome to BrainBudget! 🎉');
            
            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
            
        } catch (error) {
            console.error('Signup error:', error);
            this.showError(this.getAuthErrorMessage(error));
        }
    }
    
    async handlePasswordReset(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        
        if (!email) {
            this.showError('Please enter your email address! 📧');
            return;
        }
        
        this.showLoading('Sending reset email... 📫');
        
        try {
            await sendPasswordResetEmail(this.auth, email);
            this.showSuccess('Password reset email sent! Check your inbox 📬');
            
            setTimeout(() => {
                window.location.href = '/auth/login';
            }, 3000);
            
        } catch (error) {
            console.error('Password reset error:', error);
            this.showError(this.getAuthErrorMessage(error));
        }
    }
    
    async handleLogout() {
        try {
            await signOut(this.auth);
            this.showSuccess('Signed out successfully! See you soon! 👋');
            
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
            
        } catch (error) {
            console.error('Logout error:', error);
            this.showError('Error signing out. Please try again! 🔄');
        }
    }
    
    handleAuthStateChange(user) {
        this.currentUser = user;
        
        if (user) {
            console.log('✅ User signed in:', user.email);
            
            // Update UI for authenticated user
            this.updateAuthUI(true);
            
            // Save auth state to session
            this.saveAuthState(user);
            
        } else {
            console.log('❌ User signed out');
            
            // Update UI for unauthenticated user
            this.updateAuthUI(false);
            
            // Clear auth state
            this.clearAuthState();
            
            // Redirect to login if on protected page
            if (this.isProtectedPage()) {
                window.location.href = '/auth/login';
            }
        }
    }
    
    async createUserDocument(user, additionalData = {}) {
        try {
            const userDocRef = doc(this.db, 'users', user.uid);
            
            const userData = {
                uid: user.uid,
                email: user.email,
                displayName: user.displayName || '',
                createdAt: new Date().toISOString(),
                lastLoginAt: new Date().toISOString(),
                preferences: {
                    notifications: true,
                    reminderFrequency: 'weekly',
                    currency: 'USD'
                },
                ...additionalData
            };
            
            await setDoc(userDocRef, userData);
            console.log('✅ User document created');
            
        } catch (error) {
            console.error('Error creating user document:', error);
        }
    }
    
    validatePassword(password) {
        return password.length >= 8 && 
               /[A-Z]/.test(password) && 
               /[a-z]/.test(password) && 
               /[0-9]/.test(password);
    }
    
    getAuthErrorMessage(error) {
        const errorMessages = {
            'auth/user-not-found': 'No account found with this email. Want to create one? 🤔',
            'auth/wrong-password': 'Incorrect password. Try again or reset it! 🔑',
            'auth/email-already-in-use': 'This email is already registered. Try signing in instead! 📧',
            'auth/weak-password': 'Password is too weak. Make it stronger! 💪',
            'auth/invalid-email': 'Please enter a valid email address! 📧',
            'auth/too-many-requests': 'Too many attempts. Please wait a moment and try again! ⏰',
            'auth/network-request-failed': 'Network error. Check your connection! 🌐',
            'auth/invalid-credential': 'Invalid login credentials. Please check and try again! 🔐'
        };
        
        return errorMessages[error.code] || `Something went wrong: ${error.message} 🤔`;
    }
    
    updateAuthUI(isAuthenticated) {
        // Update navigation
        const authButtons = document.querySelectorAll('[data-auth-required]');
        const guestButtons = document.querySelectorAll('[data-guest-only]');
        
        authButtons.forEach(btn => {
            btn.style.display = isAuthenticated ? 'block' : 'none';
        });
        
        guestButtons.forEach(btn => {
            btn.style.display = isAuthenticated ? 'none' : 'block';
        });
        
        // Update user display
        const userDisplay = document.getElementById('userDisplay');
        if (userDisplay && isAuthenticated) {
            userDisplay.textContent = this.currentUser.email;
        }
    }
    
    saveAuthState(user) {
        sessionStorage.setItem('brainbudget_user', JSON.stringify({
            uid: user.uid,
            email: user.email,
            displayName: user.displayName
        }));
    }
    
    clearAuthState() {
        sessionStorage.removeItem('brainbudget_user');
    }
    
    isProtectedPage() {
        const protectedPaths = ['/dashboard', '/goals', '/advice', '/insights', '/settings'];
        return protectedPaths.some(path => window.location.pathname.startsWith(path));
    }
    
    showLoading(message) {
        this.showToast(message, 'info', 0);
    }
    
    showSuccess(message) {
        this.showToast(message, 'success', 3000);
    }
    
    showError(message) {
        this.showToast(message, 'error', 5000);
    }
    
    showToast(message, type = 'info', duration = 3000) {
        // Remove existing toast
        const existingToast = document.getElementById('auth-toast');
        if (existingToast) {
            existingToast.remove();
        }
        
        const toast = document.createElement('div');
        toast.id = 'auth-toast';
        toast.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm transition-all duration-300`;
        
        const colors = {
            success: 'bg-green-500 text-white',
            error: 'bg-red-500 text-white',
            info: 'bg-blue-500 text-white'
        };
        
        toast.className += ` ${colors[type] || colors.info}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        if (duration > 0) {
            setTimeout(() => {
                toast.classList.add('opacity-0', 'transform', 'translate-x-full');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
    }
    
    async getCurrentUser() {
        return this.currentUser;
    }
    
    async getAuthToken() {
        if (!this.currentUser) return null;
        
        try {
            return await this.currentUser.getIdToken();
        } catch (error) {
            console.error('Error getting auth token:', error);
            return null;
        }
    }
}

// Initialize authentication when module loads
const brainBudgetAuth = new BrainBudgetAuth();

// Export for global access
window.BrainBudgetAuth = brainBudgetAuth;

export default brainBudgetAuth;