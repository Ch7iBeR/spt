// Variables globales pour stocker les instances des graphiques
let accuracyChartInstance = null;
let comparisonChartInstance = null;
let pieChartInstance = null;

// Fonction pour initialiser le graphique circulaire (précision moyenne)
function initializePieChart(avgAccuracy) {
    const pieCtx = document.getElementById('accuracyPieChart');
    if (pieCtx) {
        pieChartInstance = new Chart(pieCtx, {
            type: 'pie',
            data: {
                labels: ['Accuracy', 'Remaining'],
                datasets: [{
                    data: [avgAccuracy*100 , 100 - avgAccuracy ],
                    backgroundColor: [
                        '#667c3e',
                        'rgba(0, 0, 0, 0.7)'
                    ],
                    borderColor: [
                        'rgb(102, 124, 62,1)',
                        'rgb(0, 0, 0)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.raw.toFixed(2) + '%';
                            }
                        }
                    },
                    datalabels: {
                        formatter: (value) => value.toFixed(2) + '%',
                        color: '#000'
                    }
                }
            }
        });
    }
}

// Fonction pour initialiser tous les graphiques
function initializeCharts(sessionData, avgAccuracy) {
    // Si aucune donnée, utiliser des valeurs par défaut
    if (!sessionData || sessionData.length === 0) {
        sessionData = [{
            session_date: new Date().toISOString(),
            bullets_shot: 0,
            bullets_detected: 0,
            accuracy: 0
        }];
    }

    // Vérifier et formater les données
    const labels = sessionData.map(s => {
        const date = new Date(s.session_date);
        return isNaN(date) ? 'Unknown Date' : date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    });
    const accuracyData = sessionData.map(s => {
        const accuracy = s.accuracy !== undefined && s.accuracy !== null ? s.accuracy : 0;
        return Number.isFinite(accuracy*100) ? accuracy*100 : 0;
    });
    const shotData = sessionData.map(s => s.bullets_shot || 0);
    const detectedData = sessionData.map(s => s.bullets_detected || 0);

    // Graphique en ligne (précision au fil du temps)
    const accuracyCtx = document.getElementById('accuracyChart');
    if (accuracyCtx) {
        if (accuracyChartInstance) accuracyChartInstance.destroy(); // Détruire l'instance précédente
        accuracyChartInstance = new Chart(accuracyCtx, {
            type: 'line',
            data: {
                labels: labels, // Dates sur l'axe des X
                datasets: [{
                    label: 'Accuracy (%)',
                    data: accuracyData, // Accuracy sur l'axe des Y
                    borderColor: 'rgba(102, 124, 62, 1)',
                    backgroundColor: 'rgba(153, 221, 64, 0.2)',
                    tension: 0.4, // Courbe légèrement lissée
                    fill: true,
                    pointBackgroundColor: 'rgb(0, 0, 0)', // Couleur des points
                    pointBorderColor: 'rgb(0, 0, 0)',
                    pointRadius: 5, // Taille des points
                    pointHoverRadius: 7 // Taille des points au survol
                }]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Accuracy (%)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    datalabels: {
                        anchor: 'end',
                        align: 'top',
                        formatter: (value) => value.toFixed(2) + '%',
                        color: '#000'
                    }
                }
            }
        });
    }

    // Graphique en barres (comparaison balles tirées vs détectées)
    const comparisonCtx = document.getElementById('comparisonChart');
    if (comparisonCtx) {
        if (comparisonChartInstance) comparisonChartInstance.destroy(); // Détruire l'instance précédente
        comparisonChartInstance = new Chart(comparisonCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Bullets Shot',
                        data: shotData,
                        backgroundColor: 'rgba(0, 0, 0, 0.7)'
                    },
                    {
                        label: 'Bullets Detected',
                        data: detectedData,
                        backgroundColor: 'rgb(102, 124, 62)'
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const sessionId = sessionData[index].id;
                        const detailButton = document.querySelector(`.session-details[data-id="${sessionId}"]`);
                        if (detailButton) detailButton.click();
                    }
                },
                plugins: {
                    datalabels: {
                        anchor: 'end',
                        align: 'top',
                        formatter: (value) => value,
                        color: '#000'
                    }
                }
            }
        });
    }

    // Initialiser le graphique circulaire
    const finalAvgAccuracy = Number.isFinite(avgAccuracy*100) ? avgAccuracy : 0;
    initializePieChart(finalAvgAccuracy);
}

// Initialisation des graphiques au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    let sessionData;
    try {
        sessionData = JSON.parse(document.getElementById('session-data').textContent);
    } catch (e) {
        console.error('Erreur lors du parsing des données de session:', e);
        sessionData = [];
    }

    let avgAccuracy;
    try {
        avgAccuracy = parseFloat(document.getElementById('avg-accuracy-data').textContent);
    } catch (e) {
        console.error('Erreur lors du parsing de avgAccuracy:', e);
        avgAccuracy = 0;
    }

    initializeCharts(sessionData, avgAccuracy);
});