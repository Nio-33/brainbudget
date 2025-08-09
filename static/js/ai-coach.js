/**
 * AI Financial Coach Interface for BrainBudget
 * Provides ADHD-friendly conversational AI for financial guidance
 */

class AICoachInterface {
    constructor() {
        this.sessionId = null;
        this.isLoading = false;
        this.currentRating = 0;
        this.quickActions = {};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadQuickActions();
        this.startNewConversation();
    }
    
    setupEventListeners() {
        // Message form submission
        document.getElementById('message-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // New conversation
        document.getElementById('new-conversation').addEventListener('click', (e) => {
            e.preventDefault();
            this.startNewConversation();
        });
        
        // Conversation history
        document.getElementById('conversation-history').addEventListener('click', (e) => {
            e.preventDefault();
            this.showConversationHistory();
        });
        
        // Feedback
        document.getElementById('feedback-button').addEventListener('click', (e) => {
            e.preventDefault();
            this.showFeedbackModal();
        });
        
        // Rating stars
        document.querySelectorAll('.star').forEach(star => {
            star.addEventListener('click', (e) => {
                const rating = parseInt(e.target.dataset.rating);
                this.setRating(rating);
            });
            
            star.addEventListener('mouseover', (e) => {
                const rating = parseInt(e.target.dataset.rating);
                this.highlightStars(rating);
            });
        });
        
        // Feedback modal buttons
        document.getElementById('submit-feedback').addEventListener('click', () => {
            this.submitFeedback();
        });
        
        document.getElementById('cancel-feedback').addEventListener('click', () => {
            this.hideFeedbackModal();
        });
        
        // Close modals
        document.getElementById('close-history').addEventListener('click', () => {
            this.hideHistoryModal();
        });
        
        // Close modals on background click
        document.addEventListener('click', (e) => {
            if (e.target.id === 'history-modal') {
                this.hideHistoryModal();
            }
            if (e.target.id === 'feedback-modal') {
                this.hideFeedbackModal();
            }
        });
    }
    
    async startNewConversation() {
        try {
            this.showLoading(true);
            this.updateCoachStatus('Starting new conversation...');
            
            const response = await this.makeAPICall('/api/coach/start', 'POST');
            
            if (response.success) {
                this.sessionId = response.session_id;
                this.clearMessages();
                
                if (response.welcome_message) {
                    this.addMessage(response.welcome_message.content, 'assistant');
                }
                
                this.updateCoachStatus('Ready to help with your finances');
                this.showSuccessToast('New conversation started! 💬');
            } else {
                throw new Error(response.message || 'Failed to start conversation');
            }
            
        } catch (error) {
            console.error('Error starting conversation:', error);
            this.showErrorToast('I had trouble starting our conversation. Let me try again!');
            this.updateCoachStatus('Connection issue - trying to reconnect...');
        } finally {
            this.showLoading(false);
        }
    }
    
    async sendMessage(quickAction = null) {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message && !quickAction) {
            messageInput.focus();
            return;
        }
        
        if (!this.sessionId) {
            this.showErrorToast('Let me start a conversation first!');
            await this.startNewConversation();
            return;
        }
        
        try {
            this.showLoading(true);
            
            // Add user message to UI
            if (message) {
                this.addMessage(message, 'user');
                messageInput.value = '';
                messageInput.style.height = 'auto';
            }
            
            // Show typing indicator
            this.showTypingIndicator();
            
            const payload = {};
            if (message) payload.message = message;
            if (quickAction) payload.quick_action = quickAction;
            
            const response = await this.makeAPICall(`/api/coach/chat/${this.sessionId}`, 'POST', payload);
            
            this.hideTypingIndicator();
            
            if (response.success) {
                const aiResponse = response.response;
                
                // Add AI response to UI
                this.addMessage(aiResponse.content, 'assistant', {
                    confidence: aiResponse.confidence,
                    suggestions: aiResponse.suggestions,
                    needsDisclaimer: aiResponse.needs_disclaimer,
                    quickActions: aiResponse.quick_actions
                });
                
                // Update quick actions if provided
                if (aiResponse.quick_actions && aiResponse.quick_actions.length > 0) {
                    this.updateQuickActionsBar(aiResponse.quick_actions);
                }
                
                // Announce to screen reader
                this.announceMessage(aiResponse.content, false);
                
            } else {
                throw new Error(response.message || 'Failed to send message');
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.showErrorToast(error.message || 'I had trouble processing your message. Let me try again!');
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadQuickActions() {
        try {
            const response = await this.makeAPICall('/api/coach/quick-actions', 'GET');
            
            if (response.success) {
                this.quickActions = response.quick_actions;
                this.renderQuickActions();
            }
            
        } catch (error) {
            console.error('Error loading quick actions:', error);
            // Use default quick actions
            this.renderDefaultQuickActions();
        }
    }
    
    renderQuickActions() {
        const container = document.getElementById('quick-actions-container');
        container.innerHTML = '';
        
        // Render common actions
        if (this.quickActions.common) {
            this.quickActions.common.forEach(action => {
                const button = this.createQuickActionButton(action);
                container.appendChild(button);
            });
        }
    }
    
    renderDefaultQuickActions() {
        const container = document.getElementById('quick-actions-container');
        container.innerHTML = '';
        
        const defaultActions = [
            { id: 'spending_review', text: 'Review My Spending', icon: '📊' },
            { id: 'budget_help', text: 'Budget Help', icon: '💰' },
            { id: 'motivation', text: 'I Need Encouragement', icon: '💪' },
            { id: 'adhd_tips', text: 'ADHD Money Tips', icon: '🧠' }
        ];
        
        defaultActions.forEach(action => {
            const button = this.createQuickActionButton(action);
            container.appendChild(button);
        });
    }
    
    createQuickActionButton(action) {
        const button = document.createElement('button');
        button.className = 'quick-action-btn bg-purple-100 hover:bg-purple-200 text-purple-700 px-3 py-2 rounded-full text-sm font-medium transition-colors focus:ring-2 focus:ring-purple-500 focus:ring-offset-1';
        button.innerHTML = `${action.icon} ${action.text}`;
        button.setAttribute('aria-label', `Quick action: ${action.text}`);
        
        button.addEventListener('click', () => {
            this.sendMessage(action.id);
        });
        
        return button;
    }
    
    updateQuickActionsBar(actions) {
        const container = document.getElementById('quick-actions-container');
        container.innerHTML = '';
        
        actions.forEach(action => {
            const button = this.createQuickActionButton(action);
            container.appendChild(button);
        });
    }
    
    addMessage(content, role, metadata = {}) {
        const container = document.getElementById('messages-container');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-bubble';
        
        const isUser = role === 'user';
        const alignClass = isUser ? 'justify-end' : 'justify-start';
        const bgClass = isUser ? 'bg-purple-500 text-white' : 'bg-white border border-gray-200';
        const textClass = isUser ? 'text-white' : 'text-gray-900';
        
        messageDiv.innerHTML = `
            <div class="flex ${alignClass} mb-4">
                <div class="max-w-3xl ${bgClass} rounded-2xl px-4 py-3 shadow-sm">
                    ${!isUser ? `
                        <div class="flex items-center mb-2">
                            <div class="w-6 h-6 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center mr-2">
                                <span class="text-xs">🤖</span>
                            </div>
                            <span class="text-xs font-medium text-gray-500">AI Coach</span>
                            ${metadata.confidence ? `
                                <span class="ml-2 text-xs text-gray-400" title="Confidence level">
                                    ${this.getConfidenceIndicator(metadata.confidence)}
                                </span>
                            ` : ''}
                        </div>
                    ` : ''}
                    
                    <div class="${textClass} prose prose-sm max-w-none">
                        ${this.formatMessageContent(content)}
                    </div>
                    
                    ${metadata.suggestions && metadata.suggestions.length > 0 ? `
                        <div class="mt-3 pt-3 border-t border-gray-100">
                            <p class="text-xs text-gray-500 mb-2">💡 Suggestions:</p>
                            <ul class="text-sm space-y-1">
                                ${metadata.suggestions.map(suggestion => `
                                    <li class="flex items-start">
                                        <span class="text-purple-500 mr-2">•</span>
                                        <span>${suggestion}</span>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    
                    ${metadata.needsDisclaimer ? `
                        <div class="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-600">
                            ⚠️ This is general guidance. For complex financial decisions, please consult a licensed professional.
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        container.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Announce message for accessibility
        if (!isUser) {
            setTimeout(() => {
                this.announceMessage(content, false);
            }, 100);
        }
    }
    
    formatMessageContent(content) {
        // Convert newlines to break tags
        content = content.replace(/\n/g, '<br>');
        
        // Convert numbered lists to proper HTML lists
        content = content.replace(/(\d+\.\s+.+?)(?=\d+\.\s|\n\n|$)/g, (match, item) => {
            return `<li>${item.replace(/^\d+\.\s+/, '')}</li>`;
        });
        
        if (content.includes('<li>')) {
            content = content.replace(/(<li>.*<\/li>)/s, '<ol class="list-decimal list-inside space-y-1">$1</ol>');
        }
        
        // Make URLs clickable
        content = content.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-purple-600 underline">$1</a>');
        
        return content;
    }
    
    getConfidenceIndicator(confidence) {
        if (confidence >= 0.9) return '🟢';
        if (confidence >= 0.7) return '🟡';
        return '🔴';
    }
    
    showTypingIndicator() {
        const container = document.getElementById('messages-container');
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'flex justify-start mb-4';
        
        typingDiv.innerHTML = `
            <div class="bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
                <div class="flex items-center">
                    <div class="w-6 h-6 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center mr-2">
                        <span class="text-xs">🤖</span>
                    </div>
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <span class="ml-2 text-sm text-gray-500">thinking...</span>
                </div>
            </div>
        `;
        
        container.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    clearMessages() {
        const container = document.getElementById('messages-container');
        // Keep the welcome section, clear everything else
        const welcomeSection = container.querySelector('.bg-purple-50');
        container.innerHTML = '';
        if (welcomeSection) {
            container.appendChild(welcomeSection);
        }
    }
    
    scrollToBottom() {
        const container = document.getElementById('messages-container');
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }
    
    async showConversationHistory() {
        if (!this.sessionId) {
            this.showErrorToast('No conversation to show history for');
            return;
        }
        
        try {
            const response = await this.makeAPICall(`/api/coach/history/${this.sessionId}?limit=50`, 'GET');
            
            if (response.success) {
                this.renderConversationHistory(response.history);
                this.showHistoryModal();
            } else {
                throw new Error(response.message || 'Failed to load history');
            }
            
        } catch (error) {
            console.error('Error loading conversation history:', error);
            this.showErrorToast('I had trouble loading the conversation history');
        }
    }
    
    renderConversationHistory(history) {
        const content = document.getElementById('history-content');
        
        if (history.length === 0) {
            content.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <span class="text-4xl mb-4 block">💭</span>
                    <p>No conversation history yet</p>
                </div>
            `;
            return;
        }
        
        content.innerHTML = history.map(msg => {
            const isUser = msg.role === 'user';
            const timestamp = new Date(msg.timestamp).toLocaleTimeString();
            
            return `
                <div class="mb-4 ${isUser ? 'text-right' : 'text-left'}">
                    <div class="inline-block max-w-md ${isUser ? 'bg-purple-100 text-purple-900' : 'bg-gray-100 text-gray-900'} rounded-lg px-3 py-2">
                        <div class="text-sm">${this.formatMessageContent(msg.content)}</div>
                        <div class="text-xs text-gray-500 mt-1">${timestamp}</div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    showFeedbackModal() {
        document.getElementById('feedback-modal').classList.remove('hidden');
        this.resetRating();
    }
    
    hideFeedbackModal() {
        document.getElementById('feedback-modal').classList.add('hidden');
        this.resetRating();
    }
    
    showHistoryModal() {
        document.getElementById('history-modal').classList.remove('hidden');
    }
    
    hideHistoryModal() {
        document.getElementById('history-modal').classList.add('hidden');
    }
    
    setRating(rating) {
        this.currentRating = rating;
        this.highlightStars(rating);
    }
    
    highlightStars(rating) {
        document.querySelectorAll('.star').forEach((star, index) => {
            if (index < rating) {
                star.classList.add('text-yellow-400');
                star.classList.remove('text-gray-300');
            } else {
                star.classList.remove('text-yellow-400');
                star.classList.add('text-gray-300');
            }
        });
    }
    
    resetRating() {
        this.currentRating = 0;
        this.highlightStars(0);
        document.getElementById('feedback-text').value = '';
    }
    
    async submitFeedback() {
        if (!this.sessionId) {
            this.showErrorToast('No conversation to rate');
            return;
        }
        
        if (this.currentRating === 0) {
            this.showErrorToast('Please select a rating');
            return;
        }
        
        try {
            const feedbackText = document.getElementById('feedback-text').value.trim();
            
            const response = await this.makeAPICall(`/api/coach/feedback/${this.sessionId}`, 'POST', {
                rating: this.currentRating,
                feedback: feedbackText
            });
            
            if (response.success) {
                this.showSuccessToast(response.message || 'Thank you for your feedback! 💜');
                this.hideFeedbackModal();
            } else {
                throw new Error(response.message || 'Failed to submit feedback');
            }
            
        } catch (error) {
            console.error('Error submitting feedback:', error);
            this.showErrorToast('I had trouble saving your feedback, but I appreciate it!');
        }
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        const sendButton = document.getElementById('send-button');
        
        if (show) {
            overlay.classList.remove('hidden');
            sendButton.disabled = true;
            this.isLoading = true;
        } else {
            overlay.classList.add('hidden');
            sendButton.disabled = false;
            this.isLoading = false;
        }
    }
    
    updateCoachStatus(status) {
        document.getElementById('coach-status').textContent = status;
    }
    
    showErrorToast(message) {
        const toast = document.getElementById('error-toast');
        const messageEl = document.getElementById('error-message');
        
        messageEl.textContent = message;
        toast.classList.remove('translate-x-full');
        
        setTimeout(() => {
            toast.classList.add('translate-x-full');
        }, 5000);
    }
    
    showSuccessToast(message) {
        const toast = document.getElementById('success-toast');
        const messageEl = document.getElementById('success-message');
        
        messageEl.textContent = message;
        toast.classList.remove('translate-x-full');
        
        setTimeout(() => {
            toast.classList.add('translate-x-full');
        }, 3000);
    }
    
    announceMessage(message, isFromUser) {
        const announcer = document.getElementById('screen-reader-announcements');
        const speaker = isFromUser ? 'You said' : 'AI Coach said';
        
        // Clean message for screen reader
        const cleanMessage = message.replace(/<[^>]*>/g, '').replace(/\n+/g, ' ').trim();
        announcer.textContent = `${speaker}: ${cleanMessage}`;
    }
    
    async makeAPICall(url, method, data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        // Add auth token if available
        const token = await this.getAuthToken();
        if (token) {
            options.headers['Authorization'] = `Bearer ${token}`;
        }
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Please log in to use the AI coach');
            } else if (response.status === 429) {
                throw new Error('I need a quick moment to catch up. Please try again in a few seconds! 😊');
            }
        }
        
        return await response.json();
    }
    
    async getAuthToken() {
        // Get Firebase auth token
        if (window.firebase && firebase.auth && firebase.auth().currentUser) {
            return await firebase.auth().currentUser.getIdToken();
        }
        return null;
    }
}

// Export for use
window.AICoachInterface = AICoachInterface;