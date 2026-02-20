# Terminal Todos Migration Guide

Complete guide for migrating your Terminal Todos data from one computer to another.

## Overview

Terminal Todos stores all data locally in `~/.terminal-todos/data/`:
- **SQLite database**: `todos.db` (todos, notes, emails, events, metadata)
- **ChromaDB vector store**: `chroma/` (embeddings for semantic search)

Use the built-in export/import commands to migrate your data safely.

## Quick Migration Steps

1. **On old computer**: Export data to ZIP file
2. **Transfer**: Upload ZIP to cloud storage
3. **On new computer**: Setup application and import data

## Detailed Migration Workflow

### Part 1: Export Data (Old Computer)

#### Step 1: Ensure Environment is Active

```bash
conda activate terminal-todos
```

#### Step 2: Export Your Data

```bash
terminal-todos export
```

This creates a ZIP file named `terminal-todos-export-YYYYMMDD_HHMMSS.zip` in your current directory.

**Example output**:
```
Exporting data to terminal-todos-export-20260220_143000.zip...
✓ Export successful!
  Todos:  150
  Notes:  45
  Emails: 8
  Events: 523

File: terminal-todos-export-20260220_143000.zip
```

**Custom output path**:
```bash
terminal-todos export --output ~/backups/my-todos-backup.zip
```

#### Step 3: Verify the Export

The ZIP file contains:
- `data_export.json` - Complete JSON export with all data
- `todos.db` - SQLite database backup
- `export_manifest.txt` - Human-readable summary

Check the manifest:
```bash
unzip -p terminal-todos-export-*.zip export_manifest.txt
```

### Part 2: Transfer Data

Upload your export ZIP file to cloud storage:

**Cloud Storage Options**:
- **Google Drive**: Upload via web or `gdrive` CLI
- **Dropbox**: Use web interface or Dropbox app
- **iCloud**: Copy to `~/Library/Mobile Documents/com~apple~CloudDocs/`
- **OneDrive**: Use OneDrive app or web interface
- **AWS S3**: `aws s3 cp backup.zip s3://mybucket/`
- **Email**: If small enough (< 25MB), email to yourself

**Alternative Transfer Methods**:
- USB drive
- AirDrop (macOS)
- Network transfer with `scp`: `scp backup.zip user@newcomputer:/path/`

### Part 3: Setup New Computer

**First**: Install Miniconda if you don't have it - See [docs/MINICONDA_SETUP.md](docs/MINICONDA_SETUP.md)
- Quick: `brew install miniconda && conda init zsh && source ~/.zshrc`

Then follow [SETUP.md](SETUP.md) to install Terminal Todos:

```bash
# 1. Clone repository
git clone <repository-url>
cd terminal-todos

# 2. Create conda environment
conda env create -f environment.yml

# 3. Activate environment
conda activate terminal-todos

# 4. Configure API key
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# 5. Verify installation (optional)
terminal-todos run
# Exit with Ctrl+C
```

### Part 4: Import Data (New Computer)

#### Step 1: Download Export ZIP

Download the ZIP file from cloud storage to your new computer.

Example:
```bash
# Download from cloud or copy from transfer location
mv ~/Downloads/terminal-todos-export-20260220_143000.zip ~/
```

#### Step 2: Import the Data

```bash
terminal-todos import ~/terminal-todos-export-20260220_143000.zip
```

**What happens during import**:
1. Validates ZIP file structure
2. Checks schema version compatibility
3. Imports all data (todos, notes, emails, events)
4. Rebuilds ChromaDB embeddings automatically
5. Verifies data integrity

**Example output**:
```
Importing data from terminal-todos-export-20260220_143000.zip...
Rebuilding vector store embeddings...
✓ Import successful!
  Imported 150 todos
  Imported 45 notes
  Imported 8 emails
  Imported 523 events
  Rebuilt 195 embeddings
```

#### Step 3: Verify Migration

Launch the app:
```bash
terminal-todos
```

Verify your data:
- Check todo count: `/stats`
- Search for a known todo: `/search <something you remember>`
- Review recent notes: `/note-search <topic>`

Test semantic search to ensure embeddings were rebuilt correctly.

## Advanced Options

### Export Options

**Custom filename**:
```bash
terminal-todos export --output ~/backups/todos-feb20.zip
```

**Verbose output** (for debugging):
```bash
terminal-todos export --verbose
```

### Import Options

#### Overwriting Existing Data

If the new computer already has some data, import will warn you:

```
⚠️  Warning: Database contains existing data:
  Todos: 10
  Notes: 3

Use --confirm-overwrite to proceed with import.
```

To proceed with overwrite:
```bash
terminal-todos import backup.zip --confirm-overwrite
```

**Safety features**:
- Automatic backup created before overwrite at `~/.terminal-todos/data/backups/pre-import-TIMESTAMP.db`
- Transaction-based import (rolls back on failure)
- Relationship validation before import

#### Import Methods

**JSON Import** (default, recommended):
```bash
terminal-todos import backup.zip --method json
```

- Imports data incrementally from JSON export
- Preserves all IDs and relationships
- Rebuilds vector embeddings
- Better validation and error messages

**SQLite Restore** (alternative):
```bash
terminal-todos import backup.zip --method sqlite
```

- Replaces entire database file with backup
- Faster import for large datasets
- All-or-nothing (no partial imports)
- Still rebuilds vector embeddings

**When to use SQLite method**:
- Very large datasets (10,000+ items)
- Exact restore needed (including internal SQLite metadata)
- Import speed is critical

**Verbose output**:
```bash
terminal-todos import backup.zip --verbose
```

Shows detailed progress and any warnings.

## What Gets Migrated

### Included in Export/Import

- **All Todos**: Content, completion status, priorities, due dates, focus order
- **All Notes**: Full content, titles, metadata (keywords, topics, tags, summaries)
- **All Emails**: Subjects, bodies, recipients, context references
- **Complete Audit Log**: Full event history of all changes
- **Relationships**: Todo→Note links, Email→Note references preserved
- **Metadata**: Schema version, configuration

### Not Included

- **Embeddings**: Regenerated on import (uses local model, no API calls)
- **`.env` file**: Must be configured manually on new computer
- **Error logs**: Fresh start on new computer

### Data Storage Locations

**Old Computer**:
```
~/.terminal-todos/data/
├── todos.db              # SQLite database
├── chroma/               # Vector embeddings
└── error.log             # Error logs
```

**New Computer** (after import):
```
~/.terminal-todos/data/
├── todos.db              # Imported from backup
├── chroma/               # Rebuilt from imported data
├── error.log             # Fresh log file
└── backups/              # Pre-import backups (if overwrite)
    └── pre-import-20260220_143000.db
```

## Troubleshooting

### "Export schema too new" Error

**Problem**: Export was created with a newer version of Terminal Todos

**Solution**:
```bash
# Update terminal-todos on new computer
conda activate terminal-todos
pip install --upgrade terminal-todos

# Or pull latest from git
git pull
pip install -e .
```

### "Database contains existing data" Warning

**Problem**: New computer already has some todos/notes

**Solutions**:

1. **Export existing data first** (recommended):
   ```bash
   terminal-todos export --output existing-data-backup.zip
   terminal-todos import old-computer-backup.zip --confirm-overwrite
   ```

2. **Skip import** and merge manually (if small dataset)

3. **Clear existing data**:
   ```bash
   rm -rf ~/.terminal-todos/data
   terminal-todos import backup.zip
   ```

### "Import validation failed" Error

**Problem**: Data relationships are broken (e.g., todo references missing note)

**Cause**: Corrupted export or database issue on old computer

**Solutions**:

1. **Re-export on old computer**:
   ```bash
   # On old computer
   terminal-todos export --output new-export.zip
   ```

2. **Use SQLite method**:
   ```bash
   terminal-todos import backup.zip --method sqlite --confirm-overwrite
   ```

3. **Check error log**:
   ```bash
   tail -50 ~/.terminal-todos/data/error.log
   ```

### "Vector store rebuild failed" Error

**Problem**: ChromaDB embedding generation failed

**Cause**: Usually network issues downloading embedding model, or disk space

**Solutions**:

1. **Complete import succeeded** (data is safe), just embeddings failed

2. **Manually rebuild**:
   ```python
   from terminal_todos.core.sync_service import SyncService
   sync = SyncService()
   stats = sync.full_sync()
   print(stats)
   ```

3. **Check disk space**:
   ```bash
   df -h ~/.terminal-todos
   ```

4. **Delete and rebuild ChromaDB**:
   ```bash
   rm -rf ~/.terminal-todos/data/chroma
   # Then re-run manual rebuild above
   ```

### ZIP File Corruption

**Problem**: "Not a valid ZIP file" or "unexpected end of file"

**Cause**: Incomplete download or upload

**Solutions**:

1. **Re-download from cloud storage**

2. **Verify file integrity** (if you have checksum):
   ```bash
   # On old computer (before upload)
   shasum -a 256 backup.zip > backup.zip.sha256

   # On new computer (after download)
   shasum -a 256 -c backup.zip.sha256
   ```

3. **Re-export on old computer** if file is corrupted

## Schema Versioning

Exports include schema version for compatibility checking:

- **Current schema version**: 6
- **Export includes**: Schema version in metadata
- **Import validates**: Ensures compatibility automatically
- **Migrations**: Run automatically if needed

### Version Compatibility

| Scenario | Result |
|----------|--------|
| Export v6 → Import v6 | ✓ Works perfectly |
| Export v5 → Import v6 | ✓ Migrations run automatically |
| Export v6 → Import v5 | ✗ Error - update app first |

For schema version history, see `/src/terminal_todos/db/migrations.py`

## Backup Best Practices

### Regular Backups

Create exports regularly:
```bash
# Weekly backup
terminal-todos export --output ~/backups/todos-$(date +%Y-%m-%d).zip

# Before major changes
terminal-todos export --output ~/backups/pre-migration-backup.zip
```

### Automated Backups

Add to cron (macOS/Linux):
```bash
# Edit crontab
crontab -e

# Add weekly Sunday backup at 2am
0 2 * * 0 /Users/you/miniconda3/envs/terminal-todos/bin/terminal-todos export --output ~/backups/todos-$(date +\%Y-\%m-\%d).zip
```

### Cloud Storage

Keep exports in cloud storage:
```bash
# Google Drive
terminal-todos export --output ~/Google\ Drive/backups/todos-backup.zip

# Dropbox
terminal-todos export --output ~/Dropbox/backups/todos-backup.zip

# iCloud
terminal-todos export --output ~/Library/Mobile\ Documents/com~apple~CloudDocs/backups/todos-backup.zip
```

### Retention Policy

Suggested retention:
- **Daily backups**: Keep 7 days
- **Weekly backups**: Keep 4 weeks
- **Monthly backups**: Keep 12 months
- **Major milestones**: Keep indefinitely

### Cleanup Old Backups

```bash
# Delete backups older than 30 days
find ~/backups -name "terminal-todos-export-*.zip" -mtime +30 -delete
```

## Multiple Computers

Use export/import to sync between computers (manual sync):

1. **Computer A**: `terminal-todos export --output sync.zip`
2. **Upload to cloud**
3. **Computer B**: Download and `terminal-todos import sync.zip --confirm-overwrite`

**Note**: This is a one-way sync (not bi-directional). Last import wins.

For bi-directional sync, track which computer has latest changes and export from there.

## Emergency Recovery

If you lose access to old computer:

1. **Check cloud backups**: Look for recent exports
2. **Check email**: If you emailed exports to yourself
3. **Check USB drives**: May have backup copies
4. **Check other computers**: May have synced data

If no backup exists:
- Start fresh on new computer
- Recreate critical todos from memory or other sources
- Set up regular backups going forward

## Testing the Migration

Before migrating production data, test the workflow:

```bash
# On old computer
terminal-todos export --output test-export.zip

# On new computer (or same computer, different directory)
# Import to test location
cd /tmp
terminal-todos import ~/test-export.zip

# Verify counts match
# If successful, proceed with actual migration
```

## Migration Checklist

**Before Export**:
- [ ] Terminal Todos is working on old computer
- [ ] All recent work is saved
- [ ] Run `/stats` to note counts

**Export**:
- [ ] `conda activate terminal-todos`
- [ ] `terminal-todos export --output backup.zip`
- [ ] Verify export completed successfully
- [ ] Note the counts (todos, notes, emails, events)

**Transfer**:
- [ ] Upload ZIP to cloud storage
- [ ] Verify upload completed
- [ ] Download ZIP on new computer
- [ ] Verify download integrity (file size matches)

**Setup New Computer**:
- [ ] Clone repository
- [ ] Create conda environment
- [ ] Configure `.env` with API key
- [ ] Test run `terminal-todos run` (then exit)

**Import**:
- [ ] `terminal-todos import backup.zip`
- [ ] Verify import counts match export counts
- [ ] Launch app: `terminal-todos`
- [ ] Verify todos are present
- [ ] Test semantic search
- [ ] Test agent interactions

**Cleanup Old Computer** (optional):
- [ ] Keep export ZIP as final backup
- [ ] Deactivate: `conda deactivate`
- [ ] Optional: Remove environment: `conda env remove -n terminal-todos`

## Getting Help

If you encounter issues during migration:

1. **Check error log**: `~/.terminal-todos/data/error.log`
2. **Use --verbose flag**: `terminal-todos import backup.zip --verbose`
3. **Verify ZIP integrity**: Re-download or re-export if corrupted
4. **Check setup**: Ensure new computer setup is complete
5. **Review troubleshooting**: See troubleshooting section above

For complete setup help, see [SETUP.md](SETUP.md)
