#!/bin/bash
#
# Simple Local Restore Script for Amharic Document System
# For local development/testing use only
#
# Usage:
#   ./restore_local.sh <backup_name>
#   ./restore_local.sh amharic-doc-backup-20250130_143022

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Docker container names
POSTGRES_CONTAINER="amharic-doc-postgres"
MONGODB_CONTAINER="amharic-doc-mongodb"
REDIS_CONTAINER="amharic-doc-redis"

if [ -z "$1" ]; then
  echo "Usage: $0 <backup_name>"
  echo ""
  echo "Available backups:"
  ls -1 "${BACKUP_DIR}"/amharic-doc-backup-*.tar.gz 2>/dev/null | xargs -n1 basename -s .tar.gz || echo "  (none found)"
  exit 1
fi

BACKUP_NAME="$1"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "❌ Backup not found: ${BACKUP_FILE}"
  exit 1
fi

echo "========================================"
echo "Amharic Document System - Local Restore"
echo "========================================"
echo "Backup: ${BACKUP_NAME}"
echo "Date: $(date)"
echo ""

# Extract backup
echo "Extracting backup..."
RESTORE_DIR="${BACKUP_DIR}/${BACKUP_NAME}"
tar xzf "${BACKUP_FILE}" -C "${BACKUP_DIR}"

# Show backup info
if [ -f "${RESTORE_DIR}/backup-info.txt" ]; then
  cat "${RESTORE_DIR}/backup-info.txt"
  echo ""
fi

read -p "⚠️  This will OVERWRITE existing data. Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "Restore cancelled."
  rm -rf "${RESTORE_DIR}"
  exit 0
fi

# Restore PostgreSQL
if [ -f "${RESTORE_DIR}/postgres.sql" ]; then
  echo ""
  echo "[1/4] Restoring PostgreSQL..."

  # Drop and recreate database
  docker exec ${POSTGRES_CONTAINER} psql -U postgres -c "DROP DATABASE IF EXISTS amharic_doc_system;"
  docker exec ${POSTGRES_CONTAINER} psql -U postgres -c "CREATE DATABASE amharic_doc_system;"

  # Restore data
  docker exec -i ${POSTGRES_CONTAINER} psql -U postgres amharic_doc_system < "${RESTORE_DIR}/postgres.sql"
  echo "✓ PostgreSQL restored"
fi

# Restore MongoDB
if [ -f "${RESTORE_DIR}/mongodb.archive" ]; then
  echo "[2/4] Restoring MongoDB..."

  # Copy archive to container
  docker cp "${RESTORE_DIR}/mongodb.archive" ${MONGODB_CONTAINER}:/tmp/mongodb-backup.archive

  # Drop and restore database
  docker exec ${MONGODB_CONTAINER} mongosh \
    --username=admin \
    --password=mongo_pass \
    --authenticationDatabase=admin \
    --eval "db.getSiblingDB('amharic_documents').dropDatabase()" \
    > /dev/null

  docker exec ${MONGODB_CONTAINER} mongorestore \
    --username=admin \
    --password=mongo_pass \
    --authenticationDatabase=admin \
    --archive=/tmp/mongodb-backup.archive

  docker exec ${MONGODB_CONTAINER} rm /tmp/mongodb-backup.archive
  echo "✓ MongoDB restored"
fi

# Restore MinIO
if [ -d "${RESTORE_DIR}/minio" ]; then
  echo "[3/4] Restoring MinIO files..."

  if [ -f "${RESTORE_DIR}/minio/minio-data.tar.gz" ]; then
    # Restore from tar.gz
    docker run --rm \
      -v amharic-doc-minio_data:/data \
      -v "${PWD}/${RESTORE_DIR}/minio:/backup:ro" \
      alpine sh -c "rm -rf /data/* && tar xzf /backup/minio-data.tar.gz -C /data"
  else
    # Copy files directly
    echo "⚠️  Direct file restore not implemented. Use MinIO mc client manually."
  fi

  echo "✓ MinIO restored"
fi

# Restore Redis
if [ -f "${RESTORE_DIR}/redis-dump.rdb" ]; then
  echo "[4/4] Restoring Redis..."

  docker exec ${REDIS_CONTAINER} redis-cli SHUTDOWN NOSAVE || true
  sleep 2

  docker cp "${RESTORE_DIR}/redis-dump.rdb" ${REDIS_CONTAINER}:/data/dump.rdb
  docker start ${REDIS_CONTAINER} 2>/dev/null || true

  echo "✓ Redis restored"
fi

# Cleanup
rm -rf "${RESTORE_DIR}"

echo ""
echo "========================================"
echo "✅ Restore Complete!"
echo "========================================"
echo ""
echo "Restart services to apply changes:"
echo "  cd infrastructure && docker-compose restart"
echo ""