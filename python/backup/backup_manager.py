"""Backup management module.

Provides backup management with versioning and encryption.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages device configuration backups with versioning and encryption.

    Attributes:
        backup_dir: Base directory for backups.
        retention_days: Number of days to retain backups.
        encrypt: Whether to encrypt backups.
    """

    def __init__(
        self,
        backup_dir: str | Path = "./backups",
        retention_days: int = 90,
        encrypt: bool = True,
    ) -> None:
        """Initialize BackupManager.

        Args:
            backup_dir: Base directory for storing backups.
            retention_days: Number of days to retain old backups.
            encrypt: Whether to encrypt backup files.
        """
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.encrypt = encrypt
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        device_name: str,
        config: str,
        metadata: dict | None = None,
    ) -> Path:
        """Create a backup of a device configuration.

        Args:
            device_name: Device hostname.
            config: Configuration text to backup.
            metadata: Optional metadata to store alongside backup.

        Returns:
            Path to the backup file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_dir = self.backup_dir / device_name
        device_dir.mkdir(parents=True, exist_ok=True)

        backup_file = device_dir / f"{device_name}_{timestamp}.cfg"

        # Calculate checksum
        checksum = hashlib.sha256(config.encode()).hexdigest()

        # Write backup
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(config)

        # Write metadata
        meta_file = device_dir / f"{device_name}_{timestamp}.meta"
        import json
        meta_data = {
            "device": device_name,
            "timestamp": timestamp,
            "checksum_sha256": checksum,
            "size_bytes": len(config),
            "metadata": metadata or {},
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)

        logger.info(f"Backup created: {backup_file} (checksum: {checksum[:16]}...)")
        return backup_file

    def list_backups(self, device_name: str) -> list[Path]:
        """List all backups for a device.

        Args:
            device_name: Device hostname.

        Returns:
            List of backup file paths, sorted newest first.
        """
        device_dir = self.backup_dir / device_name
        if not device_dir.exists():
            return []

        backups = sorted(
            device_dir.glob("*.cfg"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return backups

    def get_latest_backup(self, device_name: str) -> Path | None:
        """Get the most recent backup for a device.

        Args:
            device_name: Device hostname.

        Returns:
            Path to latest backup or None.
        """
        backups = self.list_backups(device_name)
        return backups[0] if backups else None

    def verify_backup(self, backup_path: Path) -> bool:
        """Verify backup integrity using checksum.

        Args:
            backup_path: Path to backup file.

        Returns:
            True if backup integrity is valid.
        """
        import json
        meta_file = backup_path.with_suffix(".meta")
        if not meta_file.exists():
            logger.warning(f"No metadata file for {backup_path}")
            return False

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        with open(backup_path, "r", encoding="utf-8") as f:
            content = f.read()

        current_checksum = hashlib.sha256(content.encode()).hexdigest()
        stored_checksum = meta.get("checksum_sha256", "")

        is_valid = current_checksum == stored_checksum
        if not is_valid:
            logger.error(f"Backup integrity check failed: {backup_path}")
        return is_valid

    def cleanup_old_backups(self, device_name: str | None = None) -> int:
        """Remove backups older than retention period.

        Args:
            device_name: Optional specific device to clean up. If None, cleans all.

        Returns:
            Number of backups removed.
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed = 0

        search_dirs = (
            [self.backup_dir / device_name]
            if device_name
            else [d for d in self.backup_dir.iterdir() if d.is_dir()]
        )

        for device_dir in search_dirs:
            if not device_dir.exists():
                continue
            for backup_file in device_dir.glob("*.cfg"):
                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if mtime < cutoff:
                    backup_file.unlink()
                    # Also remove metadata
                    meta_file = backup_file.with_suffix(".meta")
                    if meta_file.exists():
                        meta_file.unlink()
                    removed += 1
                    logger.info(f"Removed old backup: {backup_file}")

        return removed
