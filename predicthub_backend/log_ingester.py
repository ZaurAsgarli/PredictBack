#!/usr/bin/env python3
"""
Log Ingester Script

Reads project.log line-by-line, parses JSON log entries, and sends them
to an API endpoint with rate limiting and error handling.

Expected log format (JSON per line):
{
    "timestamp": "...",
    "level": "...",
    "source_ip": "...",
    "destination_ip": "...",
    "message": "..."
}
"""

import json
import time
import sys
from pathlib import Path

import requests
from requests.exceptions import ConnectionError, Timeout, RequestException


# Configuration
LOG_FILE = "project.log"
API_ENDPOINT = "http://localhost:3000/api/ingest-log"
REQUEST_DELAY_SECONDS = 1
REQUEST_TIMEOUT_SECONDS = 10


def parse_log_line(line: str, line_number: int) -> dict | None:
    """
    Parse a single log line as JSON.
    
    Returns the parsed dict or None if parsing fails.
    """
    line = line.strip()
    if not line:
        return None
    
    try:
        data = json.loads(line)
        
        # Validate required fields
        required_fields = ["timestamp", "level", "source_ip", "destination_ip", "message"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print(f"[WARNING] Line {line_number}: Missing required fields: {missing_fields}")
            return None
        
        return data
    
    except json.JSONDecodeError as e:
        print(f"[ERROR] Line {line_number}: Invalid JSON - {e}")
        return None


def send_log_entry(log_entry: dict, line_number: int) -> bool:
    """
    Send a log entry to the API endpoint.
    
    Returns True on success, False on failure.
    """
    try:
        response = requests.post(
            API_ENDPOINT,
            json=log_entry,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        
        if response.status_code >= 200 and response.status_code < 300:
            print(f"[SUCCESS] Line {line_number}: Sent successfully (HTTP {response.status_code})")
            return True
        else:
            print(f"[ERROR] Line {line_number}: API returned HTTP {response.status_code}")
            try:
                error_body = response.text[:200]  # Truncate long error messages
                print(f"         Response: {error_body}")
            except Exception:
                pass
            return False
    
    except ConnectionError:
        print(f"[ERROR] Line {line_number}: Connection failed - Is the server running at {API_ENDPOINT}?")
        return False
    
    except Timeout:
        print(f"[ERROR] Line {line_number}: Request timed out after {REQUEST_TIMEOUT_SECONDS}s")
        return False
    
    except RequestException as e:
        print(f"[ERROR] Line {line_number}: Request failed - {e}")
        return False


def ingest_logs(log_file_path: str) -> None:
    """
    Main function to read and ingest log entries from a file.
    """
    log_path = Path(log_file_path)
    
    # Check if file exists
    if not log_path.exists():
        print(f"[FATAL] Log file not found: {log_path.absolute()}")
        sys.exit(1)
    
    if not log_path.is_file():
        print(f"[FATAL] Path is not a file: {log_path.absolute()}")
        sys.exit(1)
    
    print(f"[INFO] Starting log ingestion from: {log_path.absolute()}")
    print(f"[INFO] API endpoint: {API_ENDPOINT}")
    print(f"[INFO] Delay between requests: {REQUEST_DELAY_SECONDS}s")
    print("-" * 60)
    
    # Statistics
    total_lines = 0
    successful_sends = 0
    failed_sends = 0
    skipped_lines = 0
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                total_lines += 1
                
                # Parse the log line
                log_entry = parse_log_line(line, line_number)
                
                if log_entry is None:
                    skipped_lines += 1
                    continue
                
                # Send to API
                if send_log_entry(log_entry, line_number):
                    successful_sends += 1
                else:
                    failed_sends += 1
                
                # Rate limiting - delay before next request
                time.sleep(REQUEST_DELAY_SECONDS)
    
    except KeyboardInterrupt:
        print("\n[INFO] Ingestion interrupted by user")
    
    except PermissionError:
        print(f"[FATAL] Permission denied reading file: {log_path}")
        sys.exit(1)
    
    except Exception as e:
        print(f"[FATAL] Unexpected error: {e}")
        sys.exit(1)
    
    # Print summary
    print("-" * 60)
    print("[INFO] Ingestion complete!")
    print(f"       Total lines processed: {total_lines}")
    print(f"       Successfully sent:     {successful_sends}")
    print(f"       Failed to send:        {failed_sends}")
    print(f"       Skipped (invalid):     {skipped_lines}")


if __name__ == "__main__":
    # Allow optional command-line argument for log file path
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        log_file = LOG_FILE
    
    ingest_logs(log_file)

