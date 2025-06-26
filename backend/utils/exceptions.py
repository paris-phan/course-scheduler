from typing import Any, Optional, Dict
from fastapi import HTTPException, status


class CourseSchedulerException(Exception):
    """Base exception class for Course Scheduler application"""
    pass


class DatabaseException(CourseSchedulerException):
    """Exception raised for database-related errors"""
    pass


class SISAPIException(CourseSchedulerException):
    """Exception raised when SIS API calls fail"""
    pass


class ValidationException(CourseSchedulerException):
    """Exception raised for validation errors"""
    pass


class ResourceNotFoundException(HTTPException):
    """Exception raised when a requested resource is not found"""
    
    def __init__(self, resource: str, identifier: Any):
        detail = f"{resource} with identifier '{identifier}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestException(HTTPException):
    """Exception raised for bad requests"""
    
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ConflictException(HTTPException):
    """Exception raised for resource conflicts"""
    
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnauthorizedException(HTTPException):
    """Exception raised for unauthorized access"""
    
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenException(HTTPException):
    """Exception raised for forbidden access"""
    
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)