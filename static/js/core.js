/**
 * Core JavaScript functionality for BrainBudget
 * Handles common utilities, API calls, and user-friendly interactions
 */

// Global utilities and helpers
window.BrainBudget = {
    // API configuration
    API: {
        BASE_URL: '/api',
        TIMEOUT: 30000, // 30 seconds
        
        // Make API request with proper error handling
        async request(endpoint, options = {}) {
            const url = `${this.BASE_URL}${endpoint}`;
            const config = {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            };
            
            try {
                showLoadingState(true);
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.TIMEOUT);
                
                const response = await fetch(url, {
                    ...config,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                return data;
            } catch (error) {
                if (error.name === 'AbortError') {
                    showErrorToast('Request timed out. Please try again.');
                } else {
                    showErrorToast(error.message || 'Something went wrong');
                }
                throw error;
            } finally {
                showLoadingState(false);
            }
        },
        
        // Specific API methods
        uploadFile(file, onProgress) {
            return new Promise((resolve, reject) => {
                const formData = new FormData();
                formData.append('file', file);
                
                const xhr = new XMLHttpRequest();
                
                xhr.upload.onprogress = (event) => {
                    if (event.lengthComputable && onProgress) {
                        const progress = (event.loaded / event.total) * 100;
                        onProgress(progress);
                    }
                };
                
                xhr.onload = () => {
                    if (xhr.status === 200) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            resolve(response);
                        } catch (e) {
                            reject(new Error('Invalid response format'));
                        }
                    } else {
                        reject(new Error(`Upload failed: ${xhr.statusText}`));
                    }
                };
                
                xhr.onerror = () => reject(new Error('Network error'));
                xhr.ontimeout = () => reject(new Error('Upload timeout'));
                
                xhr.timeout = this.TIMEOUT;
                xhr.open('POST', `${this.BASE_URL}/upload`);
                xhr.send(formData);
            });
        }
    },
    
    // User-friendly utilities
    Utils: {
        // Debounce function to prevent excessive API calls
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        // Format currency with proper locale
        formatCurrency(amount, currency = 'USD') {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency
            }).format(amount);
        },
        
        // Format dates in a readable way
        formatDate(date) {
            return new Intl.DateTimeFormat('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            }).format(new Date(date));
        },
        
        // Validate file size and type
        validateFile(file, maxSizeMB = 16, allowedTypes = ['pdf', 'jpg', 'jpeg', 'png']) {
            const errors = [];
            
            // Check file size
            const maxSizeBytes = maxSizeMB * 1024 * 1024;
            if (file.size > maxSizeBytes) {
                errors.push(`File size must be less than ${maxSizeMB}MB`);
            }
            
            // Check file type
            const fileExtension = file.name.split('.').pop().toLowerCase();
            if (!allowedTypes.includes(fileExtension)) {
                errors.push(`File type must be: ${allowedTypes.join(', ')}`);
            }
            
            return {
                valid: errors.length === 0,
                errors: errors
            };
        },
        
        // Generate readable file size
        formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    },
    
    // Local storage helpers
    Storage: {
        set(key, value) {
            try {
                localStorage.setItem(`brainbudget_${key}`, JSON.stringify(value));
            } catch (error) {
                console.warn('Failed to save to localStorage:', error);
            }
        },
        
        get(key) {
            try {
                const item = localStorage.getItem(`brainbudget_${key}`);
                return item ? JSON.parse(item) : null;
            } catch (error) {
                console.warn('Failed to read from localStorage:', error);
                return null;
            }
        },
        
        remove(key) {
            try {
                localStorage.removeItem(`brainbudget_${key}`);
            } catch (error) {
                console.warn('Failed to remove from localStorage:', error);
            }
        }
    },
    
    // Theme management
    Theme: {
        apply(settings) {
            const root = document.documentElement;
            
            // Apply reduced motion
            if (settings.reduceMotion) {
                root.style.setProperty('--animation-duration', '0.01ms');
            } else {
                root.style.removeProperty('--animation-duration');
            }
            
            // Apply theme
            root.classList.toggle('dark', settings.theme === 'dark');
            
            // Apply font size
            const fontSizes = {
                'small': '14px',
                'medium': '16px',
                'large': '18px',
                'extra-large': '20px'
            };
            
            if (settings.fontSize && fontSizes[settings.fontSize]) {
                root.style.fontSize = fontSizes[settings.fontSize];
            }
        },
        
        load() {
            const settings = BrainBudget.Storage.get('settings');
            if (settings) {
                this.apply(settings);
            }
        }
    }
};

// Toast notification functions
function showSuccessToast(message, duration = 4000) {
    const toast = document.getElementById('success-toast');
    const messageElement = document.getElementById('success-message');
    
    if (toast && messageElement) {
        messageElement.textContent = message;
        toast.classList.remove('hidden', 'translate-y-full');
        toast.classList.add('translate-y-0');
        
        setTimeout(() => {
            toast.classList.add('translate-y-full');
            toast.classList.remove('translate-y-0');
            setTimeout(() => toast.classList.add('hidden'), 300);
        }, duration);
    }
}

function showErrorToast(message, duration = 5000) {
    const toast = document.getElementById('error-toast');
    const messageElement = document.getElementById('error-message');
    
    if (toast && messageElement) {
        messageElement.textContent = message;
        toast.classList.remove('hidden', 'translate-y-full');
        toast.classList.add('translate-y-0');
        
        setTimeout(() => {
            toast.classList.add('translate-y-full');
            toast.classList.remove('translate-y-0');
            setTimeout(() => toast.classList.add('hidden'), 300);
        }, duration);
    }
}

// Loading state management
function showLoadingState(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        if (show) {
            overlay.classList.remove('hidden');
            overlay.classList.add('flex');
        } else {
            overlay.classList.add('hidden');
            overlay.classList.remove('flex');
        }
    }
}

// Gentle focus management for users
function setGentleFocus(element) {
    if (element && typeof element.focus === 'function') {
        setTimeout(() => {
            element.focus();
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
    }
}

// Form validation with user-friendly messaging
function validateForm(form) {
    const errors = [];
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            const label = form.querySelector(`label[for="${field.id}"]`) || 
                         field.previousElementSibling ||
                         { textContent: field.name || 'This field' };
            errors.push(`${label.textContent} is required`);
            
            // Add gentle visual feedback
            field.classList.add('border-red-300');
            setTimeout(() => field.classList.remove('border-red-300'), 3000);
        }
    });
    
    if (errors.length > 0) {
        showErrorToast(`Please fill in: ${errors.join(', ')}`);
        setGentleFocus(form.querySelector('[required]:invalid, [required][value=""]'));
        return false;
    }
    
    return true;
}

// Initialize core functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Load saved theme settings
    BrainBudget.Theme.load();
    
    // Add gentle hover effects to interactive elements
    document.querySelectorAll('button, a, [role="button"]').forEach(element => {
        element.addEventListener('mouseenter', function() {
            if (!this.disabled) {
                this.style.transform = 'translateY(-1px)';
            }
        });
        
        element.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
    
    // Add keyboard navigation improvements
    document.addEventListener('keydown', function(e) {
        // Escape key closes modals/overlays
        if (e.key === 'Escape') {
            const overlay = document.getElementById('loading-overlay');
            if (overlay && !overlay.classList.contains('hidden')) {
                showLoadingState(false);
            }
        }
    });
    
    // Add form validation to all forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-save form inputs (helpful for users who might navigate away)
    const formInputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea');
    formInputs.forEach(input => {
        const saveKey = `form_${input.name || input.id}`;
        
        // Load saved value
        const savedValue = BrainBudget.Storage.get(saveKey);
        if (savedValue && !input.value) {
            input.value = savedValue;
        }
        
        // Save on change (debounced)
        const debouncedSave = BrainBudget.Utils.debounce(() => {
            if (input.value.trim()) {
                BrainBudget.Storage.set(saveKey, input.value);
            }
        }, 1000);
        
        input.addEventListener('input', debouncedSave);
    });
    
    // Add subtle visual feedback for users
    document.querySelectorAll('input, select, textarea').forEach(element => {
        element.addEventListener('focus', function() {
            this.parentElement?.classList.add('ring-2', 'ring-primary-200');
        });
        
        element.addEventListener('blur', function() {
            this.parentElement?.classList.remove('ring-2', 'ring-primary-200');
        });
    });
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BrainBudget;
}