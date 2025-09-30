# Backup & Restore Scripts

Simple local backup and restore for development/testing.

## Quick Start

### Create Backup

```bash
cd infrastructure/scripts

# Full backup (databases + files)
./backup_local.sh

# Database only
./backup_local.sh --database-only

# Files only
./backup_local.sh --files-only
```

Backups are saved to `./backups/` and automatically compressed.

### Restore Backup

```bash
# List available backups
./restore_local.sh

# Restore specific backup
./restore_local.sh amharic-doc-backup-20250130_143022
```

**⚠️ Warning**: Restore will overwrite existing data!

## What Gets Backed Up

- **PostgreSQL**: User data, documents metadata, processing jobs
- **MongoDB**: Document content, extracted text
- **MinIO**: Uploaded files, processed documents
- **Redis**: Cache data (optional)

## Backup Schedule

For local use, run manually when needed:

```bash
# Before major changes
./backup_local.sh

# Weekly backup (add to cron)
0 2 * * 0 cd /path/to/project/infrastructure/scripts && ./backup_local.sh
```

## Storage

- Backups kept for 7 days (automatically cleaned)
- Location: `./backups/`
- Format: `.tar.gz` compressed archives

## Restore Steps

1. **Stop services** (optional but recommended):
   ```bash
   cd infrastructure
   docker-compose stop backend celery-worker
   ```

2. **Restore backup**:
   ```bash
   cd scripts
   ./restore_local.sh amharic-doc-backup-YYYYMMDD_HHMMSS
   ```

3. **Restart services**:
   ```bash
   cd ../
   docker-compose restart
   ```

## Troubleshooting

**Backup fails - container not found**
```bash
# Check container names
docker ps

# Update container names in scripts if needed
```

**Large backup size**
```bash
# Use database-only for faster backups
./backup_local.sh --database-only
```

**Restore fails**
```bash
# Ensure services are running
cd infrastructure && docker-compose up -d

# Check logs
docker-compose logs postgres mongodb
```

## Production Notes

For production deployment, use:
- **AWS RDS/DocumentDB**: Automated backups
- **Azure Database**: Point-in-time restore
- **Kubernetes**: Velero for volume backups
- **Object Storage**: Versioning enabled

This script is for **local development only**!