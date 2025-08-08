/**
 * BrainBudget Charts - ADHD-Friendly Interactive Visualizations
 * Designed for neurodivergent users with accessibility and cognitive load reduction in mind
 */

class BrainBudgetCharts {
    constructor() {
        // ADHD-friendly color palette with warm, distinct colors that are colorblind-accessible
        this.colors = {
            // Warm primary palette
            cozyBlue: '#6B9BD6',      // Gentle blue, not harsh
            warmGreen: '#81C784',      // Soft green, encouraging
            sunnyOrange: '#FFB74D',    // Warm orange, energizing
            softPurple: '#BA68C8',     // Calming purple
            gentlePink: '#F48FB1',     // Friendly pink
            earthyBrown: '#A1887F',    // Grounding brown
            
            // Support colors
            successGreen: '#66BB6A',   // For positive feedback
            warningAmber: '#FFA726',   // For attention, not alarming
            softRed: '#EF5350',        // For limits, not harsh
            neutralGray: '#90A4AE',    // For secondary info
            
            // Text and background
            textPrimary: '#37474F',    // Softer than pure black
            textSecondary: '#78909C',  // Lighter for less important info
            background: '#FAFAFA',     // Warm white
            cardBackground: '#FFFFFF', // Pure white for cards
            gridLines: '#E0E6ED',      // Subtle grid lines
            
            // Interactive states
            hover: 'rgba(107, 155, 214, 0.1)', // Light blue hover
            focus: 'rgba(107, 155, 214, 0.3)',  // Stronger focus indicator
        };
        
        // Typography optimized for ADHD (larger, clearer fonts)
        this.typography = {
            fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            titleSize: 18,
            labelSize: 14,
            legendSize: 13,
            tooltipSize: 12
        };
        
        // Animation settings (gentle, not distracting)
        this.animations = {
            duration: 800,
            easing: 'easeInOutCubic',
            delay: (context) => context.dataIndex * 100 // Staggered animations
        };
        
        // Chart instances for cleanup and updates
        this.chartInstances = {};
        
        // Current data filters
        this.filters = {
            dateRange: 'all',
            categories: [],
            minAmount: null,
            maxAmount: null
        };
        
        // Sample data (would come from API in real app)
        this.sampleData = this.generateSampleData();
    }

    /**
     * Generate sample data for demonstration
     */
    generateSampleData() {
        return {
            categories: [
                { name: '🍽️ Food & Dining', amount: 542.30, color: this.colors.warmGreen, transactions: 23 },
                { name: '🚗 Transportation', amount: 284.15, color: this.colors.cozyBlue, transactions: 12 },
                { name: '🎬 Entertainment', amount: 156.80, color: this.colors.sunnyOrange, transactions: 8 },
                { name: '🏠 Bills & Utilities', amount: 423.90, color: this.colors.softPurple, transactions: 6 },
                { name: '🛒 Shopping', amount: 298.45, color: this.colors.gentlePink, transactions: 15 },
                { name: '💊 Healthcare', amount: 89.50, color: this.colors.earthyBrown, transactions: 3 }
            ],
            monthlyTrends: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                spending: [1245, 1156, 1398, 1287, 1445, 1332, 1289],
                budget: [1400, 1400, 1400, 1400, 1400, 1400, 1400]
            },
            monthlyComparison: {
                labels: ['May 2024', 'Jun 2024', 'Jul 2024'],
                current: [1445, 1332, 1289],
                previous: [1356, 1298, 1445]
            },
            budgetGoals: [
                { name: '🍽️ Groceries', current: 245, target: 400, color: this.colors.warmGreen, icon: '🛒' },
                { name: '🍕 Dining Out', current: 178, target: 200, color: this.colors.sunnyOrange, icon: '🍽️' },
                { name: '🚗 Gas & Transport', current: 89, target: 150, color: this.colors.cozyBlue, icon: '⛽' },
                { name: '🎬 Entertainment', current: 156, target: 180, color: this.colors.softPurple, icon: '🎭' },
                { name: '👕 Shopping', current: 298, target: 250, color: this.colors.gentlePink, icon: '🛍️' }
            ]
        };
    }

    /**
     * Initialize the charts system
     */
    init() {
        this.setupEventListeners();
        this.showSkeletons();
        
        // Simulate data loading with gentle delay
        setTimeout(() => {
            this.hideSkeletons();
            this.renderAllCharts();
            this.setupKeyboardNavigation();
            this.announceChartsLoaded(); // For screen readers
        }, 1200);
    }

    /**
     * Show loading skeletons with ADHD-friendly animations
     */
    showSkeletons() {
        const skeletons = [
            'category-chart-skeleton',
            'progress-bars-skeleton', 
            'trends-chart-skeleton',
            'monthly-chart-skeleton'
        ];
        
        skeletons.forEach((id, index) => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = 'block';
                element.style.animationDelay = `${index * 100}ms`;
                element.setAttribute('aria-label', 'Loading chart data...');
            }
        });
    }
    
    /**
     * Hide loading skeletons
     */
    hideSkeletons() {
        const skeletons = [
            'category-chart-skeleton',
            'progress-bars-skeleton',
            'trends-chart-skeleton', 
            'monthly-chart-skeleton'
        ];
        
        skeletons.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = 'none';
                element.removeAttribute('aria-label');
            }
        });
    }

    /**
     * Render all charts with accessibility announcements
     */
    renderAllCharts() {
        try {
            this.renderCategoryDonutChart();
            this.renderSpendingTrendsChart();
            this.renderMonthlyComparisonChart();
            this.renderBudgetProgressBars();
            
            // Announce completion for screen readers
            this.announceToScreenReader('All spending charts have been loaded and are ready for interaction.');
        } catch (error) {
            console.error('Error rendering charts:', error);
            this.showChartError();
        }
    }

    /**
     * Render ADHD-friendly donut chart for spending categories
     */
    renderCategoryDonutChart() {
        const canvas = document.getElementById('category-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.chartInstances.categoryChart) {
            this.chartInstances.categoryChart.destroy();
        }
        
        const data = this.sampleData.categories;
        const total = data.reduce((sum, item) => sum + item.amount, 0);
        
        this.chartInstances.categoryChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(item => item.name),
                datasets: [{
                    data: data.map(item => item.amount),
                    backgroundColor: data.map(item => item.color),
                    borderWidth: 3,
                    borderColor: this.colors.cardBackground,
                    hoverBorderWidth: 4,
                    hoverBorderColor: this.colors.textPrimary
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            font: {
                                family: this.typography.fontFamily,
                                size: this.typography.legendSize,
                                weight: '500'
                            },
                            color: this.colors.textPrimary,
                            padding: 15,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            generateLabels: (chart) => {
                                const datasets = chart.data.datasets;
                                return chart.data.labels.map((label, i) => {
                                    const amount = datasets[0].data[i];
                                    const percentage = ((amount / total) * 100).toFixed(1);
                                    return {
                                        text: `${label} ($${amount.toFixed(2)})`,
                                        fillStyle: datasets[0].backgroundColor[i],
                                        hidden: false,
                                        index: i,
                                        pointStyle: 'circle'
                                    };
                                });
                            }
                        },
                        onHover: (event, legendItem, legend) => {
                            legend.chart.canvas.style.cursor = 'pointer';
                        },
                        onLeave: (event, legendItem, legend) => {
                            legend.chart.canvas.style.cursor = 'default';
                        },
                        onClick: (event, legendItem, legend) => {
                            this.showCategoryDetails(legendItem.index);
                        }
                    },
                    tooltip: {
                        backgroundColor: this.colors.cardBackground,
                        titleColor: this.colors.textPrimary,
                        bodyColor: this.colors.textSecondary,
                        borderColor: this.colors.gridLines,
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        titleFont: {
                            family: this.typography.fontFamily,
                            size: this.typography.tooltipSize,
                            weight: 'bold'
                        },
                        bodyFont: {
                            family: this.typography.fontFamily,
                            size: this.typography.tooltipSize
                        },
                        callbacks: {
                            title: (tooltipItems) => {
                                const item = tooltipItems[0];
                                return data[item.dataIndex].name;
                            },
                            label: (context) => {
                                const item = data[context.dataIndex];
                                const percentage = ((item.amount / total) * 100).toFixed(1);
                                return [
                                    `Amount: $${item.amount.toFixed(2)}`,
                                    `Percentage: ${percentage}%`,
                                    `Transactions: ${item.transactions}`,
                                    '🖱️ Click to see details'
                                ];
                            }
                        }
                    }
                },
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        this.showCategoryDetails(index);
                    }
                },
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: this.animations.duration,
                    easing: this.animations.easing,
                    delay: this.animations.delay
                }
            }
        });
        
        // Add center text showing total
        this.addCenterText(canvas, `$${total.toFixed(2)}`, 'Total Spending');
        
        // Make accessible
        canvas.setAttribute('role', 'img');
        canvas.setAttribute('aria-label', 
            `Spending categories donut chart. Total spending: $${total.toFixed(2)}. ` +
            data.map(item => `${item.name}: $${item.amount.toFixed(2)}`).join(', ')
        );
        canvas.setAttribute('tabindex', '0');
    }

    /**
     * Render spending trends line chart with budget comparison
     */
    renderSpendingTrendsChart() {
        const canvas = document.getElementById('trends-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.chartInstances.trendsChart) {
            this.chartInstances.trendsChart.destroy();
        }
        
        const data = this.sampleData.monthlyTrends;
        
        this.chartInstances.trendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: '💳 Actual Spending',
                        data: data.spending,
                        borderColor: this.colors.cozyBlue,
                        backgroundColor: this.colors.cozyBlue + '20',
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: this.colors.cozyBlue,
                        pointBorderColor: this.colors.cardBackground,
                        pointBorderWidth: 3,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        pointHoverBorderWidth: 3
                    },
                    {
                        label: '🎯 Budget Target',
                        data: data.budget,
                        borderColor: this.colors.successGreen,
                        backgroundColor: 'transparent',
                        borderDash: [8, 4],
                        borderWidth: 3,
                        fill: false,
                        tension: 0,
                        pointRadius: 0,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'start',
                        labels: {
                            font: {
                                family: this.typography.fontFamily,
                                size: this.typography.legendSize,
                                weight: '500'
                            },
                            color: this.colors.textPrimary,
                            usePointStyle: true,
                            padding: 20,
                            boxWidth: 12,
                            boxHeight: 12
                        }
                    },
                    tooltip: {
                        backgroundColor: this.colors.cardBackground,
                        titleColor: this.colors.textPrimary,
                        bodyColor: this.colors.textSecondary,
                        borderColor: this.colors.gridLines,
                        borderWidth: 1,
                        cornerRadius: 8,
                        titleFont: {
                            family: this.typography.fontFamily,
                            size: this.typography.tooltipSize,
                            weight: 'bold'
                        },
                        bodyFont: {
                            family: this.typography.fontFamily,
                            size: this.typography.tooltipSize
                        },
                        callbacks: {
                            title: (tooltipItems) => {
                                return `${tooltipItems[0].label} 2024`;
                            },
                            label: (context) => {
                                const value = context.parsed.y;
                                const budget = data.budget[context.dataIndex];
                                const difference = value - budget;
                                const status = difference > 0 ? 'over' : 'under';
                                
                                let label = `${context.dataset.label}: $${value.toFixed(2)}`;
                                
                                if (context.datasetIndex === 0) { // Spending line
                                    label += `\n${difference > 0 ? '⚠️' : '✅'} $${Math.abs(difference).toFixed(2)} ${status} budget`;
                                }
                                
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                family: this.typography.fontFamily,
                                size: this.typography.labelSize
                            },
                            color: this.colors.textSecondary,
                            padding: 10
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: this.colors.gridLines,
                            drawBorder: false
                        },
                        ticks: {
                            font: {
                                family: this.typography.fontFamily,
                                size: this.typography.labelSize
                            },
                            color: this.colors.textSecondary,
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            },
                            padding: 10
                        }
                    }
                },
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const element = elements[0];
                        const month = data.labels[element.index];
                        this.showMonthDetails(month, element.index);
                    }
                },
                animation: {
                    duration: this.animations.duration,
                    easing: this.animations.easing,
                    delay: (context) => {
                        return context.type === 'data' && context.mode === 'default' 
                            ? context.dataIndex * 100 
                            : 0;
                    }
                }
            }
        });
        
        // Make accessible
        canvas.setAttribute('role', 'img');
        canvas.setAttribute('aria-label', 
            `Spending trends line chart for ${data.labels.join(', ')}. ` +
            `Shows actual spending vs budget target. Click on data points for details.`
        );
        canvas.setAttribute('tabindex', '0');
    }

    /**
     * Render monthly comparison bar chart
     */
    renderMonthlyComparisonChart() {
        const canvas = document.getElementById('monthly-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.chartInstances.monthlyChart) {
            this.chartInstances.monthlyChart.destroy();
        }
        
        const data = this.sampleData.monthlyComparison;
        
        this.chartInstances.monthlyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: '📊 This Year',
                        data: data.current,
                        backgroundColor: this.colors.cozyBlue,
                        borderColor: this.colors.cozyBlue,
                        borderWidth: 2,
                        borderRadius: 6,
                        borderSkipped: false
                    },
                    {
                        label: '📈 Last Year',
                        data: data.previous,
                        backgroundColor: this.colors.neutralGray + '60',
                        borderColor: this.colors.neutralGray,
                        borderWidth: 2,
                        borderRadius: 6,
                        borderSkipped: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'start',
                        labels: {
                            font: {
                                family: this.typography.fontFamily,
                                size: this.typography.legendSize,
                                weight: '500'
                            },
                            color: this.colors.textPrimary,
                            usePointStyle: true,
                            padding: 20,
                            boxWidth: 12,
                            boxHeight: 12
                        }
                    },
                    tooltip: {
                        backgroundColor: this.colors.cardBackground,
                        titleColor: this.colors.textPrimary,
                        bodyColor: this.colors.textSecondary,
                        borderColor: this.colors.gridLines,
                        borderWidth: 1,
                        cornerRadius: 8,
                        titleFont: {
                            family: this.typography.fontFamily,
                            size: this.typography.tooltipSize,
                            weight: 'bold'
                        },
                        bodyFont: {
                            family: this.typography.fontFamily,
                            size: this.typography.tooltipSize
                        },
                        callbacks: {
                            title: (tooltipItems) => {
                                return tooltipItems[0].label;
                            },
                            label: (context) => {
                                const value = context.parsed.y;
                                const otherDatasetIndex = context.datasetIndex === 0 ? 1 : 0;
                                const otherValue = data.current[context.dataIndex];
                                const difference = context.datasetIndex === 0 
                                    ? value - data.previous[context.dataIndex]
                                    : data.current[context.dataIndex] - value;
                                
                                const percentage = ((difference / value) * 100).toFixed(1);
                                const trend = difference > 0 ? 'increase' : 'decrease';
                                const emoji = difference > 0 ? '📈' : '📉';
                                
                                return [
                                    `${context.dataset.label}: $${value.toLocaleString()}`,
                                    `${emoji} ${Math.abs(percentage)}% ${trend} from last year`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                family: this.typography.fontFamily,
                                size: this.typography.labelSize
                            },
                            color: this.colors.textSecondary,
                            padding: 10
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: this.colors.gridLines,
                            drawBorder: false
                        },
                        ticks: {
                            font: {
                                family: this.typography.fontFamily,
                                size: this.typography.labelSize
                            },
                            color: this.colors.textSecondary,
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            },
                            padding: 10
                        }
                    }
                },
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const element = elements[0];
                        const month = data.labels[element.index];
                        this.showMonthlyComparison(month, element.index);
                    }
                },
                animation: {
                    duration: this.animations.duration,
                    easing: this.animations.easing,
                    delay: (context) => {
                        return context.type === 'data' && context.mode === 'default'
                            ? context.dataIndex * 150 + (context.datasetIndex * 300)
                            : 0;
                    }
                }
            }
        });
        
        // Make accessible
        canvas.setAttribute('role', 'img');
        canvas.setAttribute('aria-label', 
            `Monthly spending comparison bar chart comparing this year to last year for ${data.labels.join(', ')}.`
        );
        canvas.setAttribute('tabindex', '0');
    }

    /**
     * Render ADHD-friendly budget progress bars with animations
     */
    renderBudgetProgressBars() {
        const container = document.getElementById('progress-bars-container');
        if (!container) return;
        
        container.innerHTML = ''; // Clear existing content
        
        this.sampleData.budgetGoals.forEach((goal, index) => {
            const percentage = Math.min((goal.current / goal.target) * 100, 100);
            const isOverBudget = goal.current > goal.target;
            const remainingBudget = goal.target - goal.current;
            
            // Determine status and color
            let statusClass = 'on-track';
            let statusText = '✅ On track!';
            let progressColor = goal.color;
            
            if (isOverBudget) {
                statusClass = 'over-budget';
                statusText = '⚠️ Over budget';
                progressColor = this.colors.softRed;
            } else if (percentage > 90) {
                statusClass = 'close-to-limit';
                statusText = '⚡ Close to limit';
                progressColor = this.colors.warningAmber;
            } else if (percentage > 75) {
                statusClass = 'doing-well';
                statusText = '👍 Doing well';
                progressColor = this.colors.successGreen;
            }
            
            const progressBarHTML = `
                <div class="progress-goal-card ${statusClass}" 
                     tabindex="0" 
                     role="progressbar" 
                     aria-valuenow="${goal.current}" 
                     aria-valuemin="0" 
                     aria-valuemax="${goal.target}"
                     aria-label="${goal.name}: $${goal.current} of $${goal.target} budget used">
                    
                    <div class="progress-goal-header">
                        <div class="progress-goal-title">
                            <span class="progress-goal-icon">${goal.icon}</span>
                            <span class="progress-goal-name">${goal.name}</span>
                        </div>
                        <div class="progress-goal-status ${statusClass}">${statusText}</div>
                    </div>
                    
                    <div class="progress-goal-amounts">
                        <div class="progress-current">Spent: <strong>$${goal.current.toFixed(2)}</strong></div>
                        <div class="progress-target">Budget: $${goal.target.toFixed(2)}</div>
                        <div class="progress-remaining ${isOverBudget ? 'over-budget' : ''}">
                            ${isOverBudget 
                                ? `Over by: <strong class="over-amount">$${Math.abs(remainingBudget).toFixed(2)}</strong>`
                                : `Remaining: <strong>$${remainingBudget.toFixed(2)}</strong>`
                            }
                        </div>
                    </div>
                    
                    <div class="progress-bar-wrapper">
                        <div class="progress-bar-track">
                            <div class="progress-bar-fill ${statusClass}" 
                                 style="--progress-width: ${percentage}%; --progress-color: ${progressColor};"
                                 data-percentage="${percentage.toFixed(1)}%">
                                <div class="progress-bar-shimmer"></div>
                            </div>
                        </div>
                        <div class="progress-percentage">${percentage.toFixed(1)}%</div>
                    </div>
                    
                    <div class="progress-goal-actions">
                        <button class="btn-link" onclick="charts.showGoalDetails(${index})">
                            📊 View details
                        </button>
                        <button class="btn-link" onclick="charts.editGoal(${index})">
                            ✏️ Edit budget
                        </button>
                    </div>
                </div>
            `;
            
            container.insertAdjacentHTML('beforeend', progressBarHTML);
            
            // Animate progress bar after a delay
            setTimeout(() => {
                const progressBar = container.lastElementChild.querySelector('.progress-bar-fill');
                progressBar.style.transform = 'scaleX(1)';
            }, index * 150);
        });
        
        // Add keyboard navigation for progress bars
        this.setupProgressBarNavigation(container);
    }

    /**
     * Setup event listeners for chart interactions
     */
    setupEventListeners() {
        // Filter controls
        document.getElementById('date-range-filter')?.addEventListener('change', (e) => {
            this.filters.dateRange = e.target.value;
            this.applyFilters();
        });
        
        document.getElementById('category-filter')?.addEventListener('change', (e) => {
            const selectedCategories = Array.from(e.target.selectedOptions).map(option => option.value);
            this.filters.categories = selectedCategories;
            this.applyFilters();
        });
        
        // Export buttons
        document.getElementById('export-charts')?.addEventListener('click', () => {
            this.exportChartsAsImages();
        });
        
        // Responsive handling
        window.addEventListener('resize', this.debounce(() => {
            this.handleResize();
        }, 250));
    }
    
    /**
     * Setup keyboard navigation for accessibility
     */
    setupKeyboardNavigation() {
        // Navigate between chart elements with arrow keys
        document.addEventListener('keydown', (e) => {
            if (e.target.classList.contains('chart-canvas') || e.target.classList.contains('progress-goal-card')) {
                this.handleKeyboardNavigation(e);
            }
        });
    }
    
    /**
     * Handle keyboard navigation events
     */
    handleKeyboardNavigation(event) {
        const { key, target } = event;
        
        switch (key) {
            case 'Enter':
            case ' ':
                event.preventDefault();
                if (target.classList.contains('chart-canvas')) {
                    this.announceChartData(target);
                } else if (target.classList.contains('progress-goal-card')) {
                    const index = Array.from(target.parentNode.children).indexOf(target);
                    this.showGoalDetails(index);
                }
                break;
                
            case 'ArrowUp':
            case 'ArrowDown':
                event.preventDefault();
                this.navigateToNextChart(key === 'ArrowUp' ? -1 : 1);
                break;
        }
    }
    
    /**
     * Navigate to the next focusable chart element
     */
    navigateToNextChart(direction) {
        const focusableElements = document.querySelectorAll('[tabindex="0"]');
        const currentIndex = Array.from(focusableElements).indexOf(document.activeElement);
        const nextIndex = (currentIndex + direction + focusableElements.length) % focusableElements.length;
        
        focusableElements[nextIndex].focus();
    }
    
    /**
     * Add center text to donut chart
     */
    addCenterText(canvas, primaryText, secondaryText) {
        const chart = Chart.getChart(canvas);
        if (!chart) return;
        
        const centerPlugin = {
            id: 'centerText',
            beforeDraw: (chart) => {
                const { ctx, canvas } = chart;
                const centerX = canvas.width / 2;
                const centerY = canvas.height / 2;
                
                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                // Primary text (amount)
                ctx.font = `bold ${this.typography.titleSize}px ${this.typography.fontFamily}`;
                ctx.fillStyle = this.colors.textPrimary;
                ctx.fillText(primaryText, centerX, centerY - 5);
                
                // Secondary text (label)
                ctx.font = `${this.typography.labelSize}px ${this.typography.fontFamily}`;
                ctx.fillStyle = this.colors.textSecondary;
                ctx.fillText(secondaryText, centerX, centerY + 20);
                
                ctx.restore();
            }
        };
        
        chart.options.plugins = chart.options.plugins || {};
        chart.plugins.register(centerPlugin);
    }
    
    /**
     * Setup progress bar keyboard navigation
     */
    setupProgressBarNavigation(container) {
        const progressBars = container.querySelectorAll('.progress-goal-card');
        
        progressBars.forEach((bar, index) => {
            bar.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.showGoalDetails(index);
                }
            });
            
            bar.addEventListener('focus', () => {
                bar.classList.add('keyboard-focus');
            });
            
            bar.addEventListener('blur', () => {
                bar.classList.remove('keyboard-focus');
            });
        });
    }
    
    /**
     * Apply filters to all charts
     */
    applyFilters() {
        this.showSkeletons();
        
        setTimeout(() => {
            this.hideSkeletons();
            this.renderAllCharts();
            this.announceToScreenReader('Charts updated with new filters');
        }, 600);
    }
    
    /**
     * Handle window resize events
     */
    handleResize() {
        Object.values(this.chartInstances).forEach(chart => {
            if (chart && chart.resize) {
                chart.resize();
            }
        });
    }
    
    /**
     * Export all charts as images
     */
    exportChartsAsImages() {
        const charts = [
            { id: 'category-chart', name: 'spending-categories' },
            { id: 'trends-chart', name: 'spending-trends' },
            { id: 'monthly-chart', name: 'monthly-comparison' }
        ];
        
        charts.forEach(({ id, name }) => {
            const canvas = document.getElementById(id);
            if (canvas) {
                const link = document.createElement('a');
                link.download = `brainbudget-${name}-${new Date().toISOString().split('T')[0]}.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();
            }
        });
        
        this.announceToScreenReader('Charts exported as PNG images');
    }
    
    /**
     * Show category details modal/popup
     */
    showCategoryDetails(categoryIndex) {
        const category = this.sampleData.categories[categoryIndex];
        this.announceToScreenReader(`Showing details for ${category.name} category`);
        
        // This would typically open a modal with transaction details
        // Show category details
    }
    
    /**
     * Show month details for trends chart
     */
    showMonthDetails(month, monthIndex) {
        this.announceToScreenReader(`Showing spending details for ${month}`);
        
        // This would typically show detailed breakdown for the month
        // Show month details
    }
    
    /**
     * Show monthly comparison details
     */
    showMonthlyComparison(month, monthIndex) {
        this.announceToScreenReader(`Showing comparison details for ${month}`);
        
        // This would show year-over-year comparison details
        // Show monthly comparison
    }
    
    /**
     * Show goal details for progress bars
     */
    showGoalDetails(goalIndex) {
        const goal = this.sampleData.budgetGoals[goalIndex];
        this.announceToScreenReader(`Showing budget details for ${goal.name}`);
        
        // This would open goal details modal
        // Show goal details
    }
    
    /**
     * Edit budget goal
     */
    editGoal(goalIndex) {
        const goal = this.sampleData.budgetGoals[goalIndex];
        this.announceToScreenReader(`Opening editor for ${goal.name} budget`);
        
        // This would open goal editing interface
        // Edit goal
    }
    
    /**
     * Show chart error message
     */
    showChartError() {
        const errorMessage = document.createElement('div');
        errorMessage.className = 'chart-error-message';
        errorMessage.innerHTML = `
            <div class="error-icon">📊❌</div>
            <h3>Oops! Charts couldn't load</h3>
            <p>Don't worry, we're working on it! Try refreshing the page.</p>
            <button onclick="location.reload()" class="btn-primary">🔄 Refresh Page</button>
        `;
        
        document.querySelector('.charts-container')?.appendChild(errorMessage);
        this.announceToScreenReader('Error loading charts. Please refresh the page.');
    }
    
    /**
     * Announce chart completion to screen readers
     */
    announceChartsLoaded() {
        this.announceToScreenReader('All spending visualizations have loaded successfully and are ready for interaction.');
    }
    
    /**
     * Announce chart data to screen readers
     */
    announceChartData(chartCanvas) {
        const chartId = chartCanvas.id;
        let announcement = '';
        
        switch (chartId) {
            case 'category-chart':
                const total = this.sampleData.categories.reduce((sum, item) => sum + item.amount, 0);
                announcement = `Spending categories: Total $${total.toFixed(2)}. ` +
                    this.sampleData.categories.map(item => 
                        `${item.name}: $${item.amount.toFixed(2)}`
                    ).join(', ');
                break;
            case 'trends-chart':
                announcement = 'Monthly spending trends with budget comparison. ' +
                    this.sampleData.monthlyTrends.labels.map((month, i) => 
                        `${month}: $${this.sampleData.monthlyTrends.spending[i]}`
                    ).join(', ');
                break;
            case 'monthly-chart':
                announcement = 'Monthly comparison chart showing this year vs last year spending.';
                break;
        }
        
        this.announceToScreenReader(announcement);
    }
    
    /**
     * Announce message to screen readers
     */
    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        // Remove after announcement
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }
    
    /**
     * Debounce utility function
     */
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
    }
    
    /**
     * Destroy all chart instances (cleanup)
     */
    destroy() {
        Object.values(this.chartInstances).forEach(chart => {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        });
        this.chartInstances = {};
    }
}

// Global instance for easy access
const charts = new BrainBudgetCharts();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => charts.init());
} else {
    charts.init();
}