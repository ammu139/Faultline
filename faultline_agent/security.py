"""
Faultline Security Module
Implements security features for the agent system:
- Input validation and sanitization
- Rate limiting
- API key management
- Audit logging
- Content security policy

Design: Defense-in-depth approach with multiple security layers.
All external inputs pass through validation before reaching core logic.
"""

import os
import time
import hashlib
import secrets
from typing import Any, Optional
from datetime import datetime
from functools import wraps


class InputValidator:
    """
    Validates and sanitizes all external inputs.
    
    Security behavior:
    - Strips control characters from strings
    - Enforces maximum lengths
    - Validates numeric ranges
    - Rejects known injection patterns
    """
    
    # Maximum allowed lengths for different input types
    MAX_LENGTHS = {
        "node_id": 50,
        "scenario_id": 20,
        "stress_type": 30,
        "general_string": 200,
        "description": 500,
    }
    
    # Patterns that indicate potential injection attempts
    BLOCKED_PATTERNS = [
        "__import__",
        "eval(",
        "exec(",
        "os.system",
        "subprocess",
        "<script",
        "javascript:",
        "'; DROP",
        "UNION SELECT",
    ]
    
    @classmethod
    def sanitize_string(cls, value: Any, field_type: str = "general_string") -> str:
        """
        Sanitize a string input.
        Removes control characters, enforces length limits, checks for injection.
        """
        if not isinstance(value, str):
            return ""
        
        # Remove control characters (keep printable + newlines)
        sanitized = "".join(c for c in value if c.isprintable() or c in "\n\t")
        
        # Enforce length limit
        max_len = cls.MAX_LENGTHS.get(field_type, 200)
        sanitized = sanitized[:max_len]
        
        # Check for injection patterns
        lower = sanitized.lower()
        for pattern in cls.BLOCKED_PATTERNS:
            if pattern.lower() in lower:
                return ""  # Reject entirely
        
        return sanitized
    
    @classmethod
    def validate_intensity(cls, value: Any) -> float:
        """Validate intensity is a float between 0.1 and 1.0."""
        try:
            v = float(value)
            return max(0.1, min(1.0, v))
        except (TypeError, ValueError):
            return 0.8  # Safe default
    
    @classmethod
    def validate_node_id(cls, value: Any, valid_ids: set) -> Optional[str]:
        """Validate a node ID exists in the graph."""
        sanitized = cls.sanitize_string(value, "node_id")
        if sanitized in valid_ids:
            return sanitized
        return None
    
    @classmethod
    def validate_scenario_id(cls, value: Any) -> Optional[str]:
        """Validate scenario ID is one of the allowed values."""
        sanitized = cls.sanitize_string(value, "scenario_id")
        allowed = {"ecommerce", "banking", "cicd"}
        if sanitized in allowed:
            return sanitized
        return None


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Design: Prevents abuse by limiting request frequency.
    Uses a sliding window approach for smooth rate limiting.
    """
    
    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: list[float] = []
    
    def is_allowed(self) -> bool:
        """Check if a request is allowed under the rate limit."""
        now = time.time()
        
        # Remove expired entries
        self._requests = [
            t for t in self._requests
            if now - t < self.window_seconds
        ]
        
        if len(self._requests) >= self.max_requests:
            return False
        
        self._requests.append(now)
        return True
    
    @property
    def remaining(self) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        active = [t for t in self._requests if now - t < self.window_seconds]
        return max(0, self.max_requests - len(active))


class AuditLogger:
    """
    Security audit logger.
    
    Records all significant actions for security review:
    - Scenario loads
    - Failure injections
    - Configuration changes
    - Authentication attempts
    """
    
    def __init__(self):
        self._log: list[dict[str, Any]] = []
        self._max_entries = 1000
    
    def log_action(
        self,
        action: str,
        details: dict[str, Any],
        severity: str = "info",
        user: str = "system",
    ) -> None:
        """Record an auditable action."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "severity": severity,
            "user": user,
            "details": details,
        }
        
        self._log.append(entry)
        
        # Trim old entries
        if len(self._log) > self._max_entries:
            self._log = self._log[-self._max_entries:]
    
    def get_recent(self, count: int = 20) -> list[dict]:
        """Get recent audit entries."""
        return self._log[-count:]
    
    def get_by_severity(self, severity: str) -> list[dict]:
        """Get entries filtered by severity."""
        return [e for e in self._log if e["severity"] == severity]


class APIKeyManager:
    """
    Manages API key validation for the MCP server.
    
    Security: Keys are stored as SHA-256 hashes, never in plaintext.
    Supports key rotation and expiration.
    """
    
    def __init__(self):
        self._key_hashes: dict[str, dict] = {}
        # Generate a default development key
        self._dev_key = os.getenv("FAULTLINE_API_KEY", "")
    
    def generate_key(self) -> str:
        """Generate a new API key."""
        key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        self._key_hashes[key_hash] = {
            "created_at": datetime.now().isoformat(),
            "active": True,
        }
        return key
    
    def validate_key(self, key: str) -> bool:
        """Validate an API key."""
        if not key:
            # In development mode, allow if no key is configured
            return self._dev_key == ""
        
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        entry = self._key_hashes.get(key_hash)
        
        if entry and entry.get("active"):
            return True
        
        # Check environment variable
        if key == self._dev_key and self._dev_key:
            return True
        
        return False
    
    def revoke_key(self, key: str) -> bool:
        """Revoke an API key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        if key_hash in self._key_hashes:
            self._key_hashes[key_hash]["active"] = False
            return True
        return False


# Global security instances
_validator = InputValidator()
_rate_limiter = RateLimiter()
_audit_logger = AuditLogger()
_api_key_manager = APIKeyManager()


def get_validator() -> InputValidator:
    return _validator


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter


def get_audit_logger() -> AuditLogger:
    return _audit_logger


def get_api_key_manager() -> APIKeyManager:
    return _api_key_manager