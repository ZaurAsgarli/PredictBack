import React, { useMemo } from 'react';
import './KeyMetrics.css';

function KeyMetrics({ logs = [] }) {
    // Calculate metrics with memoization for performance
    const metrics = useMemo(() => {
        const totalAlerts = logs.filter(log => log.level === 'ALERT').length;
        const uniqueSourceIPs = new Set(logs.map(log => log.source_ip).filter(Boolean));
        const uniqueDestIPs = new Set(logs.map(log => log.destination_ip).filter(Boolean));

        return {
            totalAlerts,
            uniqueSourceIPs: uniqueSourceIPs.size,
            uniqueDestIPs: uniqueDestIPs.size
        };
    }, [logs]);

    return (
        <div className="key-metrics">
            <div className="key-metrics-header">
                <h2>Key Metrics</h2>
                <span className="metrics-badge">{logs.length} logs analyzed</span>
            </div>
            
            <div className="metrics-cards">
                {/* Total Alerts Card */}
                <div className="metric-card alerts-card">
                    <div className="metric-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                            <line x1="12" y1="9" x2="12" y2="13"/>
                            <line x1="12" y1="17" x2="12.01" y2="17"/>
                        </svg>
                    </div>
                    <div className="metric-content">
                        <span className="metric-value">{metrics.totalAlerts}</span>
                        <span className="metric-label">Total Alerts</span>
                    </div>
                    <div className="metric-indicator alert-indicator"></div>
                </div>

                {/* Unique Source IPs Card */}
                <div className="metric-card source-card">
                    <div className="metric-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="2" y1="12" x2="22" y2="12"/>
                            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                        </svg>
                    </div>
                    <div className="metric-content">
                        <span className="metric-value">{metrics.uniqueSourceIPs}</span>
                        <span className="metric-label">Unique Source IPs</span>
                    </div>
                    <div className="metric-indicator source-indicator"></div>
                </div>

                {/* Unique Destination IPs Card */}
                <div className="metric-card dest-card">
                    <div className="metric-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                            <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                            <line x1="12" y1="22.08" x2="12" y2="12"/>
                        </svg>
                    </div>
                    <div className="metric-content">
                        <span className="metric-value">{metrics.uniqueDestIPs}</span>
                        <span className="metric-label">Unique Dest IPs</span>
                    </div>
                    <div className="metric-indicator dest-indicator"></div>
                </div>
            </div>
        </div>
    );
}

export default KeyMetrics;

