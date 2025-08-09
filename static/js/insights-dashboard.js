/**
 * ADHD-Friendly Insights Dashboard for BrainBudget
 * Displays spending pattern analysis with ML insights
 */

class InsightsDashboard {
    constructor() {
        this.currentPeriod = 90;
        this.consentStatus = null;
        this.lastUpdate = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.checkConsentStatus();
    }
    
    setupEventListeners() {
        // Time period selector
        document.getElementById('time-period')?.addEventListener('change', (e) => {
            this.currentPeriod = parseInt(e.target.value);
            this.refreshInsights();
        });
        
        // Refresh button
        document.getElementById('refresh-insights')?.addEventListener('click', () => {
            this.refreshInsights();
        });
        
        // Consent banner buttons
        document.getElementById('enable-insights')?.addEventListener('click', () => {
            this.enableInsights();
        });
        
        document.getElementById('learn-more')?.addEventListener('click', () => {
            this.showPrivacyModal();
        });
        
        // Privacy modal buttons
        document.getElementById('accept-privacy')?.addEventListener('click', () => {
            this.acceptPrivacy();
        });
        
        document.getElementById('cancel-privacy')?.addEventListener('click', () => {
            this.hidePrivacyModal();
        });
        
        document.getElementById('close-privacy')?.addEventListener('click', () => {
            this.hidePrivacyModal();
        });
        
        // Close modal on background click
        document.getElementById('privacy-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'privacy-modal') {
                this.hidePrivacyModal();
            }
        });
    }
    
    async checkConsentStatus() {
        try {
            const response = await this.makeAPICall('/api/analytics/consent', 'GET');
            
            if (response.success) {
                this.consentStatus = response.consent;
                
                if (this.consentStatus) {
                    this.loadInsights();
                } else {
                    this.showConsentBanner();
                }
            }
            
        } catch (error) {
            console.error('Error checking consent:', error);
            this.showError('Unable to load consent status');
        }
    }
    
    showConsentBanner() {
        document.getElementById('consent-banner')?.classList.remove('hidden');
        document.getElementById('main-content')?.classList.add('hidden');
        document.getElementById('no-data-state')?.classList.add('hidden');
    }
    
    hideConsentBanner() {
        document.getElementById('consent-banner')?.classList.add('hidden');
    }
    
    showPrivacyModal() {
        document.getElementById('privacy-modal')?.classList.remove('hidden');
    }
    
    hidePrivacyModal() {
        document.getElementById('privacy-modal')?.classList.add('hidden');
    }
    
    async enableInsights() {
        this.showPrivacyModal();
    }
    
    async acceptPrivacy() {
        try {
            this.hidePrivacyModal();
            this.showLoading(true);
            
            // Update consent
            const response = await this.makeAPICall('/api/analytics/consent', 'POST', {
                consent: true
            });
            
            if (response.success) {
                this.consentStatus = true;
                this.hideConsentBanner();
                this.showSuccess('Smart insights enabled! Analyzing your data...');
                
                // Load insights after consent
                setTimeout(() => {
                    this.loadInsights();
                }, 1000);
            } else {
                throw new Error(response.message || 'Failed to update consent');
            }
            
        } catch (error) {
            console.error('Error accepting privacy:', error);
            this.showError('Unable to enable insights right now');
        } finally {
            this.showLoading(false);
        }
    }
    
    async refreshInsights() {
        if (!this.consentStatus) {
            this.checkConsentStatus();
            return;
        }
        
        this.loadInsights();
    }
    
    async loadInsights() {
        try {
            this.showLoading(true);
            
            // Load all insights in parallel
            const [
                mainInsights,
                subscriptions,
                predictions,
                anomalies,
                categoryTrends
            ] = await Promise.all([
                this.loadMainInsights(),
                this.loadSubscriptions(),
                this.loadPredictions(),
                this.loadAnomalies(),
                this.loadCategoryTrends()
            ]);
            
            // Show main content
            document.getElementById('main-content')?.classList.remove('hidden');
            document.getElementById('no-data-state')?.classList.add('hidden');
            
            // Render insights
            this.renderMainInsights(mainInsights);
            this.renderSubscriptions(subscriptions);
            this.renderPredictions(predictions);
            this.renderAnomalies(anomalies);
            this.renderCategoryTrends(categoryTrends);
            
            this.lastUpdate = new Date();
            
        } catch (error) {
            console.error('Error loading insights:', error);
            this.handleInsightsError(error);
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadMainInsights() {
        const response = await this.makeAPICall(
            `/api/analytics/insights?days=${this.currentPeriod}&limit=6`, 
            'GET'
        );
        return response;
    }
    
    async loadSubscriptions() {
        const response = await this.makeAPICall(
            `/api/analytics/subscriptions?days=${this.currentPeriod * 2}`, // Longer period for subscriptions
            'GET'
        );
        return response;
    }
    
    async loadPredictions() {
        const response = await this.makeAPICall(
            '/api/analytics/predictions?period=monthly',
            'GET'
        );
        return response;
    }
    
    async loadAnomalies() {
        const response = await this.makeAPICall(
            `/api/analytics/anomalies?days=${this.currentPeriod}&limit=5`,
            'GET'
        );
        return response;
    }
    
    async loadCategoryTrends() {
        const response = await this.makeAPICall(
            `/api/analytics/category-trends?days=${this.currentPeriod}&limit=8`,
            'GET'
        );
        return response;
    }
    
    renderMainInsights(data) {
        const container = document.getElementById('key-insights');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!data.success || !data.insights || data.insights.length === 0) {
            container.innerHTML = `
                <div class="col-span-full bg-gray-50 rounded-lg p-6 text-center">
                    <span class="text-4xl mb-4 block">🔍</span>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">Building Your Insights</h3>
                    <p class="text-gray-600">We're analyzing your spending patterns. Check back soon for personalized insights!</p>
                </div>
            `;
            return;
        }
        
        data.insights.forEach(insight => {
            const card = this.createInsightCard(insight);
            container.appendChild(card);
        });
    }
    
    createInsightCard(insight) {
        const card = document.createElement('div');
        card.className = `insight-card bg-white rounded-lg shadow-sm border border-gray-200 p-6 insight-${insight.type}`;
        
        const typeIcons = {
            'positive': '🎉',
            'warning': '⚠️',
            'neutral': '💡',
            'celebration': '🌟'
        };
        
        const icon = typeIcons[insight.type] || '📊';
        
        card.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <span class="text-2xl">${icon}</span>
                </div>
                <div class="ml-4 flex-1">
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">${insight.title}</h3>
                    <p class="text-gray-700 mb-3">${insight.message}</p>
                    
                    ${insight.amount ? `
                        <div class="bg-blue-50 rounded-lg p-3 mb-3">
                            <p class="text-blue-800 font-medium">Amount: $${insight.amount.toLocaleString()}</p>
                        </div>
                    ` : ''}
                    
                    ${insight.adhd_note ? `
                        <div class="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-3">
                            <p class="text-purple-800 text-sm">
                                <strong>🧠 ADHD Insight:</strong> ${insight.adhd_note}
                            </p>
                        </div>
                    ` : ''}
                    
                    ${insight.tips && insight.tips.length > 0 ? `
                        <div class="space-y-2">
                            <p class="text-sm font-medium text-gray-700">💡 Actionable Tips:</p>
                            <ul class="text-sm text-gray-600 space-y-1">
                                ${insight.tips.map(tip => `<li class="flex items-start"><span class="text-green-500 mr-2">•</span><span>${tip}</span></li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    
                    <div class="mt-4 flex items-center justify-between">
                        <div class="flex items-center text-xs text-gray-500">
                            <span class="mr-2">Confidence:</span>
                            <div class="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div class="h-full bg-blue-500 rounded-full progress-bar" style="--progress-width: ${(insight.confidence * 100).toFixed(0)}%"></div>
                            </div>
                            <span class="ml-2">${(insight.confidence * 100).toFixed(0)}%</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }
    
    renderSubscriptions(data) {
        const container = document.getElementById('subscriptions-content');
        if (!container) return;
        
        if (!data.success || !data.subscriptions || data.subscriptions.length === 0) {
            container.innerHTML = `
                <div class="text-center py-6">
                    <span class="text-4xl mb-4 block">🔍</span>
                    <p class="text-gray-600">No recurring subscriptions detected yet.</p>
                    <p class="text-sm text-gray-500 mt-2">We'll identify patterns as you add more transactions!</p>
                </div>
            `;
            return;
        }
        
        const subscriptions = data.subscriptions.slice(0, 5); // Show top 5
        const totalMonthly = data.summary?.estimated_monthly_total || 0;
        
        container.innerHTML = `
            <div class="mb-4 p-4 bg-blue-50 rounded-lg">
                <div class="flex justify-between items-center">
                    <span class="text-blue-800 font-medium">Total Monthly Subscriptions</span>
                    <span class="text-2xl font-bold text-blue-600">$${totalMonthly.toFixed(2)}</span>
                </div>
            </div>
            
            <div class="space-y-3">
                ${subscriptions.map(sub => `
                    <div class="flex justify-between items-center p-3 border border-gray-200 rounded-lg">
                        <div class="flex-1">
                            <p class="font-medium text-gray-900">${sub.merchant}</p>
                            <p class="text-sm text-gray-500">
                                ${sub.frequency} • ${sub.total_occurrences} payments detected
                            </p>
                            ${sub.adhd_insight ? `
                                <p class="text-xs text-purple-600 mt-1">🧠 ${sub.adhd_insight}</p>
                            ` : ''}
                        </div>
                        <div class="text-right">
                            <p class="font-semibold text-gray-900">$${sub.amount.toFixed(2)}</p>
                            <div class="flex items-center text-xs text-gray-500">
                                <span class="mr-1">Confidence:</span>
                                <div class="w-12 h-1 bg-gray-200 rounded overflow-hidden">
                                    <div class="h-full bg-green-500" style="width: ${(sub.confidence * 100).toFixed(0)}%"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}
                
                ${data.subscriptions.length > 5 ? `
                    <p class="text-center text-sm text-gray-500 mt-4">
                        And ${data.subscriptions.length - 5} more subscriptions detected
                    </p>
                ` : ''}
            </div>
        `;
    }
    
    renderPredictions(data) {
        const container = document.getElementById('predictions-content');
        if (!container) return;
        
        if (!data.success || !data.predictions) {
            container.innerHTML = `
                <div class="text-center py-6">
                    <span class="text-4xl mb-4 block">🔮</span>
                    <p class="text-gray-600">Predictions will be available with more data.</p>
                    <p class="text-sm text-gray-500 mt-2">Keep tracking your expenses for accurate forecasts!</p>
                </div>
            `;
            return;
        }
        
        const pred = data.predictions;
        
        container.innerHTML = `
            <div class="text-center mb-6">
                <div class="text-4xl font-bold text-blue-600 mb-2">$${pred.predicted_amount.toFixed(0)}</div>
                <p class="text-lg text-gray-700">${pred.period_label}</p>
                <p class="text-sm text-gray-500">Confidence: ${pred.confidence_level}</p>
            </div>
            
            <div class="space-y-4">
                <div class="bg-gray-50 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-2">
                        <span class="text-sm font-medium text-gray-700">Prediction Accuracy</span>
                        <span class="text-sm text-gray-600">${(pred.accuracy_score * 100).toFixed(0)}%</span>
                    </div>
                    <div class="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div class="h-full bg-blue-500" style="width: ${(pred.accuracy_score * 100).toFixed(0)}%"></div>
                    </div>
                </div>
                
                ${data.adhd_note ? `
                    <div class="bg-purple-50 border border-purple-200 rounded-lg p-3">
                        <p class="text-purple-800 text-sm">
                            <strong>🧠 ADHD Note:</strong> ${data.adhd_note}
                        </p>
                    </div>
                ` : ''}
                
                ${pred.daily_breakdown && pred.daily_breakdown.length > 0 ? `
                    <div>
                        <h4 class="text-sm font-medium text-gray-700 mb-3">Weekly Breakdown</h4>
                        <div class="space-y-2">
                            ${pred.daily_breakdown.map(day => `
                                <div class="flex justify-between items-center text-sm">
                                    <span class="text-gray-600">${new Date(day.date).toLocaleDateString('en-US', {weekday: 'short', month: 'short', day: 'numeric'})}</span>
                                    <span class="font-medium">$${day.predicted_amount.toFixed(0)}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    renderAnomalies(data) {
        const container = document.getElementById('anomalies-content');
        if (!container) return;
        
        if (!data.success || !data.anomalies || data.anomalies.length === 0) {
            container.innerHTML = `
                <div class="text-center py-6">
                    <span class="text-4xl mb-4 block">✅</span>
                    <p class="text-gray-600">No unusual transactions detected!</p>
                    <p class="text-sm text-gray-500 mt-2">Your spending patterns look consistent and healthy.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="mb-4 text-sm text-gray-600">
                Found ${data.summary?.total_anomalies || data.anomalies.length} unusual transactions 
                (${(data.summary?.anomaly_percentage || 0).toFixed(1)}% of all transactions)
            </div>
            
            <div class="space-y-3">
                ${data.anomalies.map(anomaly => `
                    <div class="border border-orange-200 rounded-lg p-3 bg-orange-50">
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex-1">
                                <p class="font-medium text-gray-900">${anomaly.merchant}</p>
                                <p class="text-sm text-gray-600">${new Date(anomaly.date).toLocaleDateString()}</p>
                            </div>
                            <div class="text-right">
                                <p class="font-bold text-orange-600">$${Math.abs(anomaly.amount).toFixed(2)}</p>
                                <p class="text-xs text-orange-500">${anomaly.category}</p>
                            </div>
                        </div>
                        
                        <p class="text-sm text-gray-700 mb-2">${anomaly.reason}</p>
                        
                        ${anomaly.adhd_insight ? `
                            <div class="bg-purple-50 border border-purple-200 rounded p-2">
                                <p class="text-xs text-purple-700">🧠 ${anomaly.adhd_insight}</p>
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    renderCategoryTrends(data) {
        const container = document.getElementById('category-trends-content');
        if (!container) return;
        
        if (!data.success || !data.trends || data.trends.length === 0) {
            container.innerHTML = `
                <div class="text-center py-6">
                    <span class="text-4xl mb-4 block">📈</span>
                    <p class="text-gray-600">Category trends will appear with more transaction data.</p>
                </div>
            `;
            return;
        }
        
        const trends = data.trends.slice(0, 6); // Show top 6 categories
        
        container.innerHTML = `
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                ${trends.map(trend => {
                    const trendIcon = trend.trend_direction === 'increasing' ? '📈' : 
                                    trend.trend_direction === 'decreasing' ? '📉' : '➡️';
                    const trendColor = trend.trend_direction === 'increasing' ? 'text-red-600' : 
                                     trend.trend_direction === 'decreasing' ? 'text-green-600' : 'text-gray-600';
                    
                    return `
                        <div class="border border-gray-200 rounded-lg p-4">
                            <div class="flex items-center justify-between mb-2">
                                <h4 class="font-medium text-gray-900 capitalize">${trend.category}</h4>
                                <span class="text-xl">${trendIcon}</span>
                            </div>
                            
                            <div class="space-y-2 text-sm">
                                <div class="flex justify-between">
                                    <span class="text-gray-600">Weekly Average:</span>
                                    <span class="font-medium">$${trend.average_weekly.toFixed(2)}</span>
                                </div>
                                
                                <div class="flex justify-between">
                                    <span class="text-gray-600">Trend:</span>
                                    <span class="${trendColor} font-medium capitalize">${trend.trend_direction}</span>
                                </div>
                                
                                <div class="flex justify-between">
                                    <span class="text-gray-600">Consistency:</span>
                                    <span class="font-medium">${trend.variability < 0.3 ? 'High' : trend.variability < 0.6 ? 'Medium' : 'Variable'}</span>
                                </div>
                            </div>
                            
                            ${trend.adhd_insight ? `
                                <div class="mt-3 bg-purple-50 border border-purple-200 rounded p-2">
                                    <p class="text-xs text-purple-700">🧠 ${trend.adhd_insight}</p>
                                </div>
                            ` : ''}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }
    
    handleInsightsError(error) {
        // Check for specific error types
        if (error.message && error.message.includes('consent')) {
            this.showConsentBanner();
            return;
        }
        
        // Show no data state for insufficient data
        if (error.message && error.message.includes('insufficient')) {
            document.getElementById('no-data-state')?.classList.remove('hidden');
            document.getElementById('main-content')?.classList.add('hidden');
            return;
        }
        
        // General error handling
        document.getElementById('main-content')?.classList.remove('hidden');
        const container = document.getElementById('key-insights');
        if (container) {
            container.innerHTML = `
                <div class="col-span-full bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                    <span class="text-4xl mb-4 block">🔧</span>
                    <h3 class="text-lg font-semibold text-red-800 mb-2">Insights Temporarily Unavailable</h3>
                    <p class="text-red-700">We're having trouble analyzing your data right now. Please try again in a few minutes!</p>
                    <button class="mt-4 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors" onclick="window.location.reload()">
                        Try Again
                    </button>
                </div>
            `;
        }
    }
    
    showLoading(show) {
        const loadingState = document.getElementById('loading-state');
        const mainContent = document.getElementById('main-content');
        
        if (show) {
            loadingState?.classList.remove('hidden');
            mainContent?.classList.add('hidden');
        } else {
            loadingState?.classList.add('hidden');
            // mainContent visibility controlled by other methods
        }
    }
    
    showError(message) {
        const toast = document.getElementById('error-toast');
        const messageEl = document.getElementById('error-message');
        
        if (toast && messageEl) {
            messageEl.textContent = message;
            toast.classList.remove('translate-x-full');
            
            setTimeout(() => {
                toast.classList.add('translate-x-full');
            }, 5000);
        }
    }
    
    showSuccess(message) {
        const toast = document.getElementById('success-toast');
        const messageEl = document.getElementById('success-message');
        
        if (toast && messageEl) {
            messageEl.textContent = message;
            toast.classList.remove('translate-x-full');
            
            setTimeout(() => {
                toast.classList.add('translate-x-full');
            }, 3000);
        }
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
            if (response.status === 403) {
                throw new Error('ML analytics consent required');
            } else if (response.status === 401) {
                throw new Error('Please log in to view insights');
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
window.InsightsDashboard = InsightsDashboard;