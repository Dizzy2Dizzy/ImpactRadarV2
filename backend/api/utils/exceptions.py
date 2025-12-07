"""Custom exception classes for Impact Radar API"""
from fastapi import HTTPException, status


class ReleaseRadarException(HTTPException):
    """Base exception with error_code support"""
    
    def __init__(self, error_code: str, message: str, status_code: int, details=None):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code
        self.details = details


class QuotaExceededException(ReleaseRadarException):
    """Exception for when API quota is exceeded"""
    
    def __init__(self, details=None):
        super().__init__(
            error_code="QUOTA_EXCEEDED",
            message="API quota exceeded. Upgrade your plan for higher limits.",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details=details
        )


class UpgradeRequiredException(ReleaseRadarException):
    """Exception for when a feature requires a higher plan"""
    
    def __init__(self, feature: str, required_plan: str):
        super().__init__(
            error_code="UPGRADE_REQUIRED",
            message=f"{feature} requires {required_plan} plan or higher.",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details={"feature": feature, "required_plan": required_plan}
        )


class ResourceNotFoundException(ReleaseRadarException):
    """Exception for when a resource is not found"""
    
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(
            error_code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )


class InvalidInputException(ReleaseRadarException):
    """Exception for invalid input data"""
    
    def __init__(self, message: str, details=None):
        super().__init__(
            error_code="INVALID_INPUT",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class UnauthorizedException(ReleaseRadarException):
    """Exception for unauthorized access"""
    
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(
            error_code="UNAUTHORIZED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
