/**
 * ADHD-Friendly Goal Creation Wizard for BrainBudget
 * Guides users through creating achievable financial goals step by step
 */

class GoalCreationWizard {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 5;
        this.goalData = {};
        this.templates = {};
        
        this.init();
    }
    
    init() {
        this.loadTemplates();
        this.setupEventListeners();
        this.updateProgress();
    }
    
    async loadTemplates() {
        try {
            const response = await fetch('/api/goals/templates', {
                headers: {
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.templates = data.templates;
                this.populateTemplates();
            }
            
        } catch (error) {
            console.error('Error loading goal templates:', error);
            this.showErrorMessage('Had trouble loading goal templates, but you can still create custom goals!');
        }
    }
    
    populateTemplates() {
        const templateContainers = {
            'spending_reduction': document.getElementById('spending-templates'),
            'savings_target': document.getElementById('savings-templates'),
            'debt_reduction': document.getElementById('debt-templates'),
            'emergency_fund': document.getElementById('emergency-templates')
        };
        
        Object.entries(this.templates).forEach(([type, templates]) => {
            const container = templateContainers[type];
            if (!container) return;
            
            container.innerHTML = '';
            
            templates.forEach(template => {
                const templateCard = this.createTemplateCard(template, type);
                container.appendChild(templateCard);
            });
        });
    }
    
    createTemplateCard(template, type) {
        const card = document.createElement('div');
        card.className = 'template-card bg-white border-2 border-gray-200 rounded-xl p-6 cursor-pointer hover:border-primary-500 hover:shadow-md gentle-transition';
        card.dataset.template = JSON.stringify(template);
        card.dataset.type = type;
        
        const difficultyColors = {
            'gentle': 'bg-green-100 text-green-800',
            'moderate': 'bg-blue-100 text-blue-800',
            'ambitious': 'bg-orange-100 text-orange-800'
        };
        
        const difficultyColor = difficultyColors[template.difficulty] || 'bg-gray-100 text-gray-800';
        
        card.innerHTML = `
            <div class="flex items-start justify-between mb-4">
                <h3 class="font-semibold text-text-primary text-lg">${template.name}</h3>
                <span class="px-3 py-1 rounded-full text-xs font-medium ${difficultyColor}">
                    ${template.difficulty}
                </span>
            </div>
            <p class="text-text-secondary mb-4">${template.description}</p>
            <div class="space-y-2 text-sm">
                ${template.target_amount ? `<div class="flex justify-between">
                    <span class="text-text-muted">Target:</span>
                    <span class="font-medium">$${template.target_amount.toLocaleString()}</span>
                </div>` : ''}
                ${template.duration_weeks ? `<div class="flex justify-between">
                    <span class="text-text-muted">Duration:</span>
                    <span class="font-medium">${template.duration_weeks} weeks</span>
                </div>` : ''}
                ${template.milestones_count ? `<div class="flex justify-between">
                    <span class="text-text-muted">Milestones:</span>
                    <span class="font-medium">${template.milestones_count} steps</span>
                </div>` : ''}
            </div>
            ${template.adhd_tips ? `
                <div class="mt-4 p-3 bg-primary-50 rounded-lg border border-primary-200">
                    <div class="flex items-start">
                        <span class="text-primary-500 mr-2">💡</span>
                        <p class="text-sm text-primary-700">${template.adhd_tips}</p>
                    </div>
                </div>
            ` : ''}
        `;
        
        card.addEventListener('click', () => this.selectTemplate(template, type));
        
        return card;
    }
    
    setupEventListeners() {
        // Navigation buttons
        document.getElementById('next-step')?.addEventListener('click', () => this.nextStep());
        document.getElementById('prev-step')?.addEventListener('click', () => this.prevStep());
        document.getElementById('finish-goal')?.addEventListener('click', () => this.createGoal());
        
        // Goal type selection
        document.querySelectorAll('.goal-type-card').forEach(card => {
            card.addEventListener('click', (e) => {
                this.selectGoalType(e.currentTarget.dataset.type);
            });
        });
        
        // Custom goal option
        document.getElementById('custom-goal-option')?.addEventListener('click', () => {
            this.selectCustomGoal();
        });
        
        // Form inputs
        document.getElementById('goal-name')?.addEventListener('input', (e) => {
            this.goalData.name = e.target.value;
            this.validateCurrentStep();
        });
        
        document.getElementById('goal-description')?.addEventListener('input', (e) => {
            this.goalData.description = e.target.value;
        });
        
        document.getElementById('target-amount')?.addEventListener('input', (e) => {
            this.goalData.target_amount = parseFloat(e.target.value) || 0;
            this.updateBreakdownPreview();
            this.validateCurrentStep();
        });
        
        document.getElementById('target-date')?.addEventListener('change', (e) => {
            this.goalData.target_date = e.target.value;
            this.updateBreakdownPreview();
            this.validateCurrentStep();
        });
        
        document.getElementById('difficulty-level')?.addEventListener('change', (e) => {
            this.goalData.difficulty = e.target.value;
            this.updateDifficultyDescription();
        });
        
        // Settings toggles
        document.getElementById('allow-adjustments')?.addEventListener('change', (e) => {
            this.goalData.allow_adjustments = e.target.checked;
        });
        
        document.getElementById('celebration-style')?.addEventListener('change', (e) => {
            this.goalData.celebration_style = e.target.value;
        });
        
        document.getElementById('adhd-tips-enabled')?.addEventListener('change', (e) => {
            this.goalData.adhd_tips_enabled = e.target.checked;
        });
    }
    
    selectGoalType(type) {
        this.goalData.type = type;
        
        // Update UI
        document.querySelectorAll('.goal-type-card').forEach(card => {
            card.classList.remove('border-primary-500', 'bg-primary-50');
            card.classList.add('border-gray-200');
        });
        
        const selectedCard = document.querySelector(`[data-type="${type}"]`);
        if (selectedCard) {
            selectedCard.classList.add('border-primary-500', 'bg-primary-50');
            selectedCard.classList.remove('border-gray-200');
        }
        
        // Show relevant templates
        document.querySelectorAll('.template-section').forEach(section => {
            section.classList.add('hidden');
        });
        
        const templateSection = document.getElementById(`${type}-section`);
        if (templateSection) {
            templateSection.classList.remove('hidden');
        }
        
        this.validateCurrentStep();
    }
    
    selectTemplate(template, type) {
        // Clear previous selection
        document.querySelectorAll('.template-card').forEach(card => {
            card.classList.remove('border-primary-500', 'bg-primary-50');
            card.classList.add('border-gray-200');
        });
        
        // Select this template
        event.currentTarget.classList.add('border-primary-500', 'bg-primary-50');
        event.currentTarget.classList.remove('border-gray-200');
        
        // Store template data
        this.goalData = {
            ...this.goalData,
            ...template,
            type: type,
            template_id: `${type}_${template.name.toLowerCase().replace(/\s+/g, '_')}`,
            creation_method: 'template'
        };
        
        // Pre-fill the next step with template data
        this.prefillFromTemplate();
        
        this.validateCurrentStep();
    }
    
    selectCustomGoal() {
        // Clear template selection
        document.querySelectorAll('.template-card').forEach(card => {
            card.classList.remove('border-primary-500', 'bg-primary-50');
            card.classList.add('border-gray-200');
        });
        
        // Mark as custom
        this.goalData.creation_method = 'custom';
        this.goalData.template_id = null;
        
        this.validateCurrentStep();
    }
    
    prefillFromTemplate() {
        const template = this.goalData;
        
        // Set form values
        if (template.name) {
            const nameInput = document.getElementById('goal-name');
            if (nameInput) nameInput.value = template.name;
        }
        
        if (template.description) {
            const descInput = document.getElementById('goal-description');
            if (descInput) descInput.value = template.description;
        }
        
        if (template.target_amount) {
            const amountInput = document.getElementById('target-amount');
            if (amountInput) amountInput.value = template.target_amount;
        }
        
        if (template.duration_weeks) {
            // Calculate target date
            const targetDate = new Date();
            targetDate.setDate(targetDate.getDate() + (template.duration_weeks * 7));
            
            const dateInput = document.getElementById('target-date');
            if (dateInput) dateInput.value = targetDate.toISOString().split('T')[0];
            
            this.goalData.target_date = targetDate.toISOString();
        }
        
        if (template.difficulty) {
            const difficultySelect = document.getElementById('difficulty-level');
            if (difficultySelect) difficultySelect.value = template.difficulty;
            this.updateDifficultyDescription();
        }
        
        // Update preview
        this.updateBreakdownPreview();
    }
    
    updateDifficultyDescription() {
        const difficulty = this.goalData.difficulty;
        const descriptionEl = document.getElementById('difficulty-description');
        
        if (!descriptionEl) return;
        
        const descriptions = {
            'gentle': {
                text: 'Perfect for building confidence with very achievable targets. Great for getting started!',
                icon: '🌱',
                color: 'text-green-600'
            },
            'moderate': {
                text: 'A balanced challenge that keeps you motivated without overwhelming you.',
                icon: '🎯',
                color: 'text-blue-600'
            },
            'ambitious': {
                text: 'A stretch goal for when you\'re feeling motivated and ready for a bigger challenge.',
                icon: '🚀',
                color: 'text-orange-600'
            }
        };
        
        const desc = descriptions[difficulty] || descriptions['moderate'];
        
        descriptionEl.innerHTML = `
            <div class="flex items-center ${desc.color}">
                <span class="mr-2 text-lg">${desc.icon}</span>
                <span class="text-sm">${desc.text}</span>
            </div>
        `;
    }
    
    updateBreakdownPreview() {
        const previewEl = document.getElementById('goal-breakdown-preview');
        if (!previewEl) return;
        
        const amount = this.goalData.target_amount || 0;
        const targetDate = this.goalData.target_date;
        
        if (!amount || !targetDate) {
            previewEl.innerHTML = '<p class="text-text-muted text-sm">Enter amount and date to see breakdown</p>';
            return;
        }
        
        // Calculate time breakdown
        const today = new Date();
        const target = new Date(targetDate);
        const totalDays = Math.ceil((target - today) / (1000 * 60 * 60 * 24));
        const totalWeeks = Math.ceil(totalDays / 7);
        const totalMonths = Math.ceil(totalDays / 30);
        
        if (totalDays <= 0) {
            previewEl.innerHTML = '<p class="text-orange-600 text-sm">⚠️ Target date should be in the future</p>';
            return;
        }
        
        const dailyAmount = amount / totalDays;
        const weeklyAmount = amount / totalWeeks;
        const monthlyAmount = amount / totalMonths;
        
        // Determine milestone count based on duration
        let milestoneCount;
        if (totalWeeks <= 4) {
            milestoneCount = 2;
        } else if (totalWeeks <= 12) {
            milestoneCount = 4;
        } else if (totalWeeks <= 26) {
            milestoneCount = 6;
        } else {
            milestoneCount = 8;
        }
        
        const milestoneAmount = amount / milestoneCount;
        
        previewEl.innerHTML = `
            <div class="bg-primary-50 border border-primary-200 rounded-lg p-4">
                <h4 class="font-semibold text-primary-800 mb-3 flex items-center">
                    <span class="mr-2">📊</span>
                    Your Goal Breakdown
                </h4>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-primary-600">Per day:</span>
                            <span class="font-medium">$${dailyAmount.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-primary-600">Per week:</span>
                            <span class="font-medium">$${weeklyAmount.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-primary-600">Per month:</span>
                            <span class="font-medium">$${monthlyAmount.toFixed(2)}</span>
                        </div>
                    </div>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-primary-600">Duration:</span>
                            <span class="font-medium">${totalWeeks} weeks</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-primary-600">Milestones:</span>
                            <span class="font-medium">${milestoneCount} steps</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-primary-600">Per milestone:</span>
                            <span class="font-medium">$${milestoneAmount.toFixed(0)}</span>
                        </div>
                    </div>
                </div>
                <div class="mt-3 p-2 bg-success-50 border border-success-200 rounded text-xs text-success-700">
                    💚 This breaks down to just $${dailyAmount.toFixed(2)} per day - totally manageable!
                </div>
            </div>
        `;
    }
    
    nextStep() {
        if (!this.validateCurrentStep()) {
            this.showValidationErrors();
            return;
        }
        
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.updateWizardStep();
            this.updateProgress();
            
            // Show encouragement
            if (this.currentStep === 2) {
                this.showSuccessMessage('Great choice! Now let\'s set up the details 🎯');
            } else if (this.currentStep === 3) {
                this.showSuccessMessage('Perfect! Let\'s customize this goal for your brain 🧠');
            }
        }
    }
    
    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateWizardStep();
            this.updateProgress();
        }
    }
    
    updateWizardStep() {
        // Hide all steps
        document.querySelectorAll('.wizard-step').forEach(step => {
            step.classList.add('hidden');
        });
        
        // Show current step
        const currentStepEl = document.getElementById(`step-${this.currentStep}`);
        if (currentStepEl) {
            currentStepEl.classList.remove('hidden');
        }
        
        // Update navigation buttons
        const nextBtn = document.getElementById('next-step');
        const prevBtn = document.getElementById('prev-step');
        const finishBtn = document.getElementById('finish-goal');
        
        if (prevBtn) {
            prevBtn.style.display = this.currentStep > 1 ? 'block' : 'none';
        }
        
        if (nextBtn && finishBtn) {
            if (this.currentStep === this.totalSteps) {
                nextBtn.style.display = 'none';
                finishBtn.style.display = 'block';
            } else {
                nextBtn.style.display = 'block';
                finishBtn.style.display = 'none';
            }
        }
        
        // Update step indicators
        this.updateStepIndicators();
    }
    
    updateProgress() {
        const progressBar = document.getElementById('wizard-progress-bar');
        const progressText = document.getElementById('wizard-progress-text');
        
        const percentage = (this.currentStep / this.totalSteps) * 100;
        
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }
        
        if (progressText) {
            progressText.textContent = `Step ${this.currentStep} of ${this.totalSteps}`;
        }
        
        // Show celebration animation when complete
        if (this.currentStep === this.totalSteps && percentage === 100) {
            this.showCompletionAnimation();
        }
    }
    
    updateStepIndicators() {
        document.querySelectorAll('.step-indicator').forEach((indicator, index) => {
            const stepNumber = index + 1;
            
            indicator.classList.remove('active', 'completed');
            
            if (stepNumber < this.currentStep) {
                indicator.classList.add('completed');
            } else if (stepNumber === this.currentStep) {
                indicator.classList.add('active');
            }
        });
    }
    
    validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                return this.goalData.type && (this.goalData.template_id || this.goalData.creation_method === 'custom');
            case 2:
                return this.goalData.name && this.goalData.target_amount > 0 && this.goalData.target_date;
            case 3:
                return this.goalData.difficulty;
            case 4:
                return true; // Settings are optional
            case 5:
                return true; // Review step
            default:
                return true;
        }
    }
    
    showValidationErrors() {
        let message = '';
        
        switch (this.currentStep) {
            case 1:
                message = 'Please select a goal type and template (or choose custom)';
                break;
            case 2:
                if (!this.goalData.name) message = 'Please enter a goal name';
                else if (!this.goalData.target_amount || this.goalData.target_amount <= 0) message = 'Please enter a target amount';
                else if (!this.goalData.target_date) message = 'Please select a target date';
                break;
            case 3:
                message = 'Please select a difficulty level';
                break;
        }
        
        if (message) {
            this.showErrorMessage(message);
        }
    }
    
    showCompletionAnimation() {
        // Add celebration effect
        const wizardContainer = document.getElementById('goal-wizard-container');
        if (wizardContainer) {
            wizardContainer.classList.add('celebration-animation');
            
            setTimeout(() => {
                wizardContainer.classList.remove('celebration-animation');
            }, 3000);
        }
    }
    
    async createGoal() {
        try {
            const createBtn = document.getElementById('finish-goal');
            if (createBtn) {
                createBtn.disabled = true;
                createBtn.textContent = '🎯 Creating your goal...';
            }
            
            // Prepare goal data
            const goalPayload = {
                type: this.goalData.type,
                name: this.goalData.name,
                description: this.goalData.description || '',
                target_amount: this.goalData.target_amount,
                target_date: this.goalData.target_date,
                difficulty: this.goalData.difficulty || 'moderate',
                allow_adjustments: this.goalData.allow_adjustments !== false,
                celebration_style: this.goalData.celebration_style || 'gentle',
                adhd_tips_enabled: this.goalData.adhd_tips_enabled !== false,
                template_id: this.goalData.template_id,
                creation_method: this.goalData.creation_method || 'wizard',
                category: this.goalData.category,
                tags: ['wizard-created']
            };
            
            const response = await fetch('/api/goals/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${await this.getAuthToken()}`
                },
                body: JSON.stringify(goalPayload)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showSuccessMessage('🎉 Goal created successfully! You\'re all set to start your journey!');
                
                // Show completion step
                this.showGoalCompletionSummary(result.goal);
                
                // Redirect to dashboard after a moment
                setTimeout(() => {
                    window.location.href = '/dashboard?tab=goals&celebrate=true';
                }, 3000);
                
            } else {
                throw new Error(result.error || 'Failed to create goal');
            }
            
        } catch (error) {
            console.error('Error creating goal:', error);
            this.showErrorMessage('Had trouble creating your goal. Let\'s try again in a moment!');
            
            const createBtn = document.getElementById('finish-goal');
            if (createBtn) {
                createBtn.disabled = false;
                createBtn.textContent = '🎯 Create My Goal';
            }
        }
    }
    
    showGoalCompletionSummary(goal) {
        const summaryEl = document.getElementById('goal-completion-summary');
        if (!summaryEl) return;
        
        summaryEl.innerHTML = `
            <div class="text-center">
                <div class="mb-6">
                    <div class="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-success-400 to-success-500 rounded-full mb-4 animate-bounce">
                        <span class="text-4xl">🎯</span>
                    </div>
                    <h2 class="text-2xl font-bold text-text-primary mb-2">Goal Created Successfully!</h2>
                    <p class="text-text-secondary">${goal.name}</p>
                </div>
                
                <div class="bg-primary-50 border border-primary-200 rounded-xl p-6 mb-6">
                    <h3 class="font-semibold text-primary-800 mb-4">Your Goal Summary</h3>
                    <div class="space-y-3 text-sm">
                        <div class="flex justify-between">
                            <span class="text-primary-600">Target Amount:</span>
                            <span class="font-medium">$${goal.target_amount.toLocaleString()}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-primary-600">Target Date:</span>
                            <span class="font-medium">${new Date(goal.target_date).toLocaleDateString()}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-primary-600">Milestones:</span>
                            <span class="font-medium">${goal.milestones?.length || 0} steps</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-primary-600">Difficulty:</span>
                            <span class="font-medium capitalize">${goal.difficulty}</span>
                        </div>
                    </div>
                </div>
                
                <div class="space-y-3 text-sm">
                    <div class="flex items-center justify-center text-success-600">
                        <span class="mr-2">✅</span>
                        <span>Goal broken into manageable steps</span>
                    </div>
                    <div class="flex items-center justify-center text-success-600">
                        <span class="mr-2">✅</span>
                        <span>Progress tracking enabled</span>
                    </div>
                    <div class="flex items-center justify-center text-success-600">
                        <span class="mr-2">✅</span>
                        <span>Celebration notifications ready</span>
                    </div>
                </div>
                
                <p class="text-text-muted mt-6">Redirecting to your dashboard...</p>
            </div>
        `;
        
        summaryEl.classList.remove('hidden');
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
            console.log('Success:', message);
        }
    }
    
    showErrorMessage(message) {
        // Use the existing toast system if available
        if (window.showErrorToast) {
            window.showErrorToast(message);
        } else {
            console.error('Error:', message);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('goal-wizard-container')) {
        window.goalWizard = new GoalCreationWizard();
    }
});

// CSS for wizard animations
const style = document.createElement('style');
style.textContent = `
    .template-card.selected {
        animation: selected-bounce 0.3s ease-out;
    }
    
    @keyframes selected-bounce {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .celebration-animation {
        animation: celebration-pulse 1s ease-in-out infinite;
    }
    
    @keyframes celebration-pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    
    .wizard-step {
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }
    
    .wizard-step:not(.hidden) {
        opacity: 1;
    }
    
    .step-indicator {
        transition: all 0.3s ease-in-out;
    }
    
    .step-indicator.completed {
        background-color: #10B981;
        color: white;
    }
    
    .step-indicator.active {
        background-color: #4A90E2;
        color: white;
        transform: scale(1.1);
    }
    
    .goal-type-card, .template-card {
        transition: all 0.2s ease-out;
    }
    
    .goal-type-card:hover, .template-card:hover {
        transform: translateY(-2px);
    }
    
    #wizard-progress-bar {
        transition: width 0.3s ease-in-out;
    }
`;

document.head.appendChild(style);