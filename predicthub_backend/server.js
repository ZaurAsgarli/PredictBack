const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;
const LOG_STORAGE_FILE = path.join(__dirname, 'log_storage.json');

// Middleware
app.use(express.json());

// CORS configuration for React dashboard (ports 5173 and 3000)
app.use(cors({
    origin: [
        'http://localhost:5173',
        'http://localhost:3000',
        'http://127.0.0.1:5173',
        'http://127.0.0.1:3000'
    ],
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type']
}));

/**
 * Helper function to read logs from storage file
 */
function readLogsFromFile() {
    try {
        if (!fs.existsSync(LOG_STORAGE_FILE)) {
            fs.writeFileSync(LOG_STORAGE_FILE, '[]', 'utf8');
            return [];
        }
        const data = fs.readFileSync(LOG_STORAGE_FILE, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error('Error reading log storage file:', error.message);
        return [];
    }
}

/**
 * Helper function to write logs to storage file
 */
function writeLogsToFile(logs) {
    try {
        fs.writeFileSync(LOG_STORAGE_FILE, JSON.stringify(logs, null, 2), 'utf8');
        return true;
    } catch (error) {
        console.error('Error writing to log storage file:', error.message);
        return false;
    }
}

/**
 * POST /api/ingest-log
 * Accepts a JSON log object, validates timestamp, appends to log_storage.json
 */
app.post('/api/ingest-log', (req, res) => {
    const logEntry = req.body;

    // Validate that request body exists
    if (!logEntry || typeof logEntry !== 'object') {
        return res.status(400).json({
            success: false,
            error: 'Request body must be a valid JSON object'
        });
    }

    // Validate required timestamp field
    if (!logEntry.timestamp) {
        return res.status(400).json({
            success: false,
            error: 'Missing required field: timestamp'
        });
    }

    // Read existing logs
    const logs = readLogsFromFile();

    // Add received timestamp for tracking when log was ingested
    logEntry.ingested_at = new Date().toISOString();

    // Append new log entry
    logs.push(logEntry);

    // Write back to file
    if (writeLogsToFile(logs)) {
        console.log(`[${new Date().toISOString()}] Log ingested: ${logEntry.level || 'N/A'} - ${logEntry.message?.substring(0, 50) || 'No message'}...`);
        return res.status(201).json({
            success: true,
            message: 'Log entry ingested successfully',
            total_logs: logs.length
        });
    } else {
        return res.status(500).json({
            success: false,
            error: 'Failed to save log entry to storage'
        });
    }
});

/**
 * GET /api/dashboard-logs
 * Returns all log entries from log_storage.json as a JSON array
 */
app.get('/api/dashboard-logs', (req, res) => {
    const logs = readLogsFromFile();
    
    console.log(`[${new Date().toISOString()}] Dashboard requested ${logs.length} logs`);
    
    return res.status(200).json(logs);
});

/**
 * Health check endpoint
 */
app.get('/api/health', (req, res) => {
    res.status(200).json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        log_count: readLogsFromFile().length
    });
});

// Start server
app.listen(PORT, () => {
    console.log('='.repeat(50));
    console.log(`Log Ingestion Server running on http://localhost:${PORT}`);
    console.log('='.repeat(50));
    console.log('Endpoints:');
    console.log(`  POST /api/ingest-log     - Ingest a log entry`);
    console.log(`  GET  /api/dashboard-logs - Retrieve all logs`);
    console.log(`  GET  /api/health         - Health check`);
    console.log('='.repeat(50));
    console.log(`CORS enabled for: localhost:5173, localhost:3000`);
    console.log(`Log storage: ${LOG_STORAGE_FILE}`);
    console.log('='.repeat(50));
});

