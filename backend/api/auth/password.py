"""
Password Security — Hashing and Verification
Uses bcrypt with passlib for secure password handling
"""
from passlib.context import CryptContext
import structlog

log = structlog.get_logger()

# bcrypt hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    Args:
        password: Plaintext password
    
    Returns:
        Hashed password (safe to store in DB)
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a hash.
    
    Args:
        password: Plaintext password from user
        hashed: Hashed password from database
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(password, hashed)
    except Exception as e:
        log.warning("Password verification failed", error=str(e))
        return False
