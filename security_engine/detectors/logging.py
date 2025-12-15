"""
Security event logging utility for local file logging
Logs security events to JSONL files for later analysis
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from django.conf import settings


class SecurityLogger:
    """Logger for security events that writes to local JSONL files"""
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize security logger
        
        Args:
            log_dir: Directory for log files (default: LOGS/security/)
        """
        if log_dir is None:
            base_dir = getattr(settings, 'BASE_DIR', None)
            if base_dir:
                log_dir = os.path.join(base_dir, 'LOGS', 'security')
            else:
                log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LOGS', 'security')
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file paths
        self.login_attempts_file = self.log_dir / 'login_attempts.jsonl'
        self.security_events_file = self.log_dir / 'security_events.jsonl'
        self.failed_attempts_file = self.log_dir / 'failed_attempts.jsonl'
        self.rate_limit_file = self.log_dir / 'rate_limits.jsonl'
        
        # Setup Python logger for security events
        self._setup_python_logger()
    
    def _setup_python_logger(self):
        """Setup Python logging for security events"""
        self.logger = logging.getLogger('security.events')
        self.logger.setLevel(logging.INFO)
        
        # File handler for security events
        handler = logging.FileHandler(
            self.security_events_file,
            mode='a',
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def _write_jsonl(self, file_path: Path, data: Dict[str, Any]):
        """Write JSON data to a JSONL file"""
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            # Fallback to Python logger if file write fails
            self.logger.error(f"Failed to write to {file_path}: {str(e)}")
    
    def log_login_attempt(
        self,
        email: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
        user_id: Optional[int] = None,
        **kwargs
    ):
        """
        Log a login attempt with detailed information
        
        Args:
            email: Email address used in login attempt
            success: Whether login was successful
            ip_address: IP address of the request
            user_agent: User agent string
            reason: Reason for failure (if unsuccessful)
            user_id: User ID if login was successful
            **kwargs: Additional fields to log
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': 'LOGIN_ATTEMPT',
            'email': email,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'reason': reason,
            'user_id': user_id,
            **kwargs
        }
        
        # Write to login attempts file
        self._write_jsonl(self.login_attempts_file, log_data)
        
        # Write to failed attempts file if unsuccessful
        if not success:
            self._write_jsonl(self.failed_attempts_file, log_data)
            self.logger.warning(
                f"Failed login attempt: email={email}, ip={ip_address}, reason={reason}"
            )
        else:
            self.logger.info(
                f"Successful login: email={email}, ip={ip_address}, user_id={user_id}"
            )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str = 'MEDIUM',
        message: str = '',
        ip_address: Optional[str] = None,
        user_id: Optional[int] = None,
        path: Optional[str] = None,
        **kwargs
    ):
        """
        Log a general security event
        
        Args:
            event_type: Type of security event
            severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
            message: Event message
            ip_address: IP address of the request
            user_id: User ID if applicable
            path: Request path
            **kwargs: Additional fields to log
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': event_type,
            'severity': severity,
            'message': message,
            'ip_address': ip_address,
            'user_id': user_id,
            'path': path,
            **kwargs
        }
        
        # Write to security events file
        self._write_jsonl(self.security_events_file, log_data)
        
        # Log to Python logger based on severity
        if severity == 'CRITICAL':
            self.logger.critical(message)
        elif severity == 'HIGH':
            self.logger.error(message)
        elif severity == 'MEDIUM':
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def log_rate_limit(
        self,
        ip_address: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None,
        user_id: Optional[int] = None,
        user_agent: Optional[str] = None,
        throttle_key: Optional[str] = None,
        **kwargs
    ):
        """
        Log a rate limit violation event
        
        Args:
            ip_address: IP address of the request
            path: Request path that was rate limited
            method: HTTP method (GET, POST, etc.)
            user_id: User ID if authenticated
            user_agent: User agent string
            throttle_key: Throttle key used by DRF (for debugging)
            **kwargs: Additional fields to log
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': 'RATE_LIMIT',
            'severity': 'HIGH',
            'ip_address': ip_address,
            'path': path,
            'method': method,
            'user_id': user_id,
            'user_agent': user_agent,
            'throttle_key': throttle_key,
            'message': f'Rate limit exceeded for {method} {path} from {ip_address}',
            **kwargs
        }
        
        # Write to rate limit file
        self._write_jsonl(self.rate_limit_file, log_data)
        
        # Also write to general security events file
        self._write_jsonl(self.security_events_file, log_data)
        
        # Log to Python logger
        self.logger.warning(
            f"Rate limit exceeded: {method} {path} from {ip_address} (user_id={user_id})"
        )
    
    def get_failed_attempts_count(
        self,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        hours: int = 1
    ) -> int:
        """
        Count failed login attempts in the last N hours
        
        Args:
            email: Filter by email (optional)
            ip_address: Filter by IP address (optional)
            hours: Number of hours to look back
            
        Returns:
            Count of failed attempts
        """
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        if not self.failed_attempts_file.exists():
            return 0
        
        count = 0
        try:
            with open(self.failed_attempts_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                        
                        if timestamp < cutoff_time.replace(tzinfo=None):
                            continue
                        
                        if email and data.get('email') != email:
                            continue
                        
                        if ip_address and data.get('ip_address') != ip_address:
                            continue
                        
                        count += 1
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except FileNotFoundError:
            pass
        
        return count


# Global instance
_security_logger: Optional[SecurityLogger] = None


def get_security_logger() -> SecurityLogger:
    """Get or create the global security logger instance"""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger

