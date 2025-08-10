/**
 * BrainBudget Authentication - Firebase-Only Auth System
 * Clean Firebase authentication with comprehensive security and ADHD-friendly UX
 */

class BrainBudgetAuth {
  constructor() {
    // Authentication state
    this.currentStep = 1;
    this.totalSteps = 3;
    this.authMode = 'login'; // 'login', 'register', 'reset'
    this.rememberMe = false;
    
    // Security features
    this.failedAttempts = 0;
    this.maxFailedAttempts = 5;
    this.lockoutTimeRemaining = 0;
    this.lockoutTimer = null;
    
    // Password strength requirements
    this.passwordRequirements = {
      minLength: 8,
      hasUpperCase: false,
      hasLowerCase: false,
      hasNumbers: false,
      hasSpecialChars: false
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.init());
    } else {
      this.init();
    }
  }
  
  /**
   * Initialize the authentication system
   */
  async init() {
    try {
      // Set up event listeners
      this.setupEventListeners();
      
      // Restore saved authentication state
      this.restoreAuthState();
      
      // Authentication initialized successfully
    } catch (error) {
      console.error('Failed to initialize authentication:', error);
      this.showMessage('error', 'Authentication system failed to start. Please refresh the page!');
    }
  }
  
  /**
   * Set up all event listeners
   */
  setupEventListeners() {
    // Form submissions
    document.getElementById('login-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleLogin();
    });
    
    document.getElementById('signup-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleRegister();
    });
    
    // Google Sign-In buttons
    document.getElementById('google-signin-btn')?.addEventListener('click', () => {
      this.handleGoogleSignIn();
    });
    
    document.getElementById('google-signup-btn')?.addEventListener('click', () => {
      this.handleGoogleSignIn();
    });
    
    // Password strength checking
    const passwordInput = document.getElementById('password');
    if (passwordInput) {
      passwordInput.addEventListener('input', (e) => {
        this.checkPasswordStrength(e.target.value);
      });
    }
    
    // Password visibility toggle
    document.querySelectorAll('.auth-password-toggle').forEach(button => {
      button.addEventListener('click', this.togglePasswordVisibility);
    });
    
    // Remember me checkbox
    document.getElementById('remember-me')?.addEventListener('change', (e) => {
      this.rememberMe = e.target.checked;
    });
    
    // Logout buttons
    document.querySelectorAll('[data-action="logout"]').forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        this.handleLogout();
      });
    });
    
    // Real-time validation
    this.setupRealTimeValidation();
    
    // Keyboard shortcuts for accessibility
    document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
  }
  
  /**
   * Handle login form submission
   */
  async handleLogin() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    
    if (!this.validateEmail(email) || !password) {
      this.showMessage('error', 'Please fill in all fields correctly! 📝');
      return;
    }
    
    // Check if account is locked
    if (this.isAccountLocked()) {
      this.showLockoutMessage();
      return;
    }
    
    this.setButtonLoading('login-btn', true);
    
    try {
      // Firebase login
      const result = await this.firebaseLogin(email, password);
      
      // Reset failed attempts on successful login
      this.failedAttempts = 0;
      localStorage.removeItem('authFailedAttempts');
      
      this.showMessage('success', 'Welcome back! Ready to manage your finances? 🎉');
      
      // Store remember me preference
      if (this.rememberMe) {
        localStorage.setItem('authRememberMe', 'true');
        localStorage.setItem('authEmail', email);
      }
      
      // Redirect to homepage
      setTimeout(() => {
        window.location.href = '/';
      }, 1500);
      
    } catch (error) {
      this.handleAuthError(error);
      this.failedAttempts++;
      localStorage.setItem('authFailedAttempts', this.failedAttempts.toString());
      
      if (this.failedAttempts >= this.maxFailedAttempts) {
        this.lockAccount();
      }
    } finally {
      this.setButtonLoading('login-btn', false);
    }
  }
  
  /**
   * Handle registration form submission
   */
  async handleRegister() {
    // Collect form data
    const formData = this.collectRegistrationData();
    
    if (!this.validateRegistrationData(formData)) {
      return;
    }
    
    this.setButtonLoading('create-account-btn', true);
    
    try {
      // Firebase registration
      const result = await this.firebaseRegister(formData);
      
      this.showMessage('success', 'Account created successfully! Welcome to BrainBudget! 🎉');
      
      // Redirect to homepage
      setTimeout(() => {
        window.location.href = '/?welcome=true';
      }, 2000);
      
    } catch (error) {
      this.handleAuthError(error);
    } finally {
      this.setButtonLoading('create-account-btn', false);
    }
  }
  
  /**
   * Handle logout
   */
  async handleLogout() {
    try {
      // Show loading state if there's a logout button
      const logoutBtn = document.querySelector('[data-action="logout"]');
      if (logoutBtn) {
        this.setButtonLoading(logoutBtn.id || 'logout-btn', true);
      }

      // First, call backend logout if user is authenticated
      if (window.firebase && firebase.auth && firebase.auth().currentUser) {
        try {
          const idToken = await firebase.auth().currentUser.getIdToken();
          await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${idToken}`,
              'Content-Type': 'application/json'
            }
          });
        } catch (error) {
          console.warn('Backend logout failed, proceeding with Firebase logout:', error);
        }

        // Firebase sign out
        await firebase.auth().signOut();
      }

      // Clear local storage
      localStorage.removeItem('authRememberMe');
      localStorage.removeItem('authEmail');
      localStorage.removeItem('authFailedAttempts');
      localStorage.removeItem('authLockoutTime');

      this.showMessage('success', 'You\'ve been logged out successfully. Thanks for using BrainBudget! 👋');

      // Redirect to login page
      setTimeout(() => {
        window.location.href = '/auth/login';
      }, 1500);

    } catch (error) {
      console.error('Logout error:', error);
      this.showMessage('error', 'Logout completed anyway! See you soon! 👋');
      
      // Still redirect even if there was an error
      setTimeout(() => {
        window.location.href = '/auth/login';
      }, 2000);
    }
  }

  /**
   * Handle Google Sign-In
   */
  async handleGoogleSignIn() {
    const buttonId = document.getElementById('google-signin-btn') ? 'google-signin-btn' : 'google-signup-btn';
    this.setButtonLoading(buttonId, true);
    
    try {
      const result = await this.firebaseGoogleSignIn();
      
      this.showMessage('success', 'Signed in with Google successfully! 🎉');
      
      setTimeout(() => {
        window.location.href = '/';
      }, 1500);
      
    } catch (error) {
      this.handleAuthError(error);
    } finally {
      this.setButtonLoading(buttonId, false);
    }
  }
  
  /**
   * Firebase login
   */
  async firebaseLogin(email, password) {
    if (!window.firebaseAuth || !window.signInWithEmailAndPassword) {
      throw new Error('Firebase not initialized. Please refresh the page.');
    }
    
    // Authenticating with Firebase
    const userCredential = await window.signInWithEmailAndPassword(window.firebaseAuth, email, password);
    const user = userCredential.user;
    
    // Get ID token for backend verification
    const idToken = await user.getIdToken();
    
    // Verify with backend
    const response = await fetch('/api/auth/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ id_token: idToken })
    });
    
    if (!response.ok) {
      throw new Error('Backend verification failed');
    }
    
    const result = await response.json();
    
    if (!result.success) {
      throw new Error(result.error || 'Backend verification failed');
    }
    
    return {
      uid: user.uid,
      email: user.email,
      displayName: user.displayName,
      emailVerified: user.emailVerified
    };
  }
  
  /**
   * Firebase registration
   */
  async firebaseRegister(formData) {
    if (!window.firebaseAuth || !window.createUserWithEmailAndPassword) {
      throw new Error('Firebase not initialized. Please refresh the page.');
    }
    
    const userCredential = await window.createUserWithEmailAndPassword(
      window.firebaseAuth,
      formData.email,
      formData.password
    );
    const user = userCredential.user;
    
    // Update profile with display name
    if (formData.fullName && window.updateProfile) {
      await window.updateProfile(user, {
        displayName: formData.fullName
      });
    }
    
    // Get ID token for backend verification
    const idToken = await user.getIdToken();
    
    // Create user profile on backend
    const response = await fetch('/api/auth/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ id_token: idToken })
    });
    
    if (!response.ok) {
      throw new Error('Backend verification failed');
    }
    
    const result = await response.json();
    
    if (!result.success) {
      throw new Error(result.error || 'Backend verification failed');
    }
    
    return {
      uid: user.uid,
      email: user.email,
      displayName: user.displayName || formData.fullName,
      emailVerified: user.emailVerified
    };
  }
  
  /**
   * Firebase Google Sign-In
   */
  async firebaseGoogleSignIn() {
    if (!window.firebaseAuth || !window.signInWithPopup || !window.googleProvider) {
      throw new Error('Google Sign-In not available. Please use email/password.');
    }
    
    // Starting Google Sign-In
    const result = await window.signInWithPopup(window.firebaseAuth, window.googleProvider);
    const user = result.user;
    
    // Get ID token for backend verification
    const idToken = await user.getIdToken();
    
    // Verify with backend
    const response = await fetch('/api/auth/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ id_token: idToken })
    });
    
    if (!response.ok) {
      throw new Error('Backend verification failed');
    }
    
    const backendResult = await response.json();
    
    if (!backendResult.success) {
      throw new Error(backendResult.error || 'Backend verification failed');
    }
    
    return {
      uid: user.uid,
      email: user.email,
      displayName: user.displayName,
      photoURL: user.photoURL,
      emailVerified: user.emailVerified
    };
  }
  
  /**
   * Check password strength and provide visual feedback
   */
  checkPasswordStrength(password) {
    const strength = this.calculatePasswordStrength(password);
    const strengthBar = document.querySelector('.password-strength-fill');
    const strengthLabel = document.querySelector('.password-strength-label');
    const requirements = document.querySelectorAll('.password-requirement');
    
    if (!strengthBar || !strengthLabel) return;
    
    // Update strength bar
    strengthBar.className = `password-strength-fill ${strength.level}`;
    
    // Update strength label
    const labels = {
      weak: '🔐 Weak - Let\'s make it stronger!',
      fair: '🔒 Fair - Getting better!',
      good: '✅ Good - Almost there!',
      strong: '🛡️ Strong - Perfect!'
    };
    
    strengthLabel.innerHTML = labels[strength.level] || labels.weak;
    
    // Update requirements checklist
    requirements.forEach((req, index) => {
      const requirement = [
        password.length >= this.passwordRequirements.minLength,
        /[a-z]/.test(password),
        /[A-Z]/.test(password),
        /\d/.test(password),
        /[!@#$%^&*(),.?\":{}|<>]/.test(password)
      ][index];
      
      if (requirement) {
        req.classList.add('met');
        req.querySelector('.password-requirement-icon').textContent = '✅';
      } else {
        req.classList.remove('met');
        req.querySelector('.password-requirement-icon').textContent = '⭕';
      }
    });
    
    return strength;
  }
  
  /**
   * Calculate password strength score
   */
  calculatePasswordStrength(password) {
    let score = 0;
    
    if (password.length >= 8) score += 20;
    if (password.length >= 12) score += 10;
    if (/[a-z]/.test(password)) score += 15;
    if (/[A-Z]/.test(password)) score += 15;
    if (/\d/.test(password)) score += 15;
    if (/[!@#$%^&*(),.?\":{}|<>]/.test(password)) score += 15;
    if (password.length >= 16) score += 10;
    
    let level = 'weak';
    if (score >= 85) level = 'strong';
    else if (score >= 65) level = 'good';
    else if (score >= 40) level = 'fair';
    
    return { score, level };
  }
  
  /**
   * Toggle password visibility
   */
  togglePasswordVisibility(event) {
    const button = event.target.closest('.auth-password-toggle');
    const input = button.parentElement.querySelector('.auth-input');
    
    if (input.type === 'password') {
      input.type = 'text';
      button.textContent = '🙈';
      button.setAttribute('aria-label', 'Hide password');
    } else {
      input.type = 'password';
      button.textContent = '👁️';
      button.setAttribute('aria-label', 'Show password');
    }
  }
  
  /**
   * Validate email format
   */
  validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
  
  /**
   * Set button loading state
   */
  setButtonLoading(buttonId, loading) {
    const button = document.getElementById(buttonId);
    if (!button) return;
    
    if (loading) {
      button.classList.add('auth-button-loading');
      button.disabled = true;
      const originalText = button.innerHTML;
      button.setAttribute('data-original-text', originalText);
      button.innerHTML = '<span>Loading... ⏳</span>';
    } else {
      button.classList.remove('auth-button-loading');
      button.disabled = false;
      const originalText = button.getAttribute('data-original-text');
      if (originalText) {
        button.innerHTML = originalText;
      }
    }
  }
  
  /**
   * Show message to user
   */
  showMessage(type, message) {
    const messageContainer = document.getElementById('auth-messages');
    if (!messageContainer) return;
    
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };
    
    const messageElement = document.createElement('div');
    messageElement.className = `auth-message ${type}`;
    messageElement.innerHTML = `
      <span class=\"auth-message-icon\">${icons[type] || icons.info}</span>
      <div>${message}</div>
    `;
    
    // Clear previous messages
    messageContainer.innerHTML = '';
    messageContainer.appendChild(messageElement);
    
    // Auto-remove success messages after 5 seconds
    if (type === 'success') {
      setTimeout(() => {
        if (messageElement.parentNode) {
          messageElement.remove();
        }
      }, 5000);
    }
    
    // Announce to screen readers
    this.announceToScreenReader(`${type}: ${message}`);
    
    // Scroll message into view
    messageElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  
  /**
   * Handle authentication errors with friendly messages
   */
  handleAuthError(error) {
    console.error('Auth error:', error);
    
    const friendlyMessages = {
      'auth/user-not-found': 'We couldn\'t find an account with that email. Please check your email or create a new account! 🤔',
      'auth/wrong-password': 'That password doesn\'t look right. Please try again or reset your password! 🔑',
      'auth/email-already-in-use': 'That email is already registered. Try logging in instead! 👋',
      'auth/weak-password': 'Please choose a stronger password for better security! 💪',
      'auth/invalid-email': 'That email format doesn\'t look right. Please double-check! 📧',
      'auth/network-request-failed': 'Connection issue! Please check your internet and try again 📶',
      'auth/too-many-requests': 'Too many attempts. Please wait a moment and try again ⏰',
      'auth/popup-closed-by-user': 'Google Sign-In was cancelled. No problem, try again when ready! 👋',
      'auth/popup-blocked': 'Popup blocked! Please allow popups for this site and try again 🚫'
    };
    
    const message = friendlyMessages[error.code] ||
      error.message ||
      'Something went wrong. Don\'t worry, let\'s try again! 🔄';
    
    this.showMessage('error', message);
  }
  
  /**
   * Check if account is locked due to failed attempts
   */
  isAccountLocked() {
    const lastLockout = localStorage.getItem('authLockoutTime');
    if (!lastLockout) return false;
    
    const lockoutTime = parseInt(lastLockout);
    const now = Date.now();
    const lockoutDuration = 15 * 60 * 1000; // 15 minutes
    
    return (now - lockoutTime) < lockoutDuration;
  }
  
  /**
   * Lock account after too many failed attempts
   */
  lockAccount() {
    const lockoutTime = Date.now();
    localStorage.setItem('authLockoutTime', lockoutTime.toString());
    this.showLockoutMessage();
  }
  
  /**
   * Show account lockout message
   */
  showLockoutMessage() {
    this.showMessage('error', '🔒 Too many failed attempts. Please wait 15 minutes or reset your password.');
  }
  
  /**
   * Set up real-time field validation
   */
  setupRealTimeValidation() {
    // Email validation
    document.getElementById('email')?.addEventListener('blur', (e) => {
      this.validateField(e.target, this.validateEmail(e.target.value), 'Please enter a valid email address');
    });
    
    // Password confirmation
    document.getElementById('confirm-password')?.addEventListener('input', (e) => {
      const password = document.getElementById('password')?.value;
      this.validateField(e.target, e.target.value === password, 'Passwords don\'t match');
    });
  }
  
  /**
   * Validate individual form field
   */
  validateField(field, isValid, errorMessage) {
    if (isValid) {
      field.classList.remove('error');
      field.classList.add('success');
    } else {
      field.classList.remove('success');
      field.classList.add('error');
    }
    
    return isValid;
  }
  
  /**
   * Collect registration form data
   */
  collectRegistrationData() {
    return {
      email: document.getElementById('email')?.value.trim(),
      password: document.getElementById('password')?.value,
      fullName: document.getElementById('full-name')?.value.trim(),
      acceptTerms: document.getElementById('accept-terms')?.checked,
      newsletterOptIn: document.getElementById('newsletter-opt-in')?.checked
    };
  }
  
  /**
   * Validate complete registration data
   */
  validateRegistrationData(data) {
    const errors = [];
    
    if (!data.fullName || data.fullName.trim() === '') {
      errors.push('Please enter your name');
    }
    
    if (!this.validateEmail(data.email)) {
      errors.push('Please enter a valid email address');
    }
    
    if (!data.password || this.calculatePasswordStrength(data.password).score < 40) {
      errors.push('Please create a stronger password');
    }
    
    const confirmPassword = document.getElementById('confirm-password')?.value;
    if (data.password !== confirmPassword) {
      errors.push('Passwords do not match');
    }
    
    if (!data.acceptTerms) {
      errors.push('Please accept the terms of service to continue');
    }
    
    if (errors.length > 0) {
      this.showMessage('error', errors.join('. ') + '.');
      return false;
    }
    
    return true;
  }
  
  /**
   * Handle keyboard shortcuts for accessibility
   */
  handleKeyboardShortcuts(event) {
    // Enter key on focused buttons
    if (event.key === 'Enter' && document.activeElement.classList.contains('auth-button')) {
      document.activeElement.click();
    }
    
    // Escape key to clear messages
    if (event.key === 'Escape') {
      const messageContainer = document.getElementById('auth-messages');
      if (messageContainer) {
        messageContainer.innerHTML = '';
      }
    }
  }
  
  /**
   * Announce messages to screen readers
   */
  announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
      if (document.body.contains(announcement)) {
        document.body.removeChild(announcement);
      }
    }, 1000);
  }
  
  /**
   * Restore authentication state from localStorage
   */
  restoreAuthState() {
    // Restore remember me setting
    const rememberMe = localStorage.getItem('authRememberMe') === 'true';
    if (rememberMe) {
      const savedEmail = localStorage.getItem('authEmail');
      const emailField = document.getElementById('email');
      const rememberCheckbox = document.getElementById('remember-me');
      
      if (emailField && savedEmail) {
        emailField.value = savedEmail;
      }
      
      if (rememberCheckbox) {
        rememberCheckbox.checked = true;
        this.rememberMe = true;
      }
    }
    
    // Check for account lockout
    if (this.isAccountLocked()) {
      this.showLockoutMessage();
    }
    
    // Restore failed attempts counter
    this.failedAttempts = parseInt(localStorage.getItem('authFailedAttempts') || '0');
  }
}

// Initialize authentication system
const brainBudgetAuth = new BrainBudgetAuth();

// Export for global access
window.brainBudgetAuth = brainBudgetAuth;