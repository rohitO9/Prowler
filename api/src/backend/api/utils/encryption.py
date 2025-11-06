"""
Data Encryption Utilities for Azure AD Credentials
"""

import base64
import logging
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data
    """
    
    def __init__(self):
        self.key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.key)
    
    def _get_encryption_key(self):
        """Get encryption key from settings"""
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        
        if not key:
            # Generate a new key if none exists (for development)
            if settings.DEBUG:
                logger.warning("No ENCRYPTION_KEY found, generating new key for development")
                return Fernet.generate_key()
            else:
                raise ImproperlyConfigured(
                    "ENCRYPTION_KEY must be set in production. "
                    "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
        
        # Ensure key is bytes
        if isinstance(key, str):
            key = key.encode()
        
        return key
    
    def encrypt(self, data):
        """
        Encrypt sensitive data
        
        Args:
            data: String or bytes to encrypt
            
        Returns:
            str: Base64 encoded encrypted data
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self.cipher_suite.encrypt(data)
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data")
    
    def decrypt(self, encrypted_data):
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            str: Decrypted data
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
    
    def is_encrypted(self, data):
        """
        Check if data appears to be encrypted
        
        Args:
            data: Data to check
            
        Returns:
            bool: True if data appears encrypted
        """
        try:
            if not isinstance(data, str):
                return False
            
            # Try to decode as base64
            base64.b64decode(data.encode('utf-8'))
            return True
            
        except Exception:
            return False


# Global encryption service instance
_encryption_service = None


def get_encryption_service():
    """Get global encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_field(value):
    """Encrypt a field value"""
    if not value:
        return value
    
    encryption_service = get_encryption_service()
    return encryption_service.encrypt(value)


def decrypt_field(value):
    """Decrypt a field value"""
    if not value:
        return value
    
    encryption_service = get_encryption_service()
    
    # Check if value is already encrypted
    if encryption_service.is_encrypted(value):
        return encryption_service.decrypt(value)
    
    # Return as-is if not encrypted (for backward compatibility)
    return value
