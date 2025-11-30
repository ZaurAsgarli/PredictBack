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

