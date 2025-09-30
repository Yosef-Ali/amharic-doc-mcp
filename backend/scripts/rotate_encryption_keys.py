#!/usr/bin/env python3
"""
Encryption Key Rotation Script

Rotates encryption keys and re-encrypts existing data.

Usage:
    python scripts/rotate_encryption_keys.py --dry-run
    python scripts/rotate_encryption_keys.py --execute --tables users,documents
    python scripts/rotate_encryption_keys.py --verify

Features:
- Dry-run mode for testing
- Selective table re-encryption
- Progress tracking
- Rollback support
- Verification mode
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import List, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, inspect
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config.security import (
    initialize_encryption,
    get_field_encryption,
    _key_manager,
    EncryptedString,
)
from src.config.settings import get_settings
from src.db.models.base import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KeyRotationManager:
    """Manages encryption key rotation process"""

    def __init__(self, database_url: str):
        """
        Initialize key rotation manager.

        Args:
            database_url: Async database connection URL
        """
        self.engine = create_async_engine(database_url, echo=False)
        self.encryption = None
        self.old_key_version = None
        self.new_key_version = None

    async def initialize(self):
        """Initialize encryption system"""
        initialize_encryption()
        self.encryption = get_field_encryption()
        self.old_key_version = _key_manager.current_key_version

        logger.info(f"Current encryption key version: {self.old_key_version}")

    async def rotate_key(self) -> int:
        """
        Rotate to new encryption key version.

        Returns:
            New key version number
        """
        self.new_key_version = _key_manager.rotate_key()

        logger.info(f"Rotated encryption key: v{self.old_key_version} → v{self.new_key_version}")

        # Update environment variable for persistence
        os.environ["ENCRYPTION_KEY_VERSION"] = str(self.new_key_version)

        return self.new_key_version

    async def get_encrypted_columns(self, model_class) -> List[str]:
        """
        Get list of encrypted columns for a model.

        Args:
            model_class: SQLAlchemy model class

        Returns:
            List of encrypted column names
        """
        encrypted_columns = []

        for column in model_class.__table__.columns:
            if isinstance(column.type, EncryptedString):
                encrypted_columns.append(column.name)

        return encrypted_columns

    async def reencrypt_table(
        self,
        model_class,
        session: AsyncSession,
        batch_size: int = 100,
        dry_run: bool = False
    ) -> dict:
        """
        Re-encrypt all records in a table.

        Args:
            model_class: SQLAlchemy model class
            session: Database session
            batch_size: Records per batch
            dry_run: If True, don't commit changes

        Returns:
            Statistics dict
        """
        table_name = model_class.__tablename__
        encrypted_columns = await self.get_encrypted_columns(model_class)

        if not encrypted_columns:
            logger.info(f"Table '{table_name}' has no encrypted columns, skipping")
            return {"table": table_name, "records": 0, "columns": 0}

        logger.info(f"Re-encrypting table '{table_name}' (columns: {encrypted_columns})")

        # Count total records
        count_result = await session.execute(
            select(model_class).with_only_columns([model_class.id])
        )
        total_records = len(count_result.scalars().all())

        logger.info(f"Total records to process: {total_records}")

        # Process in batches
        processed = 0
        errors = 0

        for offset in range(0, total_records, batch_size):
            try:
                # Fetch batch
                result = await session.execute(
                    select(model_class)
                    .limit(batch_size)
                    .offset(offset)
                )
                records = result.scalars().all()

                # Re-encrypt each record
                for record in records:
                    try:
                        for column_name in encrypted_columns:
                            # Reading the value triggers decryption (old key)
                            # Setting it triggers encryption (new key)
                            current_value = getattr(record, column_name)

                            if current_value:
                                # Check if needs re-encryption
                                if self.encryption.needs_reencryption(current_value):
                                    # Decrypt with old key, encrypt with new key
                                    decrypted = self.encryption.decrypt(current_value)
                                    reencrypted = self.encryption.encrypt(
                                        decrypted,
                                        key_version=self.new_key_version
                                    )
                                    setattr(record, column_name, reencrypted)

                        processed += 1

                    except Exception as e:
                        logger.error(f"Error processing record {record.id}: {e}")
                        errors += 1

                # Commit batch
                if not dry_run:
                    await session.commit()
                else:
                    await session.rollback()

                # Progress update
                progress = (offset + len(records)) / total_records * 100
                logger.info(f"Progress: {progress:.1f}% ({processed}/{total_records})")

            except Exception as e:
                logger.error(f"Batch error at offset {offset}: {e}")
                await session.rollback()
                errors += batch_size

        return {
            "table": table_name,
            "records": total_records,
            "processed": processed,
            "errors": errors,
            "columns": len(encrypted_columns)
        }

    async def reencrypt_all_tables(
        self,
        model_classes: List,
        batch_size: int = 100,
        dry_run: bool = False
    ) -> List[dict]:
        """
        Re-encrypt all specified tables.

        Args:
            model_classes: List of SQLAlchemy model classes
            batch_size: Records per batch
            dry_run: If True, don't commit changes

        Returns:
            List of statistics dicts
        """
        results = []

        async with AsyncSession(self.engine) as session:
            for model_class in model_classes:
                result = await self.reencrypt_table(
                    model_class,
                    session,
                    batch_size=batch_size,
                    dry_run=dry_run
                )
                results.append(result)

        return results

    async def verify_encryption(self, model_classes: List) -> dict:
        """
        Verify all encrypted data uses current key version.

        Args:
            model_classes: List of SQLAlchemy model classes

        Returns:
            Verification results
        """
        results = {}

        async with AsyncSession(self.engine) as session:
            for model_class in model_classes:
                table_name = model_class.__tablename__
                encrypted_columns = await self.get_encrypted_columns(model_class)

                if not encrypted_columns:
                    continue

                # Check all records
                result = await session.execute(select(model_class))
                records = result.scalars().all()

                old_key_count = 0
                current_key_count = 0

                for record in records:
                    for column_name in encrypted_columns:
                        value = getattr(record, column_name)

                        if value:
                            if self.encryption.needs_reencryption(value):
                                old_key_count += 1
                            else:
                                current_key_count += 1

                results[table_name] = {
                    "total_records": len(records),
                    "current_key": current_key_count,
                    "old_key": old_key_count,
                    "status": "OK" if old_key_count == 0 else "NEEDS_ROTATION"
                }

        return results

    async def cleanup(self):
        """Cleanup resources"""
        await self.engine.dispose()


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Rotate encryption keys")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without committing changes"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute key rotation and re-encryption"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify encryption status"
    )
    parser.add_argument(
        "--tables",
        type=str,
        help="Comma-separated list of tables to process (default: all)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Records to process per batch (default: 100)"
    )

    args = parser.parse_args()

    # Load settings
    settings = get_settings()

    # Initialize manager
    manager = KeyRotationManager(settings.database_url)
    await manager.initialize()

    # Get model classes
    # TODO: Import actual model classes from your application
    from src.db.models.user import User
    from src.db.models.document import Document
    from src.db.models.processing_job import ProcessingJob

    all_models = [User, Document, ProcessingJob]

    # Filter models if specific tables requested
    if args.tables:
        table_names = args.tables.split(',')
        model_classes = [
            m for m in all_models
            if m.__tablename__ in table_names
        ]
    else:
        model_classes = all_models

    logger.info(f"Processing tables: {[m.__tablename__ for m in model_classes]}")

    try:
        if args.verify:
            # Verification mode
            logger.info("Starting encryption verification...")

            results = await manager.verify_encryption(model_classes)

            print("\n=== Verification Results ===")
            for table, stats in results.items():
                print(f"\nTable: {table}")
                print(f"  Total records: {stats['total_records']}")
                print(f"  Current key: {stats['current_key']}")
                print(f"  Old key: {stats['old_key']}")
                print(f"  Status: {stats['status']}")

        elif args.execute or args.dry_run:
            # Rotation mode
            mode = "DRY-RUN" if args.dry_run else "EXECUTE"
            logger.info(f"Starting key rotation ({mode})...")

            if not args.dry_run:
                # Rotate key
                new_version = await manager.rotate_key()
                logger.info(f"New key version: {new_version}")
            else:
                logger.info("Dry-run mode: key not rotated")

            # Re-encrypt data
            results = await manager.reencrypt_all_tables(
                model_classes,
                batch_size=args.batch_size,
                dry_run=args.dry_run
            )

            # Print summary
            print("\n=== Re-encryption Summary ===")
            total_processed = 0
            total_errors = 0

            for result in results:
                print(f"\nTable: {result['table']}")
                print(f"  Records: {result['records']}")
                print(f"  Processed: {result['processed']}")
                print(f"  Errors: {result['errors']}")
                print(f"  Encrypted columns: {result['columns']}")

                total_processed += result['processed']
                total_errors += result['errors']

            print(f"\nTotal processed: {total_processed}")
            print(f"Total errors: {total_errors}")

            if args.dry_run:
                print("\n⚠️  DRY-RUN MODE: No changes committed")
            else:
                print("\n✅ Key rotation complete!")
                print(f"Update environment: export ENCRYPTION_KEY_VERSION={manager.new_key_version}")

        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"Key rotation failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())