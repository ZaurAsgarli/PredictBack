import React, { useMemo } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend
} from 'chart.js';
import { Bar, Pie } from 'react-chartjs-2';
import './ThreatCharts.css';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend
);

function ThreatCharts({ logs = [] }) {
    // Calculate data for Bar Chart (events by level)
    const barChartData = useMemo(() => {
        const levelCounts = {
            INFO: 0,
            WARNING: 0,
            ALERT: 0
        };

        logs.forEach(log => {
            if (log.level && levelCounts.hasOwnProperty(log.level)) {
                levelCounts[log.level]++;
            }
        });

        return {
            labels: ['INFO', 'WARNING', 'ALERT'],
            datasets: [
                {
                    label: 'Event Count',
                    data: [levelCounts.INFO, levelCounts.WARNING, levelCounts.ALERT],
                    backgroundColor: [
                        'rgba(63, 185, 80, 0.8)',   // Green for INFO
                        'rgba(210, 153, 34, 0.8)',  // Yellow for WARNING
                        'rgba(248, 81, 73, 0.8)'   // Red for ALERT
                    ],
                    borderColor: [
                        'rgba(63, 185, 80, 1)',
                        'rgba(210, 153, 34, 1)',
                        'rgba(248, 81, 73, 1)'
                    ],
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }
            ]
        };
    }, [logs]);

    // Calculate data for Pie Chart (Top 5 Source IPs)
    const pieChartData = useMemo(() => {
        // Count occurrences of each source IP
        const ipCounts = {};
        logs.forEach(log => {
            if (log.source_ip) {
                ipCounts[log.source_ip] = (ipCounts[log.source_ip] || 0) + 1;
            }
        });

        // Sort by count and get top 5
        const sortedIPs = Object.entries(ipCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);

        const labels = sortedIPs.map(([ip]) => ip);
        const data = sortedIPs.map(([, count]) => count);

        // Color palette for pie slices
        const colors = [
            'rgba(0, 217, 255, 0.85)',    // Cyan
            'rgba(163, 113, 247, 0.85)',  // Purple
            'rgba(255, 123, 114, 0.85)',  // Coral
            'rgba(88, 166, 255, 0.85)',   // Blue
            'rgba(238, 190, 95, 0.85)'    // Gold
        ];

        const borderColors = [
            'rgba(0, 217, 255, 1)',
            'rgba(163, 113, 247, 1)',
            'rgba(255, 123, 114, 1)',
            'rgba(88, 166, 255, 1)',
            'rgba(238, 190, 95, 1)'
        ];

        return {
            labels,
            datasets: [
                {
                    label: 'Events',
                    data,
                    backgroundColor: colors.slice(0, data.length),
                    borderColor: borderColors.slice(0, data.length),
                    borderWidth: 2,
                    hoverOffset: 8
                }
            ]
        };
    }, [logs]);

    // Bar Chart options
    const barOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            title: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(22, 29, 38, 0.95)',
                titleColor: '#e6edf3',
                bodyColor: '#8b949e',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                cornerRadius: 8,
                padding: 12,
                titleFont: {
                    family: "'Outfit', sans-serif",
                    size: 14,
                    weight: '600'
                },
                bodyFont: {
                    family: "'JetBrains Mono', monospace",
                    size: 13
                }
            }
        },
        scales: {
            x: {
                grid: {
                    display: false
                },
                ticks: {
                    color: '#8b949e',
                    font: {
                        family: "'Outfit', sans-serif",
                        size: 12,
                        weight: '500'
                    }
                }
            },
            y: {
                beginAtZero: true,
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)'
                },
                ticks: {
                    color: '#6e7681',
                    font: {
                        family: "'JetBrains Mono', monospace",
                        size: 11
                    },
                    stepSize: 1
                }
            }
        }
    };

    // Pie Chart options
    const pieOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                labels: {
                    color: '#8b949e',
                    font: {
                        family: "'JetBrains Mono', monospace",
                        size: 11
                    },
                    padding: 16,
                    usePointStyle: true,
                    pointStyle: 'circle'
                }
            },
            title: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(22, 29, 38, 0.95)',
                titleColor: '#e6edf3',
                bodyColor: '#8b949e',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                cornerRadius: 8,
                padding: 12,
                titleFont: {
                    family: "'JetBrains Mono', monospace",
                    size: 12
                },
                bodyFont: {
                    family: "'JetBrains Mono', monospace",
                    size: 13
                },
                callbacks: {
                    label: function(context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((context.parsed / total) * 100).toFixed(1);
                        return ` ${context.parsed} events (${percentage}%)`;
                    }
                }
            }
        }
    };

    return (
        <div className="threat-charts">
            <div className="threat-charts-header">
                <h2>Threat Charts</h2>
            </div>

            <div className="charts-container">
                {/* Bar Chart - Events by Level */}
                <div className="chart-card">
                    <h3>Events by Severity Level</h3>
                    <div className="chart-wrapper">
                        <Bar data={barChartData} options={barOptions} />
                    </div>
                    <div className="chart-legend-custom">
                        <span className="legend-item">
                            <span className="legend-dot info"></span>
                            INFO: {barChartData.datasets[0].data[0]}
                        </span>
                        <span className="legend-item">
                            <span className="legend-dot warning"></span>
                            WARNING: {barChartData.datasets[0].data[1]}
                        </span>
                        <span className="legend-item">
                            <span className="legend-dot alert"></span>
                            ALERT: {barChartData.datasets[0].data[2]}
                        </span>
                    </div>
                </div>

                {/* Pie Chart - Top 5 Source IPs */}
                <div className="chart-card">
                    <h3>Top 5 Source IPs</h3>
                    <div className="chart-wrapper pie-wrapper">
                        {pieChartData.labels.length > 0 ? (
                            <Pie data={pieChartData} options={pieOptions} />
                        ) : (
                            <div className="no-data">No source IP data available</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ThreatCharts;

