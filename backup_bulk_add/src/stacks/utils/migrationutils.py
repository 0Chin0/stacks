import logging
import shutil
from pathlib import Path
from typing import Tuple, List

logger = logging.getLogger('migration')

def migrate_incomplete_folder(old_path: Path, new_path: Path) -> Tuple[bool, str, dict]:
    """
    Migrate .part files from old incomplete folder to new incomplete folder.
    """
    stats = {
        'files_found': 0,
        'files_migrated': 0,
        'files_failed': 0,
        'files_left': 0,
        'bytes_migrated': 0,
        'errors': []
    }

    try:
        # Validate paths
        if not old_path.exists():
            logger.warning(f"Old incomplete path does not exist: {old_path}")
            # Not an error - might be first time setup
            old_path = None

        if old_path and not old_path.is_dir():
            return False, f"Old path is not a directory: {old_path}", stats

        # Create new directory
        try:
            new_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created new incomplete directory: {new_path}")
        except Exception as e:
            logger.error(f"Failed to create new incomplete directory: {e}")
            return False, f"Failed to create new directory: {str(e)}", stats

        # If old path doesn't exist or is the same as new path, nothing to migrate
        if not old_path or old_path.resolve() == new_path.resolve():
            logger.info("No migration needed (paths are the same or old path doesn't exist)")
            return True, "No migration needed", stats

        # Find all .part files
        part_files: List[Path] = []
        try:
            part_files = list(old_path.glob('*.part'))
            stats['files_found'] = len(part_files)
            logger.info(f"Found {len(part_files)} .part files to migrate")
        except Exception as e:
            logger.error(f"Failed to scan old incomplete directory: {e}")
            return False, f"Failed to scan old directory: {str(e)}", stats

        if not part_files:
            logger.info("No .part files to migrate")
            return True, "No .part files found to migrate", stats

        # Migrate each .part file
        migrated_files = []
        for part_file in part_files:
            try:
                dest_file = new_path / part_file.name
                file_size = part_file.stat().st_size

                # Copy file
                logger.debug(f"Copying {part_file.name} to {dest_file}")
                shutil.copy2(part_file, dest_file)

                # Verify copy succeeded
                if dest_file.exists() and dest_file.stat().st_size == file_size:
                    migrated_files.append(part_file)
                    stats['files_migrated'] += 1
                    stats['bytes_migrated'] += file_size
                    logger.debug(f"Successfully copied {part_file.name}")
                else:
                    stats['files_failed'] += 1
                    error_msg = f"Copy verification failed for {part_file.name}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg)

            except Exception as e:
                stats['files_failed'] += 1
                error_msg = f"Failed to migrate {part_file.name}: {str(e)}"
                stats['errors'].append(error_msg)
                logger.error(error_msg)

        # Delete successfully migrated files from old location
        for part_file in migrated_files:
            try:
                part_file.unlink()
                logger.debug(f"Deleted {part_file.name} from old location")
            except Exception as e:
                logger.warning(f"Failed to delete {part_file.name} from old location: {e}")

        # Count files left in old directory
        try:
            remaining_files = list(old_path.iterdir())
            stats['files_left'] = len(remaining_files)
            if remaining_files:
                logger.info(f"{len(remaining_files)} files remain in old incomplete directory")
        except Exception as e:
            logger.warning(f"Failed to count remaining files: {e}")

        # Success if we migrated at least some files, or there were no files to migrate
        if stats['files_failed'] == 0:
            logger.info(f"Migration completed successfully: {stats['files_migrated']} files migrated")
            return True, f"Successfully migrated {stats['files_migrated']} file(s)", stats
        elif stats['files_migrated'] > 0:
            logger.warning(f"Migration partially completed: {stats['files_migrated']} succeeded, {stats['files_failed']} failed")
            return False, f"Partial migration: {stats['files_migrated']} succeeded, {stats['files_failed']} failed", stats
        else:
            logger.error(f"Migration failed: {stats['files_failed']} files failed to migrate")
            return False, f"Migration failed: {stats['files_failed']} file(s) failed", stats

    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}", exc_info=True)
        return False, f"Migration failed: {str(e)}", stats
