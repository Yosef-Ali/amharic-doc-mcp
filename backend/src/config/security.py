"""
Security Configuration for Amharic Document Processing System

Implements:
- AES-128 encryption at rest for sensitive data
- Key management and rotation
- Secrets encryption
- Field-level encryption for database
- Storage encryption (MinIO, file system)
"""

import os
import base64
import hashlib
from typing import Optional, Union, Dict, Any
from datetime import datetime, timedelta
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

logger = logging.getLogger(__name__)


class EncryptionKeyManager:
    """
    Manages encryption keys with rotation support.

    Keys are derived from master key using PBKDF2 for AES-128 encryption.
    Supports key versioning for rotation without data loss.
    """

    def __init__(
        self,
        master_key: Optional[str] = None,
        key_vault_url: Optional[str] = None,
    ):
        """
        Initialize key manager.

        Args:
            master_key: Master encryption key (base64 encoded)
            key_vault_url: Optional external key vault URL (AWS KMS, Azure Key Vault)
        """
        self.master_key = master_key or os.getenv("MASTER_ENCRYPTION_KEY")
        self.key_vault_url = key_vault_url or os.getenv("KEY_VAULT_URL")

        if not self.master_key and not self.key_vault_url:
            raise ValueError("Either master_key or key_vault_url must be provided")

        # Key rotation tracking
        self.current_key_version = int(os.getenv("ENCRYPTION_KEY_VERSION", "1"))
        self.key_cache: Dict[int, bytes] = {}

        logger.info(f"Encryption key manager initialized (version: {self.current_key_version})")

    def get_encryption_key(self, version: Optional[int] = None) -> bytes:
        """
        Get encryption key for specified version.

        Args:
            version: Key version (defaults to current)

        Returns:
            AES-128 encryption key (16 bytes)
        """
        version = version or self.current_key_version

        # Check cache first
        if version in self.key_cache:
            return self.key_cache[version]

        # Derive key from master key
        if self.master_key:
            key = self._derive_key(self.master_key, version)
            self.key_cache[version] = key
            return key

        # Fetch from key vault
        if self.key_vault_url:
            key = self._fetch_from_vault(version)
            self.key_cache[version] = key
            return key

        raise ValueError("No key source available")

    def _derive_key(self, master_key: str, version: int) -> bytes:
        """
        Derive encryption key from master key using PBKDF2.

        Args:
            master_key: Master key string
            version: Key version for salt

        Returns:
            Derived AES-128 key (16 bytes)
        """
        # Use version as part of salt for key derivation
        salt = f"amharic-doc-v{version}".encode()

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=16,  # AES-128 requires 16 bytes
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )

        key = kdf.derive(master_key.encode())
        return key

    def _fetch_from_vault(self, version: int) -> bytes:
        """
        Fetch key from external key vault.

        Args:
            version: Key version

        Returns:
            Encryption key from vault
        """
        # TODO: Implement key vault integration (AWS KMS, Azure Key Vault, HashiCorp Vault)
        raise NotImplementedError("Key vault integration not implemented")

    def rotate_key(self) -> int:
        """
        Rotate to new encryption key version.

        Returns:
            New key version
        """
        new_version = self.current_key_version + 1

        # Generate new key
        self.get_encryption_key(new_version)

        # Update current version
        self.current_key_version = new_version

        logger.info(f"Encryption key rotated to version {new_version}")

        return new_version

    @staticmethod
    def generate_master_key() -> str:
        """
        Generate a new master encryption key.

        Returns:
            Base64-encoded master key
        """
        key = Fernet.generate_key()
        return key.decode()


class FieldEncryption:
    """
    Field-level encryption for sensitive database fields.

    Uses AES-128-CBC with PKCS7 padding for encrypt/decrypt operations.
    Stores encrypted data with key version prefix for rotation support.
    """

    def __init__(self, key_manager: EncryptionKeyManager):
        """
        Initialize field encryption.

        Args:
            key_manager: Key manager instance
        """
        self.key_manager = key_manager

    def encrypt(self, plaintext: Union[str, bytes], key_version: Optional[int] = None) -> str:
        """
        Encrypt plaintext data.

        Args:
            plaintext: Data to encrypt
            key_version: Optional key version (defaults to current)

        Returns:
            Base64-encoded encrypted data with version prefix
            Format: "v{version}:{iv}:{ciphertext}"
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')

        # Get encryption key
        version = key_version or self.key_manager.current_key_version
        key = self.key_manager.get_encryption_key(version)

        # Generate random IV
        iv = os.urandom(16)

        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        # Pad plaintext to AES block size (16 bytes)
        padded_plaintext = self._pad(plaintext)

        # Encrypt
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

        # Encode result with version prefix
        iv_b64 = base64.b64encode(iv).decode('utf-8')
        ciphertext_b64 = base64.b64encode(ciphertext).decode('utf-8')

        return f"v{version}:{iv_b64}:{ciphertext_b64}"

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data.

        Args:
            encrypted_data: Encrypted data with version prefix

        Returns:
            Decrypted plaintext string
        """
        # Parse version, IV, and ciphertext
        parts = encrypted_data.split(':')
        if len(parts) != 3:
            raise ValueError("Invalid encrypted data format")

        version_str, iv_b64, ciphertext_b64 = parts
        version = int(version_str[1:])  # Remove 'v' prefix

        # Decode from base64
        iv = base64.b64decode(iv_b64)
        ciphertext = base64.b64decode(ciphertext_b64)

        # Get decryption key
        key = self.key_manager.get_encryption_key(version)

        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()

        # Decrypt
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove padding
        plaintext = self._unpad(padded_plaintext)

        return plaintext.decode('utf-8')

    @staticmethod
    def _pad(data: bytes) -> bytes:
        """PKCS7 padding to AES block size (16 bytes)"""
        padding_length = 16 - (len(data) % 16)
        padding = bytes([padding_length] * padding_length)
        return data + padding

    @staticmethod
    def _unpad(data: bytes) -> bytes:
        """Remove PKCS7 padding"""
        padding_length = data[-1]
        return data[:-padding_length]

    def needs_reencryption(self, encrypted_data: str) -> bool:
        """
        Check if data needs re-encryption with current key.

        Args:
            encrypted_data: Encrypted data with version prefix

        Returns:
            True if data uses old key version
        """
        version_str = encrypted_data.split(':')[0]
        version = int(version_str[1:])
        return version < self.key_manager.current_key_version


class StorageEncryption:
    """
    Encryption for object storage (MinIO) and file system.
    """

    @staticmethod
    def configure_minio_encryption() -> Dict[str, Any]:
        """
        Get MinIO server-side encryption configuration.

        Returns:
            MinIO SSE-C encryption headers
        """
        # For production, use MinIO KMS or SSE-S3
        # This example uses SSE-C (customer-provided keys)

        encryption_key = os.getenv("MINIO_ENCRYPTION_KEY")
        if not encryption_key:
            logger.warning("MinIO encryption key not configured")
            return {}

        # Generate MD5 hash of key for MinIO
        key_bytes = base64.b64decode(encryption_key)
        key_md5 = hashlib.md5(key_bytes).digest()

        return {
            "ServerSideEncryption": {
                "Rule": {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            }
        }

    @staticmethod
    def get_minio_sse_headers(key: Optional[bytes] = None) -> Dict[str, str]:
        """
        Get SSE-C headers for MinIO requests.

        Args:
            key: Optional encryption key (defaults to env var)

        Returns:
            SSE-C headers dict
        """
        if key is None:
            key_str = os.getenv("MINIO_ENCRYPTION_KEY")
            if not key_str:
                return {}
            key = base64.b64decode(key_str)

        key_b64 = base64.b64encode(key).decode()
        key_md5 = base64.b64encode(hashlib.md5(key).digest()).decode()

        return {
            "X-Amz-Server-Side-Encryption-Customer-Algorithm": "AES256",
            "X-Amz-Server-Side-Encryption-Customer-Key": key_b64,
            "X-Amz-Server-Side-Encryption-Customer-Key-MD5": key_md5,
        }


class SecretsManager:
    """
    Encrypted secrets storage and retrieval.

    Encrypts sensitive configuration values (API keys, passwords, tokens).
    """

    def __init__(self, field_encryption: FieldEncryption):
        """
        Initialize secrets manager.

        Args:
            field_encryption: Field encryption instance
        """
        self.field_encryption = field_encryption
        self._secrets_cache: Dict[str, str] = {}

    def store_secret(self, name: str, value: str) -> str:
        """
        Encrypt and store secret.

        Args:
            name: Secret name
            value: Secret value (plaintext)

        Returns:
            Encrypted secret value
        """
        encrypted = self.field_encryption.encrypt(value)
        self._secrets_cache[name] = encrypted

        logger.info(f"Secret '{name}' stored (encrypted)")

        return encrypted

    def get_secret(self, name: str, encrypted_value: Optional[str] = None) -> str:
        """
        Retrieve and decrypt secret.

        Args:
            name: Secret name
            encrypted_value: Optional encrypted value (uses cache if not provided)

        Returns:
            Decrypted secret value
        """
        encrypted = encrypted_value or self._secrets_cache.get(name)

        if not encrypted:
            raise ValueError(f"Secret '{name}' not found")

        return self.field_encryption.decrypt(encrypted)

    def rotate_secret(self, name: str, new_value: str) -> str:
        """
        Rotate secret with new value and current key.

        Args:
            name: Secret name
            new_value: New secret value

        Returns:
            New encrypted value
        """
        return self.store_secret(name, new_value)


# Global instances (initialized in application startup)
_key_manager: Optional[EncryptionKeyManager] = None
_field_encryption: Optional[FieldEncryption] = None
_secrets_manager: Optional[SecretsManager] = None


def initialize_encryption():
    """
    Initialize encryption system on application startup.

    Call this in FastAPI startup event or worker initialization.
    """
    global _key_manager, _field_encryption, _secrets_manager

    _key_manager = EncryptionKeyManager()
    _field_encryption = FieldEncryption(_key_manager)
    _secrets_manager = SecretsManager(_field_encryption)

    logger.info("Encryption system initialized")


def get_field_encryption() -> FieldEncryption:
    """Get field encryption instance"""
    if _field_encryption is None:
        raise RuntimeError("Encryption not initialized. Call initialize_encryption() first.")
    return _field_encryption


def get_secrets_manager() -> SecretsManager:
    """Get secrets manager instance"""
    if _secrets_manager is None:
        raise RuntimeError("Encryption not initialized. Call initialize_encryption() first.")
    return _secrets_manager


# Database column encryption utilities for SQLAlchemy

from sqlalchemy.types import TypeDecorator, String


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy column type for encrypted strings.

    Usage:
        class User(Base):
            email = Column(EncryptedString(255), nullable=False)
            ssn = Column(EncryptedString(50), nullable=True)
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt on insert/update"""
        if value is not None:
            encryption = get_field_encryption()
            return encryption.encrypt(value)
        return value

    def process_result_value(self, value, dialect):
        """Decrypt on select"""
        if value is not None:
            encryption = get_field_encryption()
            return encryption.decrypt(value)
        return value


# Example usage in models:
"""
from src.config.security import EncryptedString, initialize_encryption
from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)
    email = Column(EncryptedString(255), nullable=False)  # Encrypted at rest
    phone = Column(EncryptedString(50), nullable=True)    # Encrypted at rest

# In application startup:
initialize_encryption()
"""