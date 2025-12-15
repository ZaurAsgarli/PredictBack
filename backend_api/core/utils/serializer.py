"""
Utility functions for standardized API responses
"""
from rest_framework.response import Response
from rest_framework import status


def success(data=None):
    """
    Return a standardized success response.
    
    Args:
        data: Optional data to include in the response
    
    Returns:
        Response: DRF Response with success format
    """
    return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


def error(message, status_code=400):
    """
    Return a standardized error response.
    
    Args:
        message: Error message string
        status_code: HTTP status code (default: 400)
    
    Returns:
        Response: DRF Response with error format
    """
    return Response({"success": False, "error": message}, status=status_code)

