#!/usr/bin/env python3
"""
Generate Encryption Keys

Generates all required encryption keys for the system.

Usage:
    python scripts/generate_encryption_keys.py
    python scripts/generate_encryption_keys.py --output .env
"""

import argparse
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


def generate_master_key() -> str:
    """Generate master encryption key"""
    key = Fernet.generate_key()
    return key.decode()


def generate_random_key(size: int = 32) -> str:
    """Generate random key of specified size"""
    key = os.urandom(size)
    return base64.b64encode(key).decode()


def generate_mongodb_keyfile(output_path: str = None):
    """
    Generate MongoDB encryption keyfile (96 bytes).

    Args:
        output_path: Path to save keyfile (default: infrastructure/security/mongodb-keyfile)
    """
    if output_path is None:
        output_path = "infrastructure/security/mongodb-keyfile"

    # Generate 96 random bytes
    key_data = os.urandom(96)

    # Encode to base64
    key_b64 = base64.b64encode(key_data).decode()

    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(key_b64)

    # Set restrictive permissions
    os.chmod(output_path, 0o400)

    print(f"✅ MongoDB keyfile generated: {output_path}")
    print(f"   Permissions: 400 (read-only for owner)")


def main():
    parser = argparse.ArgumentParser(description="Generate encryption keys")
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for environment variables (default: print to stdout)"
    )
    parser.add_argument(
        "--mongodb-keyfile",
        type=str,
        default="infrastructure/security/mongodb-keyfile",
        help="Path for MongoDB keyfile (default: infrastructure/security/mongodb-keyfile)"
    )

    args = parser.parse_args()

    # Generate keys
    master_key = generate_master_key()
    minio_key = generate_random_key(32)
    key_version = "1"

    # Generate MongoDB keyfile
    generate_mongodb_keyfile(args.mongodb_keyfile)

    # Prepare output
    output = f"""# Encryption Keys
# Generated on: {os.popen('date').read().strip()}
#
# IMPORTANT: Store these keys securely!
# - Use a secrets manager in production (AWS KMS, Azure Key Vault, HashiCorp Vault)
# - Never commit these keys to version control
# - Rotate keys regularly (quarterly recommended)

# Master encryption key (for field-level encryption)
MASTER_ENCRYPTION_KEY={master_key}

# Encryption key version (increment when rotating keys)
ENCRYPTION_KEY_VERSION={key_version}

# MinIO object storage encryption key
MINIO_ENCRYPTION_KEY={minio_key}

# MongoDB encryption keyfile path
MONGODB_ENCRYPTION_KEYFILE={args.mongodb_keyfile}

# ============================================
# Additional Security Configuration
# ============================================

# Enable encryption verification on startup
VERIFY_ENCRYPTION_ON_STARTUP=true

# Enforce TLS for database connections
ENFORCE_TLS=true

# Log encryption operations for audit trail
LOG_ENCRYPTION_OPS=true
"""

    if args.output:
        # Write to file
        with open(args.output, 'w') as f:
            f.write(output)

        # Set restrictive permissions
        os.chmod(args.output, 0o600)

        print(f"\n✅ Encryption keys generated and saved to: {args.output}")
        print(f"   Permissions: 600 (read/write for owner only)")
        print(f"\n⚠️  IMPORTANT:")
        print(f"   1. Review the generated keys in {args.output}")
        print(f"   2. Store these keys in a secure secrets manager")
        print(f"   3. DO NOT commit {args.output} to version control")
        print(f"   4. Set up key rotation schedule (quarterly recommended)")
        print(f"\n📝 Next steps:")
        print(f"   1. Source the environment file: source {args.output}")
        print(f"   2. Start the application: docker-compose up -d")
        print(f"   3. Verify encryption: python scripts/rotate_encryption_keys.py --verify")

    else:
        # Print to stdout
        print(output)
        print("\n" + "="*60)
        print("📋 To save these keys to a file, run:")
        print("   python scripts/generate_encryption_keys.py --output .env.encryption")
        print("\n⚠️  IMPORTANT: Never commit encryption keys to version control!")


if __name__ == "__main__":
    main()