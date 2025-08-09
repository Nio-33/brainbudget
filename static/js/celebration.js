/**
 * ADHD-Friendly Celebration System for BrainBudget
 * Provides dopamine-boosting animations and feedback
 */

class CelebrationSystem {
    constructor() {
        this.celebrationQueue = [];
        this.isPlaying = false;
        this.init();
    }
    
    init() {
        this.createCelebrationContainer();
        this.preloadSounds();
    }
    
    createCelebrationContainer() {
        if (document.getElementById('celebration-container')) return;
        
        const container = document.createElement('div');
        container.id = 'celebration-container';
        container.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9999;
            overflow: hidden;
        `;
        document.body.appendChild(container);
    }
    
    preloadSounds() {
        // Create audio context for celebration sounds (optional)
        this.audioContext = null;
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.log('Audio not available, using visual-only celebrations');
        }
    }
    
    // Main celebration trigger
    celebrate(type = 'default', message = '', options = {}) {
        const celebration = {
            type,
            message,
            options: {
                duration: 3000,
                intensity: 'medium',
                sound: true,
                confetti: true,
                animation: 'bounce',
                ...options
            }
        };
        
        this.celebrationQueue.push(celebration);
        this.processQueue();
    }
    
    async processQueue() {
        if (this.isPlaying || this.celebrationQueue.length === 0) return;
        
        this.isPlaying = true;
        const celebration = this.celebrationQueue.shift();
        
        await this.playCelebration(celebration);
        
        this.isPlaying = false;
        
        // Process next celebration after a brief pause
        setTimeout(() => {
            this.processQueue();
        }, 500);
    }
    
    async playCelebration(celebration) {
        const { type, message, options } = celebration;
        
        // Play multiple celebration elements in parallel
        const promises = [];
        
        if (options.confetti) {
            promises.push(this.showConfetti(type, options));
        }
        
        if (message) {
            promises.push(this.showMessage(message, options));
        }
        
        if (options.sound) {
            promises.push(this.playSound(type, options));
        }
        
        promises.push(this.showAnimation(type, options));
        
        await Promise.all(promises);
    }
    
    // Confetti animation
    async showConfetti(type, options) {
        const colors = {
            'goal_achieved': ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'],
            'milestone': ['#667eea', '#764ba2', '#f093fb', '#f5576c'],
            'streak': ['#4facfe', '#00f2fe', '#fa709a', '#fee140'],
            'default': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA726', '#AB47BC']
        };
        
        const confettiColors = colors[type] || colors.default;
        const intensity = options.intensity === 'high' ? 100 : options.intensity === 'low' ? 30 : 60;
        
        return new Promise((resolve) => {
            this.createConfettiParticles(confettiColors, intensity);
            setTimeout(resolve, options.duration * 0.8);
        });
    }
    
    createConfettiParticles(colors, count) {
        const container = document.getElementById('celebration-container');
        
        for (let i = 0; i < count; i++) {
            const particle = document.createElement('div');
            particle.style.cssText = `
                position: absolute;
                width: ${Math.random() * 10 + 5}px;
                height: ${Math.random() * 10 + 5}px;
                background: ${colors[Math.floor(Math.random() * colors.length)]};
                border-radius: ${Math.random() > 0.5 ? '50%' : '0'};
                left: ${Math.random() * 100}%;
                top: -20px;
                transform: rotate(${Math.random() * 360}deg);
                animation: confettiFall ${Math.random() * 2 + 1}s linear forwards;
            `;
            
            container.appendChild(particle);
            
            // Remove particle after animation
            setTimeout(() => {
                if (particle.parentNode) {
                    particle.parentNode.removeChild(particle);
                }
            }, 3000);
        }
    }
    
    // Message display
    async showMessage(message, options) {
        return new Promise((resolve) => {
            const messageEl = document.createElement('div');
            messageEl.innerHTML = `
                <div style="
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) scale(0);
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 1.5rem 2rem;
                    border-radius: 1rem;
                    font-size: 1.25rem;
                    font-weight: 600;
                    text-align: center;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
                    animation: celebrationPop 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards,
                               celebrationFadeOut 0.5s ease-in ${options.duration - 500}ms forwards;
                    z-index: 10000;
                ">
                    ${message}
                </div>
            `;
            
            document.body.appendChild(messageEl);
            
            setTimeout(() => {
                if (messageEl.parentNode) {
                    messageEl.parentNode.removeChild(messageEl);
                }
                resolve();
            }, options.duration);
        });
    }
    
    // Sound generation
    async playSound(type, options) {
        if (!this.audioContext) return;
        
        const soundPatterns = {
            'goal_achieved': [
                { freq: 523.25, duration: 0.2 }, // C5
                { freq: 659.25, duration: 0.2 }, // E5
                { freq: 783.99, duration: 0.4 }  // G5
            ],
            'milestone': [
                { freq: 440, duration: 0.15 },   // A4
                { freq: 554.37, duration: 0.15 }, // C#5
                { freq: 659.25, duration: 0.3 }   // E5
            ],
            'streak': [
                { freq: 261.63, duration: 0.1 }, // C4
                { freq: 329.63, duration: 0.1 }, // E4
                { freq: 392.00, duration: 0.1 }, // G4
                { freq: 523.25, duration: 0.2 }  // C5
            ],
            'default': [
                { freq: 523.25, duration: 0.2 }, // C5
                { freq: 659.25, duration: 0.3 }  // E5
            ]
        };
        
        const pattern = soundPatterns[type] || soundPatterns.default;
        
        return new Promise((resolve) => {
            let delay = 0;
            pattern.forEach((note, index) => {
                setTimeout(() => {
                    this.playTone(note.freq, note.duration);
                    if (index === pattern.length - 1) {
                        setTimeout(resolve, note.duration * 1000);
                    }
                }, delay);
                delay += note.duration * 1000;
            });
        });
    }
    
    playTone(frequency, duration) {
        if (!this.audioContext) return;
        
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);
        
        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration);
    }
    
    // Animation effects
    async showAnimation(type, options) {
        const animations = {
            'goal_achieved': this.goalAchievedAnimation,
            'milestone': this.milestoneAnimation,
            'streak': this.streakAnimation,
            'upload_success': this.uploadSuccessAnimation,
            'default': this.defaultAnimation
        };
        
        const animationFn = animations[type] || animations.default;
        return animationFn.call(this, options);
    }
    
    async goalAchievedAnimation(options) {
        // Screen flash effect
        const flash = document.createElement('div');
        flash.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #FFD700, #FFA726);
            opacity: 0;
            animation: screenFlash 0.8s ease-out;
            z-index: 9998;
        `;
        
        document.body.appendChild(flash);
        
        setTimeout(() => {
            if (flash.parentNode) {
                flash.parentNode.removeChild(flash);
            }
        }, 800);
        
        return new Promise(resolve => setTimeout(resolve, 800));
    }
    
    async milestoneAnimation(options) {
        // Ripple effect from center
        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            width: 20px;
            height: 20px;
            border: 3px solid #667eea;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            animation: rippleExpand 1s ease-out;
            z-index: 9998;
        `;
        
        document.body.appendChild(ripple);
        
        setTimeout(() => {
            if (ripple.parentNode) {
                ripple.parentNode.removeChild(ripple);
            }
        }, 1000);
        
        return new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    async streakAnimation(options) {
        // Multiple sparkles
        const container = document.getElementById('celebration-container');
        
        for (let i = 0; i < 20; i++) {
            setTimeout(() => {
                const sparkle = document.createElement('div');
                sparkle.innerHTML = '✨';
                sparkle.style.cssText = `
                    position: absolute;
                    font-size: ${Math.random() * 20 + 15}px;
                    left: ${Math.random() * 100}%;
                    top: ${Math.random() * 100}%;
                    animation: sparkleFloat 2s ease-out forwards;
                    z-index: 9999;
                `;
                
                container.appendChild(sparkle);
                
                setTimeout(() => {
                    if (sparkle.parentNode) {
                        sparkle.parentNode.removeChild(sparkle);
                    }
                }, 2000);
            }, i * 100);
        }
        
        return new Promise(resolve => setTimeout(resolve, 2200));
    }
    
    async uploadSuccessAnimation(options) {
        // Gentle pulsing check mark
        const checkmark = document.createElement('div');
        checkmark.innerHTML = '✅';
        checkmark.style.cssText = `
            position: fixed;
            top: 30%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 4rem;
            animation: checkmarkPulse 1.5s ease-out;
            z-index: 9999;
        `;
        
        document.body.appendChild(checkmark);
        
        setTimeout(() => {
            if (checkmark.parentNode) {
                checkmark.parentNode.removeChild(checkmark);
            }
        }, 1500);
        
        return new Promise(resolve => setTimeout(resolve, 1500));
    }
    
    async defaultAnimation(options) {
        // Simple bounce animation
        const emoji = document.createElement('div');
        emoji.innerHTML = '🎉';
        emoji.style.cssText = `
            position: fixed;
            top: 20%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 3rem;
            animation: bounceIn 1s ease-out;
            z-index: 9999;
        `;
        
        document.body.appendChild(emoji);
        
        setTimeout(() => {
            if (emoji.parentNode) {
                emoji.parentNode.removeChild(emoji);
            }
        }, 1000);
        
        return new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    // Convenience methods for common celebrations
    celebrateGoalAchieved(goalName, amount) {
        this.celebrate('goal_achieved', `🎉 Goal Achieved!\n${goalName}\n$${amount}`, {
            intensity: 'high',
            duration: 4000
        });
    }
    
    celebrateMilestone(milestone) {
        this.celebrate('milestone', `🌟 Milestone Reached!\n${milestone}`, {
            intensity: 'medium',
            duration: 3000
        });
    }
    
    celebrateStreak(days) {
        this.celebrate('streak', `🔥 ${days} Day Streak!\nYou're on fire!`, {
            intensity: 'medium',
            duration: 2500
        });
    }
    
    celebrateUpload() {
        this.celebrate('upload_success', '📊 Analysis Complete!\nGreat job tracking your spending!', {
            intensity: 'low',
            duration: 2000
        });
    }
    
    celebrateProgress(message) {
        this.celebrate('default', `💪 ${message}`, {
            intensity: 'low',
            duration: 2000
        });
    }
    
    // Micro celebrations for small wins
    microCelebration(emoji = '🎉') {
        const microEl = document.createElement('div');
        microEl.innerHTML = emoji;
        microEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            font-size: 2rem;
            animation: microBounce 0.8s ease-out;
            z-index: 9999;
            pointer-events: none;
        `;
        
        document.body.appendChild(microEl);
        
        setTimeout(() => {
            if (microEl.parentNode) {
                microEl.parentNode.removeChild(microEl);
            }
        }, 800);
    }
}

// CSS animations as a style block
const celebrationStyles = document.createElement('style');
celebrationStyles.textContent = `
    @keyframes confettiFall {
        0% {
            transform: translateY(-20px) rotate(0deg);
            opacity: 1;
        }
        100% {
            transform: translateY(100vh) rotate(720deg);
            opacity: 0;
        }
    }
    
    @keyframes celebrationPop {
        0% {
            transform: translate(-50%, -50%) scale(0);
            opacity: 0;
        }
        100% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
        }
    }
    
    @keyframes celebrationFadeOut {
        0% {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
        100% {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.8);
        }
    }
    
    @keyframes screenFlash {
        0% { opacity: 0; }
        50% { opacity: 0.3; }
        100% { opacity: 0; }
    }
    
    @keyframes rippleExpand {
        0% {
            width: 20px;
            height: 20px;
            opacity: 1;
        }
        100% {
            width: 300px;
            height: 300px;
            opacity: 0;
        }
    }
    
    @keyframes sparkleFloat {
        0% {
            transform: translateY(0px) scale(0);
            opacity: 1;
        }
        50% {
            opacity: 1;
            transform: translateY(-20px) scale(1);
        }
        100% {
            transform: translateY(-40px) scale(0);
            opacity: 0;
        }
    }
    
    @keyframes checkmarkPulse {
        0% {
            transform: translate(-50%, -50%) scale(0);
            opacity: 0;
        }
        50% {
            transform: translate(-50%, -50%) scale(1.2);
            opacity: 1;
        }
        100% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
        }
    }
    
    @keyframes bounceIn {
        0% {
            transform: translate(-50%, -50%) scale(0);
            opacity: 0;
        }
        60% {
            transform: translate(-50%, -50%) scale(1.2);
            opacity: 1;
        }
        100% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
        }
    }
    
    @keyframes microBounce {
        0%, 20%, 53%, 80%, 100% {
            transform: translate3d(0,0,0);
        }
        40%, 43% {
            transform: translate3d(0, -15px, 0);
        }
        70% {
            transform: translate3d(0, -7px, 0);
        }
        90% {
            transform: translate3d(0, -3px, 0);
        }
    }
    
    /* Reduced motion support */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
`;

document.head.appendChild(celebrationStyles);

// Initialize global celebration system
window.CelebrationSystem = CelebrationSystem;
window.celebrations = new CelebrationSystem();