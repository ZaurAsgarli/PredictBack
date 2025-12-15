"""
Custom middleware for logging and error handling
"""
import logging
import traceback
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class LoggingMiddleware(MiddlewareMixin):
    """Middleware to log all requests"""
    
    def process_request(self, request):
        logger.info(
            f"{request.method} {request.path} - User: {getattr(request.user, 'username', 'Anonymous')}"
        )
        return None


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Middleware to handle and log errors"""
    
    def process_exception(self, request, exception):
        logger.error(
            f"Exception in {request.path}: {str(exception)}\n{traceback.format_exc()}"
        )
        
        # Return JSON error response for API requests
        if request.path.startswith('/api/') or request.path.startswith('/auth/') or request.path.startswith('/markets/'):
            return JsonResponse(
                {
                    'error': 'Internal server error',
                    'detail': str(exception) if hasattr(exception, '__str__') else 'Unknown error'
                },
                status=500
            )
        return None


class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log security events (429 Rate Limit, 401 Unauthorized)
    to the SecurityLogs database table.
    """
    
    def process_response(self, request, response):
        # Only log security events for API endpoints
        if not request.path.startswith('/api/'):
            return response
        
        # Get client IP address
        ip = self._get_client_ip(request)
        
        # Log rate limit violations (429)
        if response.status_code == 429:
            try:
                from security_engine.models import SecurityLog
                from security_engine.detectors.logging import get_security_logger
                
                user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # Log to database
                SecurityLog.objects.create(
                    ip=ip,
                    event_type='RATE_LIMIT',
                    severity='HIGH',
                    message=f'Rate limit exceeded for {request.method} {request.path}',
                    path=request.path,
                    user=user,
                    user_agent=user_agent,
                    metadata={
                        'method': request.method,
                        'throttle_key': getattr(request, 'throttle_key', None)
                    }
                )
                
                # Also log to local files
                security_logger = get_security_logger()
                security_logger.log_rate_limit(
                    ip_address=ip,
                    path=request.path,
                    method=request.method,
                    user_id=user.id if user else None,
                    user_agent=user_agent,
                    throttle_key=getattr(request, 'throttle_key', None)
                )
            except Exception as e:
                logger.error(f"Failed to log security event: {e}")
        
        # Log failed login attempts (401)
        elif response.status_code == 401 and 'login' in request.path.lower():
            try:
                from security_engine.models import SecurityLog
                SecurityLog.objects.create(
                    ip=ip,
                    event_type='FAILED_LOGIN',
                    severity='MEDIUM',
                    message=f'Failed login attempt from {ip}',
                    path=request.path,
                    user=None  # User is not authenticated on failed login
                )
            except Exception as e:
                logger.error(f"Failed to log security event: {e}")
        
        return response
    
    def _get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
