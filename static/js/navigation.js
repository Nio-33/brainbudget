/**
 * Navigation functionality for BrainBudget
 * Handles mobile menu, active states, and accessible navigation
 */

class Navigation {
    constructor() {
        this.mobileMenuBtn = document.getElementById('mobile-menu-btn');
        this.mobileMenu = document.getElementById('mobile-menu');
        this.navLinks = document.querySelectorAll('.nav-link');
        
        this.init();
    }
    
    init() {
        this.setupMobileMenu();
        this.setupActiveStates();
        this.setupKeyboardNavigation();
        this.setupSmoothScrolling();
    }
    
    setupMobileMenu() {
        if (!this.mobileMenuBtn || !this.mobileMenu) return;
        
        this.mobileMenuBtn.addEventListener('click', () => {
            this.toggleMobileMenu();
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.mobileMenuBtn.contains(e.target) && !this.mobileMenu.contains(e.target)) {
                this.closeMobileMenu();
            }
        });
        
        // Close mobile menu on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.mobileMenu.classList.contains('hidden')) {
                this.closeMobileMenu();
                this.mobileMenuBtn.focus();
            }
        });
        
        // Close mobile menu when clicking on nav links
        this.mobileMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                this.closeMobileMenu();
            });
        });
    }
    
    toggleMobileMenu() {
        const isHidden = this.mobileMenu.classList.contains('hidden');
        
        if (isHidden) {
            this.openMobileMenu();
        } else {
            this.closeMobileMenu();
        }
    }
    
    openMobileMenu() {
        this.mobileMenu.classList.remove('hidden');
        this.mobileMenuBtn.setAttribute('aria-expanded', 'true');
        
        // Update button icon to X
        const icon = this.mobileMenuBtn.querySelector('svg');
        if (icon) {
            icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>';
        }
        
        // Focus first menu item
        const firstLink = this.mobileMenu.querySelector('a');
        if (firstLink) {
            setTimeout(() => firstLink.focus(), 100);
        }
    }
    
    closeMobileMenu() {
        this.mobileMenu.classList.add('hidden');
        this.mobileMenuBtn.setAttribute('aria-expanded', 'false');
        
        // Update button icon back to hamburger
        const icon = this.mobileMenuBtn.querySelector('svg');
        if (icon) {
            icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>';
        }
    }
    
    setupActiveStates() {
        const currentPath = window.location.pathname;
        
        this.navLinks.forEach(link => {
            const linkPath = new URL(link.href).pathname;
            
            // Remove existing active states
            link.classList.remove('text-primary-500', 'font-semibold');
            link.classList.add('text-text-secondary');
            
            // Add active state to current page
            if (linkPath === currentPath || 
                (currentPath === '/' && linkPath === '/') ||
                (currentPath.startsWith(linkPath) && linkPath !== '/')) {
                link.classList.remove('text-text-secondary');
                link.classList.add('text-primary-500', 'font-semibold');
                link.setAttribute('aria-current', 'page');
            }
        });
        
        // Handle mobile menu links
        const mobileLinks = this.mobileMenu?.querySelectorAll('a') || [];
        mobileLinks.forEach(link => {
            const linkPath = new URL(link.href).pathname;
            
            link.classList.remove('text-primary-500', 'font-semibold');
            
            if (linkPath === currentPath || 
                (currentPath === '/' && linkPath === '/') ||
                (currentPath.startsWith(linkPath) && linkPath !== '/')) {
                link.classList.add('text-primary-500', 'font-semibold');
                link.setAttribute('aria-current', 'page');
            }
        });
    }
    
    setupKeyboardNavigation() {
        // Handle arrow key navigation in mobile menu
        if (!this.mobileMenu) return;
        
        const menuLinks = Array.from(this.mobileMenu.querySelectorAll('a'));
        
        menuLinks.forEach((link, index) => {
            link.addEventListener('keydown', (e) => {
                switch (e.key) {
                    case 'ArrowDown':
                        e.preventDefault();
                        const nextIndex = (index + 1) % menuLinks.length;
                        menuLinks[nextIndex].focus();
                        break;
                        
                    case 'ArrowUp':
                        e.preventDefault();
                        const prevIndex = index === 0 ? menuLinks.length - 1 : index - 1;
                        menuLinks[prevIndex].focus();
                        break;
                        
                    case 'Home':
                        e.preventDefault();
                        menuLinks[0].focus();
                        break;
                        
                    case 'End':
                        e.preventDefault();
                        menuLinks[menuLinks.length - 1].focus();
                        break;
                }
            });
        });
    }
    
    setupSmoothScrolling() {
        // Handle anchor links with smooth scrolling
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                const targetId = link.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    e.preventDefault();
                    
                    // Close mobile menu if open
                    this.closeMobileMenu();
                    
                    // Smooth scroll to target
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Update URL without triggering navigation
                    history.replaceState(null, null, `#${targetId}`);
                    
                    // Focus the target for accessibility
                    setTimeout(() => {
                        targetElement.focus();
                        targetElement.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }, 500);
                }
            });
        });
    }
    
    // Method to programmatically highlight nav item
    highlightNavItem(path) {
        this.navLinks.forEach(link => {
            const linkPath = new URL(link.href).pathname;
            
            if (linkPath === path) {
                link.classList.remove('text-text-secondary');
                link.classList.add('text-primary-500', 'font-semibold');
            } else {
                link.classList.remove('text-primary-500', 'font-semibold');
                link.classList.add('text-text-secondary');
            }
        });
    }
}

// Breadcrumb functionality
class Breadcrumb {
    constructor(container) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        if (this.container) {
            this.generate();
        }
    }
    
    generate() {
        const path = window.location.pathname;
        const pathParts = path.split('/').filter(part => part);
        
        if (pathParts.length === 0) {
            this.container.innerHTML = '<span class="text-text-primary font-medium">Home</span>';
            return;
        }
        
        const breadcrumbs = ['<a href="/" class="text-primary-500 hover:text-primary-600 font-medium">Home</a>'];
        
        let currentPath = '';
        pathParts.forEach((part, index) => {
            currentPath += `/${part}`;
            const isLast = index === pathParts.length - 1;
            const displayName = this.formatPathPart(part);
            
            if (isLast) {
                breadcrumbs.push(`<span class="text-text-primary font-medium">${displayName}</span>`);
            } else {
                breadcrumbs.push(`<a href="${currentPath}" class="text-primary-500 hover:text-primary-600 font-medium">${displayName}</a>`);
            }
        });
        
        this.container.innerHTML = breadcrumbs.join(' <span class="text-text-muted mx-2">/</span> ');
    }
    
    formatPathPart(part) {
        // Convert URL parts to readable names
        const partMap = {
            'upload': 'Upload Statement',
            'analysis': 'Analysis Results',
            'dashboard': 'Dashboard',
            'settings': 'Settings'
        };
        
        return partMap[part] || part.charAt(0).toUpperCase() + part.slice(1);
    }
}

// Page transition effects
class PageTransitions {
    constructor() {
        this.setupTransitions();
    }
    
    setupTransitions() {
        // Add loading state to navigation links
        document.querySelectorAll('a:not([href^="#"]):not([target="_blank"])').forEach(link => {
            link.addEventListener('click', (e) => {
                // Don't add loading for external links or same page
                if (link.hostname !== window.location.hostname || 
                    link.pathname === window.location.pathname) {
                    return;
                }
                
                // Show loading state
                const loadingOverlay = document.getElementById('loading-overlay');
                if (loadingOverlay) {
                    loadingOverlay.classList.remove('hidden');
                    loadingOverlay.classList.add('flex');
                }
                
                // Add subtle fade out effect
                document.body.style.opacity = '0.8';
                document.body.style.transition = 'opacity 0.2s ease-out';
            });
        });
        
        // Handle browser back/forward buttons
        window.addEventListener('popstate', () => {
            this.handlePageLoad();
        });
        
        // Handle initial page load
        this.handlePageLoad();
    }
    
    handlePageLoad() {
        // Fade in effect
        document.body.style.opacity = '1';
        document.body.style.transition = 'opacity 0.3s ease-in';
        
        // Hide loading overlay
        setTimeout(() => {
            const loadingOverlay = document.getElementById('loading-overlay');
            if (loadingOverlay) {
                loadingOverlay.classList.add('hidden');
                loadingOverlay.classList.remove('flex');
            }
        }, 100);
    }
}

// Initialize navigation when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize navigation
    const navigation = new Navigation();
    
    // Initialize page transitions
    const pageTransitions = new PageTransitions();
    
    // Initialize breadcrumbs if container exists
    const breadcrumbContainer = document.querySelector('#breadcrumb');
    if (breadcrumbContainer) {
        new Breadcrumb(breadcrumbContainer);
    }
    
    // Add skip link functionality
    const skipLink = document.querySelector('a[href="#main-content"]');
    if (skipLink) {
        skipLink.addEventListener('click', (e) => {
            e.preventDefault();
            const mainContent = document.getElementById('main-content');
            if (mainContent) {
                mainContent.focus();
                mainContent.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
});

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.Navigation = Navigation;
    window.Breadcrumb = Breadcrumb;
    window.PageTransitions = PageTransitions;
}