import React, { useState, useEffect } from 'react';
import './Dashboard.css';

const API_ENDPOINT = 'http://localhost:3000/api/dashboard-logs';

function Dashboard() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const response = await fetch(API_ENDPOINT);
                
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                
                const data = await response.json();
                setLogs(data);
                setError(null);
            } catch (err) {
                console.error('Failed to fetch logs:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchLogs();
    }, []);

    // Calculate key metrics from logs
    const metrics = {
        totalLogs: logs.length,
        infoCount: logs.filter(log => log.level === 'INFO').length,
        warningCount: logs.filter(log => log.level === 'WARNING').length,
        alertCount: logs.filter(log => log.level === 'ALERT').length,
        uniqueSourceIPs: [...new Set(logs.map(log => log.source_ip))].length,
        uniqueDestIPs: [...new Set(logs.map(log => log.destination_ip))].length
    };

    if (loading) {
        return (
            <div className="dashboard">
                <div className="loading-container">
                    <div className="loading-spinner"></div>
                    <p className="loading-text">Loading...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="dashboard">
                <div className="error-container">
                    <h2>⚠️ Error</h2>
                    <p>{error}</p>
                    <p className="error-hint">Make sure the server is running on port 3000</p>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard">
            {/* Main Heading */}
            <header className="dashboard-header">
                <h1>SIEM Log Dashboard</h1>
                <p className="subtitle">Real-time Security Event Monitoring</p>
            </header>

            {/* Key Metrics Section */}
            <section className="dashboard-section">
                <h2 className="section-title">Key Metrics</h2>
                <div className="metrics-grid">
                    <div className="metric-card total">
                        <span className="metric-value">{metrics.totalLogs}</span>
                        <span className="metric-label">Total Logs</span>
                    </div>
                    <div className="metric-card info">
                        <span className="metric-value">{metrics.infoCount}</span>
                        <span className="metric-label">Info Events</span>
                    </div>
                    <div className="metric-card warning">
                        <span className="metric-value">{metrics.warningCount}</span>
                        <span className="metric-label">Warnings</span>
                    </div>
                    <div className="metric-card alert">
                        <span className="metric-value">{metrics.alertCount}</span>
                        <span className="metric-label">Alerts</span>
                    </div>
                    <div className="metric-card sources">
                        <span className="metric-value">{metrics.uniqueSourceIPs}</span>
                        <span className="metric-label">Unique Source IPs</span>
                    </div>
                    <div className="metric-card destinations">
                        <span className="metric-value">{metrics.uniqueDestIPs}</span>
                        <span className="metric-label">Unique Dest IPs</span>
                    </div>
                </div>
            </section>

            {/* Threat Charts Section */}
            <section className="dashboard-section">
                <h2 className="section-title">Threat Charts</h2>
                <div className="charts-grid">
                    <div className="chart-card">
                        <h3>Log Level Distribution</h3>
                        <div className="chart-placeholder">
                            <div className="bar-chart">
                                <div className="bar info-bar" style={{ height: `${(metrics.infoCount / metrics.totalLogs) * 100}%` }}>
                                    <span className="bar-label">INFO</span>
                                </div>
                                <div className="bar warning-bar" style={{ height: `${(metrics.warningCount / metrics.totalLogs) * 100}%` }}>
                                    <span className="bar-label">WARN</span>
                                </div>
                                <div className="bar alert-bar" style={{ height: `${(metrics.alertCount / metrics.totalLogs) * 100}%` }}>
                                    <span className="bar-label">ALERT</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="chart-card">
                        <h3>Recent Activity Timeline</h3>
                        <div className="timeline-container">
                            {logs.slice(-5).reverse().map((log, index) => (
                                <div key={index} className={`timeline-item ${log.level?.toLowerCase()}`}>
                                    <span className="timeline-time">
                                        {new Date(log.timestamp).toLocaleTimeString()}
                                    </span>
                                    <span className={`timeline-level level-${log.level?.toLowerCase()}`}>
                                        {log.level}
                                    </span>
                                    <span className="timeline-message">
                                        {log.message?.substring(0, 60)}...
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}

export default Dashboard;

