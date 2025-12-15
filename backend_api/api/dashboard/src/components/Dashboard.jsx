import React, { useState, useEffect } from 'react';
import './Dashboard.css';

const API_ENDPOINT = 'http://localhost:8000/api/admin/security-logs/';

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
        rateLimitCount: logs.filter(log => log.event_type === 'RATE_LIMIT').length,
        failedLoginCount: logs.filter(log => log.event_type === 'FAILED_LOGIN').length,
        highSeverityCount: logs.filter(log => log.severity === 'HIGH' || log.severity === 'CRITICAL').length,
        uniqueIPs: [...new Set(logs.map(log => log.ip).filter(ip => ip))].length,
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
                    <div className="metric-card warning">
                        <span className="metric-value">{metrics.rateLimitCount}</span>
                        <span className="metric-label">Rate Limit Violations</span>
                    </div>
                    <div className="metric-card alert">
                        <span className="metric-value">{metrics.failedLoginCount}</span>
                        <span className="metric-label">Failed Logins</span>
                    </div>
                    <div className="metric-card alert">
                        <span className="metric-value">{metrics.highSeverityCount}</span>
                        <span className="metric-label">High Severity Events</span>
                    </div>
                    <div className="metric-card sources">
                        <span className="metric-value">{metrics.uniqueIPs}</span>
                        <span className="metric-label">Unique IP Addresses</span>
                    </div>
                </div>
            </section>

            {/* Threat Charts Section */}
            <section className="dashboard-section">
                <h2 className="section-title">Threat Charts</h2>
                <div className="charts-grid">
                    <div className="chart-card">
                        <h3>Event Type Distribution</h3>
                        <div className="chart-placeholder">
                            <div className="bar-chart">
                                <div className="bar warning-bar" style={{ height: `${metrics.totalLogs > 0 ? (metrics.rateLimitCount / metrics.totalLogs) * 100 : 0}%` }}>
                                    <span className="bar-label">RATE_LIMIT</span>
                                </div>
                                <div className="bar alert-bar" style={{ height: `${metrics.totalLogs > 0 ? (metrics.failedLoginCount / metrics.totalLogs) * 100 : 0}%` }}>
                                    <span className="bar-label">FAILED_LOGIN</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="chart-card">
                        <h3>Recent Activity Timeline</h3>
                        <div className="timeline-container">
                            {logs.slice(-5).reverse().map((log, index) => (
                                <div key={log.id || index} className={`timeline-item ${log.severity?.toLowerCase()}`}>
                                    <span className="timeline-time">
                                        {new Date(log.timestamp).toLocaleTimeString()}
                                    </span>
                                    <span className={`timeline-level level-${log.severity?.toLowerCase()}`}>
                                        {log.event_type}
                                    </span>
                                    <span className="timeline-message">
                                        {log.message?.substring(0, 60) || 'No message'}...
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

