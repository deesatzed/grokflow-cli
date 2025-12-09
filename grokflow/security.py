"""
GrokFlow Security Module

Security utilities and hardening:
- API key encryption
- Input sanitization
- Security auditing
- Secure defaults
- Vulnerability detection
- Secret management

Features:
- Encrypted storage
- Secure key handling
- Audit logging
- Security scanning
- Best practices enforcement
"""

import os
import re
import hashlib
import secrets
import base64
from typing import Optional, Dict, List, Any, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from grokflow.logging_config import get_logger
from grokflow.exceptions import GrokFlowError

logger = get_logger('grokflow.security')


class SecurityLevel(Enum):
    """Security severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityError(GrokFlowError):
    """Security-related errors"""
    pass


@dataclass
class SecurityIssue:
    """Security issue detected"""
    level: SecurityLevel
    category: str
    description: str
    location: str
    recommendation: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'level': self.level.value,
            'category': self.category,
            'description': self.description,
            'location': self.location,
            'recommendation': self.recommendation,
            'timestamp': self.timestamp
        }


class SecretManager:
    """
    Secure secret management
    
    Features:
    - Encrypted storage
    - Environment variable fallback
    - Secure key derivation
    - Audit logging
    
    Example:
        >>> sm = SecretManager()
        >>> sm.set_secret('api_key', 'secret_value')
        >>> value = sm.get_secret('api_key')
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize secret manager
        
        Args:
            storage_path: Path to encrypted storage
        """
        self.storage_path = storage_path or Path.home() / '.grokflow' / '.secrets'
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Simple XOR encryption key (derived from system)
        self._key = self._derive_key()
        
        logger.info("SecretManager initialized")
    
    def _derive_key(self) -> bytes:
        """Derive encryption key from system"""
        # Use machine-specific data for key derivation
        # In production, use proper key derivation (e.g., PBKDF2)
        machine_id = os.environ.get('USER', 'default')
        return hashlib.sha256(machine_id.encode()).digest()
    
    def _encrypt(self, data: str) -> str:
        """
        Simple XOR encryption
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data (base64)
        """
        data_bytes = data.encode('utf-8')
        encrypted = bytearray()
        
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ self._key[i % len(self._key)])
        
        return base64.b64encode(bytes(encrypted)).decode('utf-8')
    
    def _decrypt(self, encrypted_data: str) -> str:
        """
        Simple XOR decryption
        
        Args:
            encrypted_data: Encrypted data (base64)
            
        Returns:
            Decrypted data
        """
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted = bytearray()
        
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ self._key[i % len(self._key)])
        
        return bytes(decrypted).decode('utf-8')
    
    def set_secret(self, name: str, value: str) -> None:
        """
        Store secret securely
        
        Args:
            name: Secret name
            value: Secret value
        """
        # Load existing secrets
        secrets_dict = {}
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            secrets_dict[k] = v
            except Exception as e:
                logger.error(f"Failed to load secrets: {e}")
        
        # Encrypt and store
        encrypted = self._encrypt(value)
        secrets_dict[name] = encrypted
        
        # Write back
        try:
            with open(self.storage_path, 'w') as f:
                for k, v in secrets_dict.items():
                    f.write(f"{k}={v}\n")
            
            # Set restrictive permissions (owner only)
            os.chmod(self.storage_path, 0o600)
            
            logger.info(f"Secret stored: {name}")
        except Exception as e:
            logger.error(f"Failed to store secret: {e}")
            raise SecurityError(f"Failed to store secret: {e}") from e
    
    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve secret
        
        Args:
            name: Secret name
            default: Default value if not found
            
        Returns:
            Secret value or default
        """
        # Try environment variable first
        env_value = os.environ.get(name.upper())
        if env_value:
            return env_value
        
        # Try encrypted storage
        if not self.storage_path.exists():
            return default
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        if k == name:
                            return self._decrypt(v)
        except Exception as e:
            logger.error(f"Failed to retrieve secret: {e}")
        
        return default
    
    def delete_secret(self, name: str) -> bool:
        """
        Delete secret
        
        Args:
            name: Secret name
            
        Returns:
            True if deleted, False if not found
        """
        if not self.storage_path.exists():
            return False
        
        secrets_dict = {}
        found = False
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        if k != name:
                            secrets_dict[k] = v
                        else:
                            found = True
            
            if found:
                with open(self.storage_path, 'w') as f:
                    for k, v in secrets_dict.items():
                        f.write(f"{k}={v}\n")
                
                logger.info(f"Secret deleted: {name}")
            
            return found
        except Exception as e:
            logger.error(f"Failed to delete secret: {e}")
            return False


class InputSanitizer:
    """
    Advanced input sanitization
    
    Features:
    - SQL injection prevention
    - XSS prevention
    - Command injection prevention
    - Path traversal prevention
    - Unicode normalization
    
    Example:
        >>> sanitizer = InputSanitizer()
        >>> safe_input = sanitizer.sanitize(user_input)
    """
    
    # Dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()]",
        r"(\.\./|\.\.\\)",
        r"(\beval\b|\bexec\b)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
    ]
    
    def __init__(self):
        """Initialize input sanitizer"""
        self.sql_regex = re.compile('|'.join(self.SQL_INJECTION_PATTERNS), re.IGNORECASE)
        self.cmd_regex = re.compile('|'.join(self.COMMAND_INJECTION_PATTERNS), re.IGNORECASE)
        self.xss_regex = re.compile('|'.join(self.XSS_PATTERNS), re.IGNORECASE)
        
        logger.debug("InputSanitizer initialized")
    
    def detect_sql_injection(self, text: str) -> bool:
        """
        Detect SQL injection attempts
        
        Args:
            text: Text to check
            
        Returns:
            True if SQL injection detected
        """
        return bool(self.sql_regex.search(text))
    
    def detect_command_injection(self, text: str) -> bool:
        """
        Detect command injection attempts
        
        Args:
            text: Text to check
            
        Returns:
            True if command injection detected
        """
        return bool(self.cmd_regex.search(text))
    
    def detect_xss(self, text: str) -> bool:
        """
        Detect XSS attempts
        
        Args:
            text: Text to check
            
        Returns:
            True if XSS detected
        """
        return bool(self.xss_regex.search(text))
    
    def sanitize(self, text: str, strict: bool = False) -> str:
        """
        Sanitize input text
        
        Args:
            text: Text to sanitize
            strict: If True, raise error on dangerous input
            
        Returns:
            Sanitized text
            
        Raises:
            SecurityError: If strict and dangerous input detected
        """
        if self.detect_sql_injection(text):
            if strict:
                raise SecurityError("SQL injection attempt detected")
            logger.warning("Potential SQL injection detected")
        
        if self.detect_command_injection(text):
            if strict:
                raise SecurityError("Command injection attempt detected")
            logger.warning("Potential command injection detected")
        
        if self.detect_xss(text):
            if strict:
                raise SecurityError("XSS attempt detected")
            logger.warning("Potential XSS detected")
        
        # Remove dangerous characters
        sanitized = text
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized


class SecurityAuditor:
    """
    Security auditing and scanning
    
    Features:
    - Code scanning
    - Configuration auditing
    - Vulnerability detection
    - Best practices checking
    
    Example:
        >>> auditor = SecurityAuditor()
        >>> issues = auditor.audit_code(code_string)
    """
    
    # Dangerous patterns in code
    DANGEROUS_PATTERNS = {
        'hardcoded_secret': (
            r'(api[_-]?key|password|secret|token)\s*=\s*["\'][^"\']+["\']',
            SecurityLevel.CRITICAL,
            "Hardcoded secret detected"
        ),
        'eval_usage': (
            r'\beval\s*\(',
            SecurityLevel.HIGH,
            "Use of eval() detected"
        ),
        'exec_usage': (
            r'\bexec\s*\(',
            SecurityLevel.HIGH,
            "Use of exec() detected"
        ),
        'pickle_usage': (
            r'import\s+pickle|from\s+pickle\s+import',
            SecurityLevel.MEDIUM,
            "Use of pickle detected (unsafe deserialization)"
        ),
        'shell_true': (
            r'shell\s*=\s*True',
            SecurityLevel.HIGH,
            "shell=True in subprocess (command injection risk)"
        ),
    }
    
    def __init__(self):
        """Initialize security auditor"""
        self.issues: List[SecurityIssue] = []
        logger.debug("SecurityAuditor initialized")
    
    def audit_code(self, code: str, filename: str = "unknown") -> List[SecurityIssue]:
        """
        Audit code for security issues
        
        Args:
            code: Code to audit
            filename: Filename for reporting
            
        Returns:
            List of security issues
        """
        issues = []
        
        for pattern_name, (pattern, level, description) in self.DANGEROUS_PATTERNS.items():
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                issue = SecurityIssue(
                    level=level,
                    category=pattern_name,
                    description=description,
                    location=f"{filename}:{self._get_line_number(code, match.start())}",
                    recommendation=self._get_recommendation(pattern_name)
                )
                issues.append(issue)
        
        self.issues.extend(issues)
        return issues
    
    def _get_line_number(self, text: str, position: int) -> int:
        """Get line number for position in text"""
        return text[:position].count('\n') + 1
    
    def _get_recommendation(self, pattern_name: str) -> str:
        """Get recommendation for issue"""
        recommendations = {
            'hardcoded_secret': "Use environment variables or SecretManager",
            'eval_usage': "Avoid eval(), use ast.literal_eval() or safer alternatives",
            'exec_usage': "Avoid exec(), refactor to use functions",
            'pickle_usage': "Use JSON or other safe serialization formats",
            'shell_true': "Use shell=False and pass command as list",
        }
        return recommendations.get(pattern_name, "Review and fix security issue")
    
    def audit_file(self, file_path: Path) -> List[SecurityIssue]:
        """
        Audit file for security issues
        
        Args:
            file_path: Path to file
            
        Returns:
            List of security issues
        """
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            return self.audit_code(code, str(file_path))
        except Exception as e:
            logger.error(f"Failed to audit file {file_path}: {e}")
            return []
    
    def audit_directory(self, directory: Path, extensions: Optional[Set[str]] = None) -> List[SecurityIssue]:
        """
        Audit directory for security issues
        
        Args:
            directory: Directory to audit
            extensions: File extensions to check (default: .py)
            
        Returns:
            List of security issues
        """
        if extensions is None:
            extensions = {'.py'}
        
        all_issues = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                issues = self.audit_file(file_path)
                all_issues.extend(issues)
        
        return all_issues
    
    def generate_report(self) -> str:
        """
        Generate security audit report
        
        Returns:
            Formatted report
        """
        if not self.issues:
            return "No security issues found."
        
        # Group by severity
        by_severity = {level: [] for level in SecurityLevel}
        for issue in self.issues:
            by_severity[issue.level].append(issue)
        
        lines = ["Security Audit Report", "=" * 50, ""]
        
        for level in [SecurityLevel.CRITICAL, SecurityLevel.HIGH, SecurityLevel.MEDIUM, SecurityLevel.LOW]:
            issues = by_severity[level]
            if issues:
                lines.append(f"{level.value.upper()} ({len(issues)} issues):")
                for issue in issues:
                    lines.append(f"  [{issue.category}] {issue.location}")
                    lines.append(f"    {issue.description}")
                    lines.append(f"    Fix: {issue.recommendation}")
                    lines.append("")
        
        lines.append(f"Total Issues: {len(self.issues)}")
        
        return "\n".join(lines)


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token
    
    Args:
        length: Token length in bytes
        
    Returns:
        Secure random token (hex)
    """
    return secrets.token_hex(length)


def hash_password(password: str) -> str:
    """
    Hash password securely
    
    Args:
        password: Password to hash
        
    Returns:
        Hashed password
    """
    # In production, use bcrypt or argon2
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hashed.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hash
    
    Args:
        password: Password to verify
        hashed: Hashed password
        
    Returns:
        True if password matches
    """
    try:
        salt, hash_value = hashed.split('$')
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return new_hash.hex() == hash_value
    except Exception:
        return False


# Global instances
_global_secret_manager: Optional[SecretManager] = None
_global_sanitizer: Optional[InputSanitizer] = None
_global_auditor: Optional[SecurityAuditor] = None


def get_secret_manager() -> SecretManager:
    """Get global secret manager"""
    global _global_secret_manager
    if _global_secret_manager is None:
        _global_secret_manager = SecretManager()
    return _global_secret_manager


def get_input_sanitizer() -> InputSanitizer:
    """Get global input sanitizer"""
    global _global_sanitizer
    if _global_sanitizer is None:
        _global_sanitizer = InputSanitizer()
    return _global_sanitizer


def get_security_auditor() -> SecurityAuditor:
    """Get global security auditor"""
    global _global_auditor
    if _global_auditor is None:
        _global_auditor = SecurityAuditor()
    return _global_auditor
