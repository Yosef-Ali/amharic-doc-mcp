# Encryption at Rest Configuration

Complete guide for AES-128 encryption at rest across all system components.

## Overview

The Amharic Document Processing System implements comprehensive encryption at rest:

- **Field-Level Encryption**: Sensitive database fields (emails, PII)
- **Database Encryption**: PostgreSQL transparent data encryption (TDE)
- **Object Storage Encryption**: MinIO server-side encryption
- **MongoDB Encryption**: WiredTiger encryption at rest
- **Redis Encryption**: Encrypted snapshots
- **Key Management**: Master key with versioned rotation

## Architecture

```
┌──────────────────┐
│   Master Key     │  (Environment variable or Key Vault)
│  (Base64 256bit) │
└────────┬─────────┘
         │
         ├─► PBKDF2 Key Derivation (100k iterations)
         │
    ┌────┴──────────────────────────┐
    │                                │
    ▼                                ▼
┌───────────┐                  ┌──────────┐
│  AES-128  │                  │ Storage  │
│Field-Level│                  │   Keys   │
│Encryption │                  │ (MinIO)  │
└───────────┘                  └──────────┘
    │
    ├─► Database columns
    ├─► Secrets storage
    └─► Sensitive configuration
```

## Quick Start

### 1. Generate Master Encryption Key

```bash
# Generate master key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Output example:
# gAAAAABhj...long_key_here...xyz=
```

### 2. Set Environment Variables

```bash
# Required
export MASTER_ENCRYPTION_KEY="your_generated_master_key_here"
export ENCRYPTION_KEY_VERSION="1"

# Optional: MinIO encryption
export MINIO_ENCRYPTION_KEY="$(openssl rand -base64 32)"

# Optional: Key vault integration
export KEY_VAULT_URL="https://your-vault.vault.azure.net/"
```

### 3. Initialize Encryption in Application

```python
# In backend/src/main.py startup event
from src.config.security import initialize_encryption

@app.on_event("startup")
async def startup():
    initialize_encryption()
    logger.info("Encryption initialized")
```

## Component Configuration

### PostgreSQL Encryption

PostgreSQL transparent data encryption using pgcrypto:

```sql
-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Application-level encryption handled by SQLAlchemy EncryptedString type
-- No additional PostgreSQL configuration required for field-level encryption

-- For full database encryption (optional), use PostgreSQL TDE:
-- Requires compiled PostgreSQL with encryption support
```

**Docker Configuration:**
```yaml
# infrastructure/docker-compose.yml
postgres:
  environment:
    # Application handles field-level encryption
    POSTGRES_INITDB_ARGS: "--encoding=UTF8 --data-checksums"
  command: >
    postgres
    -c ssl=on
    -c ssl_cert_file=/etc/ssl/certs/server.crt
    -c ssl_key_file=/etc/ssl/private/server.key
```

### MongoDB Encryption

WiredTiger encryption at rest:

```yaml
# infrastructure/docker-compose.yml
mongodb:
  image: mongo:7
  command: >
    mongod
    --enableEncryption
    --encryptionKeyFile /data/mongodb-keyfile
  environment:
    MONGO_INITDB_ROOT_USERNAME: admin
    MONGO_INITDB_ROOT_PASSWORD: mongo_pass
  volumes:
    - ./security/mongodb-keyfile:/data/mongodb-keyfile:ro
```

**Generate MongoDB keyfile:**
```bash
# Create 96-byte random keyfile
openssl rand -base64 96 > infrastructure/security/mongodb-keyfile
chmod 400 infrastructure/security/mongodb-keyfile
```

### MinIO Object Storage Encryption

Server-side encryption (SSE-S3 or SSE-KMS):

```python
# In application code
from src.config.security import StorageEncryption

# Configure MinIO client with encryption
sse_config = StorageEncryption.configure_minio_encryption()

# For SSE-C (customer-provided keys) on upload
sse_headers = StorageEncryption.get_minio_sse_headers()

minio_client.put_object(
    bucket_name="documents",
    object_name="file.pdf",
    data=file_data,
    length=file_size,
    metadata=sse_headers  # Encrypted with AES-256
)
```

**MinIO Environment Configuration:**
```bash
# Enable MinIO KMS encryption (production recommended)
export MINIO_KMS_KES_ENDPOINT="https://kes-server:7373"
export MINIO_KMS_KES_KEY_NAME="amharic-doc-key"
export MINIO_KMS_KES_CERT_FILE="/certs/client.cert"
export MINIO_KMS_KES_KEY_FILE="/certs/client.key"
```

### Redis Encrypted Snapshots

Redis persistence with encryption:

```yaml
# infrastructure/docker-compose.yml
redis:
  command: >
    redis-server
    --appendonly yes
    --save 900 1
    --save 300 10
    --save 60 10000
    --rdbcompression yes
    --rdbchecksum yes
  volumes:
    - redis_data:/data

# Encrypt Redis snapshots post-processing
# Use filesystem-level encryption (LUKS) or application-level encryption
```

### Elasticsearch Encryption

Node-to-node encryption and encrypted indices:

```yaml
# infrastructure/docker-compose.yml
elasticsearch:
  environment:
    - xpack.security.enabled=true
    - xpack.security.transport.ssl.enabled=true
    - xpack.security.http.ssl.enabled=true
```

## Field-Level Encryption Usage

### Define Encrypted Columns

```python
from sqlalchemy import Column, Integer, String
from src.config.security import EncryptedString
from src.db.models.base import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)

    # These fields are automatically encrypted/decrypted
    email = Column(EncryptedString(255), nullable=False)
    phone = Column(EncryptedString(50), nullable=True)
    ssn = Column(EncryptedString(50), nullable=True)
```

### Manual Encryption/Decryption

```python
from src.config.security import get_field_encryption

encryption = get_field_encryption()

# Encrypt sensitive data
encrypted_value = encryption.encrypt("sensitive_data_here")
# Returns: "v1:base64_iv:base64_ciphertext"

# Decrypt data
plaintext = encryption.decrypt(encrypted_value)
# Returns: "sensitive_data_here"

# Check if re-encryption needed (after key rotation)
if encryption.needs_reencryption(encrypted_value):
    new_encrypted = encryption.encrypt(plaintext)
```

## Secrets Management

### Store and Retrieve Secrets

```python
from src.config.security import get_secrets_manager

secrets = get_secrets_manager()

# Store API key
encrypted_api_key = secrets.store_secret("openai_api_key", "sk-...")

# Retrieve API key
api_key = secrets.get_secret("openai_api_key", encrypted_api_key)

# Rotate secret
new_encrypted = secrets.rotate_secret("openai_api_key", "sk-new-key...")
```

### Environment Variables for Secrets

```bash
# Store encrypted secrets in environment
export OPENAI_API_KEY_ENCRYPTED="v1:abc123...:xyz789..."

# Application decrypts on load
api_key = secrets.get_secret("openai_api_key", os.getenv("OPENAI_API_KEY_ENCRYPTED"))
```

## Key Rotation

### Rotate Encryption Keys

```python
from src.config.security import _key_manager

# Rotate to new key version
new_version = _key_manager.rotate_key()
print(f"Rotated to key version {new_version}")

# Update environment variable
# export ENCRYPTION_KEY_VERSION="2"
```

### Re-encrypt Existing Data

```python
# Migration script to re-encrypt data with new key
from sqlalchemy import select
from src.db.models.user import User
from src.config.security import get_field_encryption

encryption = get_field_encryption()

async def reencrypt_user_data(session):
    """Re-encrypt user data with current key version"""

    # Get all users
    result = await session.execute(select(User))
    users = result.scalars().all()

    for user in users:
        # SQLAlchemy will decrypt with old key, encrypt with new key on commit
        user.email = user.email  # Triggers decrypt/encrypt cycle
        user.phone = user.phone if user.phone else None

    await session.commit()
    print(f"Re-encrypted data for {len(users)} users")
```

## Security Best Practices

### 1. Master Key Storage

**Development:**
```bash
# .env file (DO NOT COMMIT)
MASTER_ENCRYPTION_KEY="..."
```

**Production (Recommended):**
- AWS KMS, Azure Key Vault, or HashiCorp Vault
- Environment variables in secure secret store
- Kubernetes Secrets with RBAC

```bash
# Kubernetes secret example
kubectl create secret generic encryption-keys \
  --from-literal=master-key="$MASTER_ENCRYPTION_KEY" \
  --namespace amharic-doc
```

### 2. Key Rotation Schedule

- **Master Key**: Rotate annually or on suspected compromise
- **Field Encryption Keys**: Rotate quarterly (automated via version)
- **Storage Keys**: Rotate semi-annually
- **Secrets**: Rotate on team member departure or 90 days

### 3. Access Control

```python
# Restrict encryption key access to specific roles
from src.services.auth import require_role

@require_role("security_admin")
async def rotate_encryption_keys():
    """Only security admins can rotate keys"""
    pass
```

### 4. Audit Logging

```python
# Log all encryption operations
import logging
from src.services.audit import audit_log

logger = logging.getLogger(__name__)

def encrypt_with_audit(data: str, context: dict):
    result = encryption.encrypt(data)

    audit_log.record_event(
        event_type="data_encryption",
        user_id=context.get("user_id"),
        resource="sensitive_field",
        details={"key_version": key_manager.current_key_version}
    )

    return result
```

## Compliance

### GDPR Requirements
✅ Encryption at rest for all PII (names, emails, addresses)
✅ Key management with rotation
✅ Audit trail for encryption operations
✅ Right to erasure (encrypted deletion)

### Ethiopian Data Protection
✅ Local data encryption requirements
✅ Government compliance for data storage
✅ Audit logs for regulatory review

## Verification

### Test Encryption

```bash
# Run encryption tests
cd backend
pytest tests/unit/test_encryption.py -v

# Verify field encryption
python -m src.config.security
```

### Verify Database Encryption

```sql
-- PostgreSQL: Check encrypted columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'users' AND column_name IN ('email', 'phone');

-- Data should appear as encrypted strings in database
SELECT email FROM users LIMIT 1;
-- Returns: v1:ABC123...:XYZ789...
```

### Verify MinIO Encryption

```bash
# Check MinIO encryption headers
mc stat minio/documents/file.pdf | grep -i encrypt
```

## Troubleshooting

### "Encryption not initialized" Error

```python
# Ensure initialize_encryption() is called on startup
from src.config.security import initialize_encryption

initialize_encryption()
```

### Decryption Failed

- **Check key version matches**: Old data with rotated key
- **Verify master key**: Ensure MASTER_ENCRYPTION_KEY is correct
- **Re-encrypt data**: Use migration script after key rotation

### Performance Impact

- Field encryption adds ~1-5ms per operation
- Use selective encryption (only sensitive fields)
- Consider caching decrypted values (in-memory only)

## References

- [NIST AES Specification](https://csrc.nist.gov/publications/detail/fips/197/final)
- [GDPR Encryption Requirements](https://gdpr.eu/encryption/)
- [PostgreSQL Encryption](https://www.postgresql.org/docs/current/encryption-options.html)
- [MinIO Encryption Guide](https://min.io/docs/minio/linux/operations/server-side-encryption.html)
- [MongoDB Encryption](https://www.mongodb.com/docs/manual/core/security-encryption-at-rest/)