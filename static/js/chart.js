function initializeCharts(sessionData) {
    console.log('Initializing charts with data:', sessionData); // Debug

    // Validate sessionData
    if (!Array.isArray(sessionData)) {
        console.error('Session data is not an array:', sessionData);
        return;
    }

    if (sessionData.length === 0) {
        console.warn('No session data available for charts');
        return;
    }

    // Limit to 50 sessions for performance
    const maxDataPoints = 50;
    const dataToDisplay = sessionData.slice(0, maxDataPoints);

    // Prepare data
    const labels = dataToDisplay.map(s => {
        try {
            const date = new Date(s.session_date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } catch (e) {
            console.error('Invalid session_date:', s.session_date);
            return 'Invalid Date';
        }
    });

    const accuracyData = dataToDisplay.map(s => s.accuracy || 0);
    const shotData = dataToDisplay.map(s => s.bullets_shot || 0);
    const detectedData = dataToDisplay.map(s => s.bullets_detected || 0);

    console.log('Chart labels:', labels); // Debug
    console.log('Accuracy data:', accuracyData); // Debug
    console.log('Shot data:', shotData); // Debug
    console.log('Detected data:', detectedData); // Debug

    // Destroy existing charts to prevent duplicates
    const accuracyCtx = document.getElementById('accuracyChart');
    if (accuracyCtx && accuracyCtx.chart) {
        accuracyCtx.chart.destroy();
    }

    // Accuracy Over Time Chart
    if (accuracyCtx) {
        accuracyCtx.chart = new Chart(accuracyCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Accuracy (%)',
                    data: accuracyData,
                    borderColor: '#4B7043', /* Soft olive green */
                    backgroundColor: 'rgba(75, 112, 67, 0.2)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    pointBackgroundColor: '#4B7043',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#2D3748',
                        titleColor: '#FFFFFF',
                        bodyColor: '#FFFFFF',
                        callbacks: {
                            label: function(context) {
                                return `Accuracy: ${context.raw.toFixed(2)}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { color: '#2D3748', callback: value => value + '%' },
                        grid: { color: 'rgba(0, 0, 0, 0.05)' }
                    },
                    x: {
                        ticks: { color: '#2D3748' },
                        grid: { display: false }
                    }
                },
                animation: { duration: 500 }
            }
        });
    } else {
        console.error('Accuracy chart canvas not found');
    }

    // Destroy existing comparison chart
    const comparisonCtx = document.getElementById('comparisonChart');
    if (comparisonCtx && comparisonCtx.chart) {
        comparisonCtx.chart.destroy();
    }

    // Bullets Shot vs Detected Chart
    if (comparisonCtx) {
        comparisonCtx.chart = new Chart(comparisonCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Bullets Shot',
                        data: shotData,
                        backgroundColor: '#F4A261', /* Mustard yellow */
                        borderColor: '#F4A261',
                        borderWidth: 1
                    },
                    {
                        label: 'Bullets Detected',
                        data: detectedData,
                        backgroundColor: '#3182CE', /* Modern blue */
                        borderColor: '#3182CE',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { usePointStyle: true, padding: 20, color: '#2D3748' }
                    },
                    tooltip: {
                        backgroundColor: '#2D3748',
                        titleColor: '#FFFFFF',
                        bodyColor: '#FFFFFF',
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#2D3748' },
                        grid: { color: 'rgba(0, 0, 0, 0.05)' }
                    },
                    x: {
                        ticks: { color: '#2D3748' },
                        grid: { display: false }
                    }
                },
                animation: { duration: 500 }
            }
        });
    } else {
        console.error('Comparison chart canvas not found');
    }
}

// Export chart as PNG
function exportChart(chartId, filename) {
    const canvas = document.getElementById(chartId);
    if (canvas) {
        const link = document.createElement('a');
        link.href = canvas.toDataURL('image/png');
        link.download = `${filename}.png`;
        link.click();
    } else {
        alert('Chart not found');
    }
}