import os
import zipfile
import datetime
import shutil
import hashlib

# === CONFIG ===

LIBRARIES = {
    "books": r"C:\Users\user\Books Library",
    "manga": r"C:\Users\user\Manga Library",
}

BACKUP_DIR = r"C:\Users\user\calibrebackups"

# How many "recent" backups to keep (non-monthly), per library
MAX_RECENT_BACKUPS = 1

# How many monthly snapshots to keep (per library)
MAX_MONTHLY_SNAPSHOTS = 12  # 1 year of monthlies


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def compute_library_fingerprint(library_dir: str) -> str:
    """
    Build a fingerprint of the library based on file paths, sizes, and mtimes.
    We DON'T hash full file contents to keep it fast.
    """
    hasher = hashlib.sha256()

    for root, dirs, files in os.walk(library_dir):
        # Sort to make traversal deterministic
        dirs.sort()
        files.sort()
        for file in files:
            full_path = os.path.join(root, file)
            try:
                stat = os.stat(full_path)
            except FileNotFoundError:
                # File disappeared between walk and stat; skip it
                continue
            rel_path = os.path.relpath(full_path, library_dir)
            size = stat.st_size
            mtime = int(stat.st_mtime)

            entry = f"{rel_path}|{size}|{mtime}\n"
            hasher.update(entry.encode("utf-8"))

    return hasher.hexdigest()


def state_file_for_prefix(prefix: str) -> str:
    return os.path.join(BACKUP_DIR, f"{prefix}_library_state.txt")


def has_library_changed(prefix: str, library_dir: str) -> bool:
    """
    Compare current fingerprint with last stored fingerprint.
    Returns True if changed or state file missing.
    """
    current = compute_library_fingerprint(library_dir)
    state_path = state_file_for_prefix(prefix)

    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            old = f.read().strip()
        if old == current:
            print(f"[{prefix}] No changes detected since last backup. Skipping.")
            return False

    # Either no state file or fingerprint differs
    with open(state_path, "w", encoding="utf-8") as f:
        f.write(current)
    print(f"[{prefix}] Changes detected. Proceeding with backup.")
    return True


def create_backup_zip(prefix, library_dir):
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"{prefix}_library_{timestamp}.zip"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    print(f"[{prefix}] Creating backup: {backup_path}")

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(library_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, library_dir)
                zf.write(full_path, rel_path)

    print(f"[{prefix}] Backup created.")
    return backup_path


def ensure_monthly_snapshot(prefix, latest_backup_path):
    """
    Keep one 'monthly' snapshot per calendar month per library:
    e.g. books_library_YYYY-MM_monthly.zip
         manga_library_YYYY-MM_monthly.zip
    """
    now = datetime.datetime.now()
    month_tag = now.strftime("%Y-%m")
    monthly_name = f"{prefix}_library_{month_tag}_monthly.zip"
    monthly_path = os.path.join(BACKUP_DIR, monthly_name)

    if not os.path.exists(monthly_path):
        print(f"[{prefix}] No monthly snapshot for {month_tag} found. Creating one...")
        shutil.copy2(latest_backup_path, monthly_path)
        print(f"[{prefix}] Monthly snapshot created: {monthly_path}")
    else:
        print(f"[{prefix}] Monthly snapshot for {month_tag} already exists. Skipping.")


def prune_backups_for_prefix(prefix):
    """
    Prune backups for a single library (prefix).
    Keeps:
      - last MAX_RECENT_BACKUPS "recent" backups
      - last MAX_MONTHLY_SNAPSHOTS monthly backups
    """
    all_files = [
        f for f in os.listdir(BACKUP_DIR)
        if f.lower().endswith(".zip") and f.startswith(f"{prefix}_library_")
    ]
    full_paths = [os.path.join(BACKUP_DIR, f) for f in all_files]

    recent = [p for p in full_paths if "_monthly" not in os.path.basename(p)]
    monthly = [p for p in full_paths if "_monthly" in os.path.basename(p)]

    recent.sort()
    monthly.sort()

    # Prune recent
    if len(recent) > MAX_RECENT_BACKUPS:
        to_delete = recent[:-MAX_RECENT_BACKUPS]
        for path in to_delete:
            print(f"[{prefix}] Deleting old backup: {path}")
            os.remove(path)

    # Prune monthly
    if len(monthly) > MAX_MONTHLY_SNAPSHOTS:
        to_delete = monthly[:-MAX_MONTHLY_SNAPSHOTS]
        for path in to_delete:
            print(f"[{prefix}] Deleting old monthly snapshot: {path}")
            os.remove(path)


def main():
    ensure_backup_dir()

    for prefix, library_dir in LIBRARIES.items():
        if not os.path.isdir(library_dir):
            print(f"[{prefix}] WARNING: Library dir does not exist: {library_dir}, skipping.")
            continue

        # Only back up if something changed
        if not has_library_changed(prefix, library_dir):
            continue

        latest_backup = create_backup_zip(prefix, library_dir)
        ensure_monthly_snapshot(prefix, latest_backup)
        prune_backups_for_prefix(prefix)

    print("Backup routine complete for all libraries.")


if __name__ == "__main__":
    main()

