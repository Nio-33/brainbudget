/**
 * ADHD-Friendly Financial Advice Dashboard for BrainBudget
 * Displays personalized financial guidance with interactive features
 */

class AdviceDashboard {
    constructor() {
        this.currentCategory = '';
        this.currentAdvice = [];
        this.userProfile = {};
        this.currentAdviceId = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadPersonalizedAdvice();
    }
    
    setupEventListeners() {
        // Category selector
        document.getElementById('advice-category')?.addEventListener('change', (e) => {
            this.currentCategory = e.target.value;
            this.loadPersonalizedAdvice();
        });
        
        // Refresh button
        document.getElementById('refresh-advice')?.addEventListener('click', () => {
            this.loadPersonalizedAdvice();
        });
        
        // Quick action buttons
        document.getElementById('urgent-advice-btn')?.addEventListener('click', () => {
            this.loadUrgentAdvice();
        });
        
        document.getElementById('quick-tips-btn')?.addEventListener('click', () => {
            this.loadQuickTips();
        });
        
        document.getElementById('progress-check-btn')?.addEventListener('click', () => {
            this.showProgressModal();
        });
        
        // Progress modal buttons
        document.getElementById('close-progress-modal')?.addEventListener('click', () => {
            this.hideProgressModal();
        });
        
        document.getElementById('submit-progress')?.addEventListener('click', () => {
            this.submitProgress();
        });
        
        document.getElementById('cancel-progress')?.addEventListener('click', () => {
            this.hideProgressModal();
        });
        
        // Close modal on background click
        document.getElementById('progress-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'progress-modal') {
                this.hideProgressModal();
            }
        });
    }
    
    async loadPersonalizedAdvice() {
        try {
            this.showLoading(true);
            
            let url = '/api/advice/personalized?limit=5';
            if (this.currentCategory) {
                url = `/api/advice/by-category/${this.currentCategory}?limit=5`;
            }
            
            const response = await this.makeAPICall(url, 'GET');
            
            if (response.success) {
                this.currentAdvice = response.advice || response.advice || [];
                this.userProfile = response.user_profile || response.user_context || {};
                
                if (this.currentAdvice.length > 0) {
                    this.renderAdviceCards(this.currentAdvice);
                    this.renderUserProfile(this.userProfile);
                    this.showMainContent();
                } else {
                    this.showNoDataState();
                }
                
                // Show personalization notes if available
                const notes = response.personalization_notes;
                if (notes && notes.length > 0) {
                    this.showSuccess(`Advice personalized: ${notes.join(', ')}`);
                }
            } else {
                throw new Error(response.message || 'Failed to load advice');
            }
            
        } catch (error) {
            console.error('Error loading advice:', error);
            this.handleAdviceError(error);
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadUrgentAdvice() {
        try {
            this.showLoading(true);
            
            const response = await this.makeAPICall('/api/advice/urgent?limit=3', 'GET');
            
            if (response.success) {
                const urgentAdvice = response.urgent_advice || [];
                
                if (urgentAdvice.length > 0) {
                    this.currentAdvice = urgentAdvice;
                    this.renderAdviceCards(urgentAdvice);
                    this.showMainContent();
                    
                    // Show explanation
                    this.showSuccess(`Found ${urgentAdvice.length} urgent financial priorities`);
                } else {
                    this.showSuccess('Great news! No urgent financial issues detected 🎉');
                    this.loadPersonalizedAdvice(); // Fall back to regular advice
                }
            } else {
                throw new Error(response.message || 'Failed to load urgent advice');
            }
            
        } catch (error) {
            console.error('Error loading urgent advice:', error);
            this.showError('Unable to analyze urgent priorities right now');
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadQuickTips() {
        try {
            this.showLoading(true);
            
            const response = await this.makeAPICall('/api/advice/quick-tips?limit=8', 'GET');
            
            if (response.success) {
                const tips = response.quick_tips || [];
                this.renderQuickTips(tips);
                this.showMainContent();
                
                if (response.personalized) {
                    this.showSuccess('Quick tips personalized for you! ⚡');
                }
            } else {
                throw new Error(response.message || 'Failed to load quick tips');
            }
            
        } catch (error) {
            console.error('Error loading quick tips:', error);
            this.showError('Unable to load quick tips right now');
        } finally {
            this.showLoading(false);
        }
    }
    
    renderAdviceCards(advice) {
        const container = document.getElementById('advice-cards');
        if (!container) return;
        
        container.innerHTML = '';
        
        advice.forEach((adviceItem, index) => {
            const card = this.createAdviceCard(adviceItem, index);
            container.appendChild(card);
        });
    }
    
    createAdviceCard(advice, index) {
        const card = document.createElement('div');
        card.className = `advice-card bg-white rounded-lg shadow-sm border border-gray-200 p-6 urgency-${advice.urgency || 'medium'}`;\n        \n        const categoryClass = `category-${advice.category || 'general'}`;\n        const urgencyColors = {\n            'critical': 'text-red-600',\n            'high': 'text-orange-600',\n            'medium': 'text-blue-600',\n            'low': 'text-green-600'\n        };\n        \n        const urgencyColor = urgencyColors[advice.urgency] || 'text-blue-600';\n        \n        card.innerHTML = `\n            <div class=\"flex items-start justify-between mb-4\">\n                <div class=\"flex-1\">\n                    <div class=\"flex items-center mb-2\">\n                        <h3 class=\"text-xl font-semibold text-gray-900 mr-3\">${advice.title}</h3>\n                        <span class=\"px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600 capitalize\">\n                            ${(advice.category || 'general').replace('_', ' ')}\n                        </span>\n                        <span class=\"ml-2 px-2 py-1 text-xs rounded-full ${urgencyColor.replace('text-', 'bg-').replace('-600', '-100')} ${urgencyColor} capitalize\">\n                            ${advice.urgency || 'medium'} priority\n                        </span>\n                    </div>\n                    <p class=\"text-gray-700 mb-4\">${advice.summary}</p>\n                </div>\n                \n                <div class=\"flex-shrink-0 ml-4\">\n                    <div class=\"w-16 text-center\">\n                        <div class=\"text-sm text-gray-500 mb-1\">Confidence</div>\n                        <div class=\"relative w-12 h-12 mx-auto\">\n                            <svg class=\"w-12 h-12 transform -rotate-90\" viewBox=\"0 0 36 36\">\n                                <path class=\"text-gray-200\" stroke=\"currentColor\" stroke-width=\"3\" fill=\"none\" d=\"M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831\"/>\n                                <path class=\"confidence-bar\" stroke=\"currentColor\" stroke-width=\"3\" fill=\"none\" stroke-dasharray=\"${(advice.confidence_score * 100).toFixed(0)}, 100\" d=\"M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831\"/>\n                            </svg>\n                            <div class=\"absolute inset-0 flex items-center justify-center text-xs font-medium\">\n                                ${(advice.confidence_score * 100).toFixed(0)}%\n                            </div>\n                        </div>\n                    </div>\n                </div>\n            </div>\n            \n            <div class=\"mb-4\">\n                <div class=\"prose prose-sm max-w-none\">\n                    ${this.formatAdviceContent(advice.content)}\n                </div>\n            </div>\n            \n            ${advice.action_steps && advice.action_steps.length > 0 ? `\n                <div class=\"mb-4\">\n                    <h4 class=\"text-sm font-semibold text-gray-900 mb-2\">🎯 Action Steps</h4>\n                    <ul class=\"space-y-2\">\n                        ${advice.action_steps.map((step, stepIndex) => `\n                            <li class=\"flex items-start\">\n                                <button class=\"action-btn flex-shrink-0 w-6 h-6 rounded-full border-2 border-gray-300 mr-3 mt-0.5 focus:outline-none\" \n                                        onclick=\"window.adviceDashboard.toggleActionStep(this, '${advice.advice_id}', ${stepIndex})\">\n                                    <span class=\"hidden\">✓</span>\n                                </button>\n                                <span class=\"text-sm text-gray-700\">${step}</span>\n                            </li>\n                        `).join('')}\n                    </ul>\n                </div>\n            ` : ''}\n            \n            ${advice.adhd_tips && advice.adhd_tips.length > 0 ? `\n                <div class=\"mb-4 bg-purple-50 border border-purple-200 rounded-lg p-3\">\n                    <h4 class=\"text-sm font-semibold text-purple-800 mb-2\">🧠 ADHD-Friendly Tips</h4>\n                    <ul class=\"space-y-1\">\n                        ${advice.adhd_tips.map(tip => `\n                            <li class=\"text-xs text-purple-700 flex items-start\">\n                                <span class=\"text-purple-500 mr-2\">•</span>\n                                <span>${tip}</span>\n                            </li>\n                        `).join('')}\n                    </ul>\n                </div>\n            ` : ''}\n            \n            ${advice.personalization_reasons && advice.personalization_reasons.length > 0 ? `\n                <div class=\"mb-4 text-xs text-gray-500\">\n                    <strong>Why this advice:</strong> ${advice.personalization_reasons.join(', ')}\n                </div>\n            ` : ''}\n            \n            <div class=\"flex items-center justify-between pt-4 border-t border-gray-200\">\n                <div class=\"flex items-center space-x-4 text-sm text-gray-500\">\n                    <span>⏱️ ${advice.time_to_implement || 'varies'}</span>\n                    <span>📈 ${advice.estimated_impact || 'Positive impact expected'}</span>\n                </div>\n                \n                <div class=\"flex space-x-2\">\n                    <button class=\"text-sm bg-green-500 text-white px-3 py-1 rounded-lg hover:bg-green-600 transition-colors\"\n                            onclick=\"window.adviceDashboard.markAdviceAsStarted('${advice.advice_id}')\">\n                        Start This\n                    </button>\n                    <button class=\"text-sm text-gray-500 hover:text-gray-700 px-2 py-1\"\n                            onclick=\"window.adviceDashboard.provideFeedback('${advice.advice_id}', 'helpful')\">\n                        👍 Helpful\n                    </button>\n                    <button class=\"text-sm text-gray-500 hover:text-gray-700 px-2 py-1\"\n                            onclick=\"window.adviceDashboard.provideFeedback('${advice.advice_id}', 'not_helpful')\">\n                        👎 Not helpful\n                    </button>\n                </div>\n            </div>\n        `;\n        \n        return card;\n    }\n    \n    formatAdviceContent(content) {\n        if (!content) return '';\n        \n        // Convert markdown-style formatting to HTML\n        return content\n            .replace(/## ([^\\n]+)/g, '<h4 class=\"font-semibold text-gray-900 mt-4 mb-2\">$1</h4>')\n            .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>')\n            .replace(/\\n\\n/g, '</p><p class=\"mb-2\">')\n            .replace(/^(.)/g, '<p class=\"mb-2\">$1')\n            .replace(/(..)$/g, '$1</p>');\n    }\n    \n    renderQuickTips(tips) {\n        const container = document.getElementById('advice-cards');\n        if (!container) return;\n        \n        container.innerHTML = `\n            <div class=\"bg-white rounded-lg shadow-sm border border-gray-200 p-6\">\n                <h2 class=\"text-xl font-semibold text-gray-900 mb-4\">⚡ Quick Financial Tips</h2>\n                <div class=\"grid grid-cols-1 md:grid-cols-2 gap-4\">\n                    ${tips.map(tip => `\n                        <div class=\"bg-blue-50 border border-blue-200 rounded-lg p-4\">\n                            <div class=\"flex items-start\">\n                                <span class=\"text-2xl mr-3\">${this.getCategoryIcon(tip.category)}</span>\n                                <div class=\"flex-1\">\n                                    <p class=\"text-blue-800 font-medium mb-2\">${tip.tip}</p>\n                                    <div class=\"text-xs text-blue-600 space-y-1\">\n                                        <div>⏱️ ${tip.time_needed}</div>\n                                        ${tip.confidence ? `<div>✅ ${(tip.confidence * 100).toFixed(0)}% confidence</div>` : ''}\n                                    </div>\n                                    \n                                    ${tip.adhd_tips && tip.adhd_tips.length > 0 ? `\n                                        <div class=\"mt-2 space-y-1\">\n                                            ${tip.adhd_tips.map(adhdTip => `\n                                                <div class=\"text-xs text-purple-600\">🧠 ${adhdTip}</div>\n                                            `).join('')}\n                                        </div>\n                                    ` : ''}\n                                    \n                                    ${tip.from_advice_id ? `\n                                        <button class=\"mt-2 text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600 transition-colors\"\n                                                onclick=\"window.adviceDashboard.expandAdvice('${tip.from_advice_id}')\">\n                                            Get Full Advice\n                                        </button>\n                                    ` : ''}\n                                </div>\n                            </div>\n                        </div>\n                    `).join('')}\n                </div>\n            </div>\n        `;\n    }\n    \n    renderUserProfile(profile) {\n        const container = document.getElementById('profile-content');\n        if (!container || !profile || Object.keys(profile).length === 0) return;\n        \n        container.innerHTML = `\n            <div class=\"grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4\">\n                <div class=\"text-center\">\n                    <div class=\"text-2xl mb-2\">💰</div>\n                    <div class=\"text-sm text-gray-600\">Income Profile</div>\n                    <div class=\"font-medium text-gray-900\">${profile.income_profile || 'Analyzing...'}</div>\n                </div>\n                \n                <div class=\"text-center\">\n                    <div class=\"text-2xl mb-2\">🧠</div>\n                    <div class=\"text-sm text-gray-600\">ADHD Considerations</div>\n                    <div class=\"font-medium text-gray-900\">${profile.adhd_considerations || 'Moderate'}</div>\n                </div>\n                \n                <div class=\"text-center\">\n                    <div class=\"text-2xl mb-2\">💳</div>\n                    <div class=\"text-sm text-gray-600\">Total Debt</div>\n                    <div class=\"font-medium text-gray-900\">$${(profile.total_debt || 0).toLocaleString()}</div>\n                </div>\n                \n                <div class=\"text-center\">\n                    <div class=\"text-2xl mb-2\">🎯</div>\n                    <div class=\"text-sm text-gray-600\">Primary Focus</div>\n                    <div class=\"font-medium text-gray-900\">${profile.primary_focus || 'Goal setting'}</div>\n                </div>\n            </div>\n        `;\n    }\n    \n    getCategoryIcon(category) {\n        const icons = {\n            'budgeting': '📊',\n            'debt_reduction': '💪',\n            'savings': '🏦',\n            'investment': '📈',\n            'emergency_fund': '🛡️',\n            'general': '💡'\n        };\n        return icons[category] || '💡';\n    }\n    \n    // Interaction methods\n    \n    async toggleActionStep(button, adviceId, stepIndex) {\n        const isCompleted = button.classList.contains('completed');\n        \n        if (isCompleted) {\n            button.classList.remove('completed');\n            button.querySelector('span').classList.add('hidden');\n        } else {\n            button.classList.add('completed');\n            button.querySelector('span').classList.remove('hidden');\n            \n            // Record the action\n            await this.recordInteraction(adviceId, 'step_completed', {\n                step_index: stepIndex,\n                step_completed: true\n            });\n            \n            // Show encouragement\n            this.showSuccess('Great job completing that step! 🎉');\n        }\n    }\n    \n    async markAdviceAsStarted(adviceId) {\n        try {\n            await this.recordInteraction(adviceId, 'started');\n            this.showSuccess('Awesome! You\\'ve started working on this advice. You\\'ve got this! 💪');\n        } catch (error) {\n            console.error('Error marking advice as started:', error);\n        }\n    }\n    \n    async provideFeedback(adviceId, feedback) {\n        try {\n            await this.recordInteraction(adviceId, feedback);\n            \n            const messages = {\n                'helpful': 'Thanks for the feedback! Glad this advice was helpful! 😊',\n                'not_helpful': 'Thanks for letting us know - we\\'ll work on better suggestions! 🛠️'\n            };\n            \n            this.showSuccess(messages[feedback] || 'Thanks for your feedback!');\n        } catch (error) {\n            console.error('Error providing feedback:', error);\n        }\n    }\n    \n    async recordInteraction(adviceId, action, feedback = {}) {\n        try {\n            await this.makeAPICall('/api/advice/interaction', 'POST', {\n                advice_id: adviceId,\n                action: action,\n                feedback: feedback\n            });\n        } catch (error) {\n            console.error('Error recording interaction:', error);\n        }\n    }\n    \n    // Progress modal methods\n    \n    showProgressModal() {\n        document.getElementById('progress-modal')?.classList.remove('hidden');\n    }\n    \n    hideProgressModal() {\n        document.getElementById('progress-modal')?.classList.add('hidden');\n        \n        // Reset form\n        document.getElementById('progress-status').value = '';\n        document.getElementById('progress-notes').value = '';\n    }\n    \n    async submitProgress() {\n        try {\n            const status = document.getElementById('progress-status').value;\n            const notes = document.getElementById('progress-notes').value;\n            \n            if (!status) {\n                this.showError('Please select your progress status');\n                return;\n            }\n            \n            const response = await this.makeAPICall('/api/advice/progress-check', 'POST', {\n                advice_id: this.currentAdviceId || 'general',\n                progress_status: status,\n                notes: notes\n            });\n            \n            if (response.success) {\n                this.hideProgressModal();\n                this.showProgressResponse(response);\n            } else {\n                throw new Error(response.message || 'Failed to submit progress');\n            }\n            \n        } catch (error) {\n            console.error('Error submitting progress:', error);\n            this.showError('Unable to submit progress right now');\n        }\n    }\n    \n    showProgressResponse(response) {\n        const responseData = response.response || {};\n        const message = responseData.message || 'Thanks for checking in!';\n        const encouragement = responseData.encouragement || '';\n        const nextSteps = responseData.next_steps || [];\n        const challengeTips = response.challenge_tips || [];\n        \n        // Show a detailed response modal or notification\n        let fullMessage = message;\n        if (encouragement) {\n            fullMessage += `\\n\\n${encouragement}`;\n        }\n        if (nextSteps.length > 0) {\n            fullMessage += `\\n\\nNext steps: ${nextSteps.join(', ')}`;\n        }\n        if (challengeTips.length > 0) {\n            fullMessage += `\\n\\nTips: ${challengeTips.join(', ')}`;\n        }\n        \n        this.showSuccess(fullMessage.substring(0, 200) + (fullMessage.length > 200 ? '...' : ''));\n    }\n    \n    // UI state methods\n    \n    showLoading(show) {\n        const loadingState = document.getElementById('loading-state');\n        const mainContent = document.getElementById('main-content');\n        const noDataState = document.getElementById('no-data-state');\n        \n        if (show) {\n            loadingState?.classList.remove('hidden');\n            mainContent?.classList.add('hidden');\n            noDataState?.classList.add('hidden');\n        } else {\n            loadingState?.classList.add('hidden');\n        }\n    }\n    \n    showMainContent() {\n        document.getElementById('main-content')?.classList.remove('hidden');\n        document.getElementById('no-data-state')?.classList.add('hidden');\n    }\n    \n    showNoDataState() {\n        document.getElementById('no-data-state')?.classList.remove('hidden');\n        document.getElementById('main-content')?.classList.add('hidden');\n    }\n    \n    handleAdviceError(error) {\n        // Check for specific error types\n        if (error.message && error.message.includes('insufficient')) {\n            this.showNoDataState();\n            return;\n        }\n        \n        // Show error message\n        this.showError('Unable to load personalized advice right now');\n        \n        // Show fallback content if possible\n        this.showMainContent();\n        const container = document.getElementById('advice-cards');\n        if (container) {\n            container.innerHTML = `\n                <div class=\"bg-red-50 border border-red-200 rounded-lg p-6 text-center\">\n                    <span class=\"text-4xl mb-4 block\">🔧</span>\n                    <h3 class=\"text-lg font-semibold text-red-800 mb-2\">Advice Temporarily Unavailable</h3>\n                    <p class=\"text-red-700\">We're having trouble generating your personalized advice right now. Please try again in a few minutes!</p>\n                    <button class=\"mt-4 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors\" onclick=\"window.location.reload()\">\n                        Try Again\n                    </button>\n                </div>\n            `;\n        }\n    }\n    \n    showError(message) {\n        const toast = document.getElementById('error-toast');\n        const messageEl = document.getElementById('error-message');\n        \n        if (toast && messageEl) {\n            messageEl.textContent = message;\n            toast.classList.remove('translate-x-full');\n            \n            setTimeout(() => {\n                toast.classList.add('translate-x-full');\n            }, 5000);\n        }\n    }\n    \n    showSuccess(message) {\n        const toast = document.getElementById('success-toast');\n        const messageEl = document.getElementById('success-message');\n        \n        if (toast && messageEl) {\n            messageEl.textContent = message;\n            toast.classList.remove('translate-x-full');\n            \n            setTimeout(() => {\n                toast.classList.add('translate-x-full');\n            }, 3000);\n        }\n    }\n    \n    async makeAPICall(url, method, data = null) {\n        const options = {\n            method: method,\n            headers: {\n                'Content-Type': 'application/json'\n            }\n        };\n        \n        // Add auth token if available\n        const token = await this.getAuthToken();\n        if (token) {\n            options.headers['Authorization'] = `Bearer ${token}`;\n        }\n        \n        if (data) {\n            options.body = JSON.stringify(data);\n        }\n        \n        const response = await fetch(url, options);\n        \n        if (!response.ok) {\n            if (response.status === 401) {\n                throw new Error('Please log in to view personalized advice');\n            }\n        }\n        \n        return await response.json();\n    }\n    \n    async getAuthToken() {\n        // Get Firebase auth token\n        if (window.firebase && firebase.auth && firebase.auth().currentUser) {\n            return await firebase.auth().currentUser.getIdToken();\n        }\n        return null;\n    }\n}\n\n// Export for use\nwindow.AdviceDashboard = AdviceDashboard;