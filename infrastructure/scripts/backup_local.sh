#!/bin/bash
#
# Simple Local Backup Script for Amharic Document System
# For local development/testing use only
#
# Usage:
#   ./backup_local.sh                    # Full backup
#   ./backup_local.sh --database-only    # Database only
#   ./backup_local.sh --files-only       # Files only

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="amharic-doc-backup-${DATE}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Docker container names
POSTGRES_CONTAINER="amharic-doc-postgres"
MONGODB_CONTAINER="amharic-doc-mongodb"
MINIO_CONTAINER="amharic-doc-minio"
REDIS_CONTAINER="amharic-doc-redis"

# Create backup directory
mkdir -p "${BACKUP_PATH}"

echo "========================================"
echo "Amharic Document System - Local Backup"
echo "========================================"
echo "Backup location: ${BACKUP_PATH}"
echo "Date: $(date)"
echo ""

# Parse arguments
DATABASE_ONLY=false
FILES_ONLY=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --database-only)
      DATABASE_ONLY=true
      shift
      ;;
    --files-only)
      FILES_ONLY=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Backup PostgreSQL
if [ "$FILES_ONLY" = false ]; then
  echo "[1/4] Backing up PostgreSQL..."
  docker exec ${POSTGRES_CONTAINER} pg_dump -U postgres amharic_doc_system > "${BACKUP_PATH}/postgres.sql"
  echo "✓ PostgreSQL backup complete ($(du -h "${BACKUP_PATH}/postgres.sql" | cut -f1))"
fi

# Backup MongoDB
if [ "$FILES_ONLY" = false ]; then
  echo "[2/4] Backing up MongoDB..."
  docker exec ${MONGODB_CONTAINER} mongodump \
    --username=admin \
    --password=mongo_pass \
    --authenticationDatabase=admin \
    --db=amharic_documents \
    --archive=/tmp/mongodb-backup.archive

  docker cp ${MONGODB_CONTAINER}:/tmp/mongodb-backup.archive "${BACKUP_PATH}/mongodb.archive"
  docker exec ${MONGODB_CONTAINER} rm /tmp/mongodb-backup.archive
  echo "✓ MongoDB backup complete ($(du -h "${BACKUP_PATH}/mongodb.archive" | cut -f1))"
fi

# Backup MinIO (object storage)
if [ "$DATABASE_ONLY" = false ]; then
  echo "[3/4] Backing up MinIO files..."
  mkdir -p "${BACKUP_PATH}/minio"

  # Export MinIO data using mc (MinIO client)
  docker run --rm --network amharic-doc-network \
    -v "${BACKUP_PATH}/minio:/backup" \
    minio/mc \
    mirror minio/documents /backup/documents --quiet 2>/dev/null || \

  # Fallback: Copy volume directly
  docker run --rm \
    -v amharic-doc-minio_data:/data:ro \
    -v "${PWD}/${BACKUP_PATH}/minio:/backup" \
    alpine tar czf /backup/minio-data.tar.gz -C /data .

  echo "✓ MinIO backup complete ($(du -sh "${BACKUP_PATH}/minio" | cut -f1))"
fi

# Backup Redis (optional - mainly cache)
if [ "$DATABASE_ONLY" = false ]; then
  echo "[4/4] Backing up Redis..."
  docker exec ${REDIS_CONTAINER} redis-cli SAVE > /dev/null 2>&1 || true
  docker cp ${REDIS_CONTAINER}:/data/dump.rdb "${BACKUP_PATH}/redis-dump.rdb" 2>/dev/null || \
    echo "⚠ Redis backup skipped (no persistent data)"
fi

# Create metadata file
cat > "${BACKUP_PATH}/backup-info.txt" << EOF
Amharic Document System Backup
==============================
Date: $(date)
Hostname: $(hostname)
Backup Type: $([ "$DATABASE_ONLY" = true ] && echo "Database Only" || [ "$FILES_ONLY" = true ] && echo "Files Only" || echo "Full Backup")

Components:
- PostgreSQL: $([ -f "${BACKUP_PATH}/postgres.sql" ] && echo "✓" || echo "✗")
- MongoDB: $([ -f "${BACKUP_PATH}/mongodb.archive" ] && echo "✓" || echo "✗")
- MinIO: $([ -d "${BACKUP_PATH}/minio" ] && echo "✓" || echo "✗")
- Redis: $([ -f "${BACKUP_PATH}/redis-dump.rdb" ] && echo "✓" || echo "✗")

Restore with:
  ./restore_local.sh ${BACKUP_NAME}
EOF

# Compress backup (optional)
echo ""
echo "Compressing backup..."
tar czf "${BACKUP_PATH}.tar.gz" -C "${BACKUP_DIR}" "${BACKUP_NAME}"
rm -rf "${BACKUP_PATH}"

BACKUP_SIZE=$(du -h "${BACKUP_PATH}.tar.gz" | cut -f1)

echo ""
echo "========================================"
echo "✅ Backup Complete!"
echo "========================================"
echo "Location: ${BACKUP_PATH}.tar.gz"
echo "Size: ${BACKUP_SIZE}"
echo ""
echo "To restore:"
echo "  ./restore_local.sh ${BACKUP_NAME}"
echo ""

# Cleanup old backups (keep last 7 days)
echo "Cleaning up old backups (keeping last 7)..."
ls -t "${BACKUP_DIR}"/amharic-doc-backup-*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm
echo "Done!"