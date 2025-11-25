import os
import zipfile
import shutil
import subprocess  # for stopping/starting Docker container
from pathlib import Path

# === CONFIG (MAC) ===

# Local Calibre libraries on this Mac, keyed by the same prefixes
# used on your Windows backup script ("books", "manga", etc.).
# These match what you're mounting into Docker at /books
REPO_ROOT = Path(__file__).resolve().parents[1]

# Folder on your Mac where the backup zips + state files are synced
HOME = Path.home()
BACKUP_DIR = HOME / "calibrebackups"


LIBRARIES = {
    "books": REPO_ROOT / "calibre-libraries" / "Books Library",
    "manga": REPO_ROOT / "calibre-libraries" / "Manga Library",
}

# Name suffix for the *local* "last restored state" files on this Mac.
LOCAL_STATE_SUFFIX = "_library_last_restored_state.txt"

# Name of your Docker container running linuxserver/calibre
DOCKER_CONTAINER_NAME = "calibre"


def remote_state_file(prefix: str) -> str:
    """Path to the state file produced on your main PC."""
    return os.path.join(BACKUP_DIR, f"{prefix}_library_state.txt")


def local_state_file(prefix: str) -> str:
    """Path to the state file tracking what this Mac has already restored."""
    return os.path.join(BACKUP_DIR, f"{prefix}{LOCAL_STATE_SUFFIX}")


def read_state(path: str):
    """Read a state file (hash) if it exists, else None."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip() or None


def write_state(path: str, value: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(value)


def find_latest_non_monthly_backup(prefix: str):
    """
    Find the newest non-monthly backup zip for this prefix.
    Uses filename ordering, since they are of the form:
      {prefix}_library_YYYY-MM-DD_HH-MM-SS.zip
    """
    if not os.path.isdir(BACKUP_DIR):
        return None

    candidates = []
    for name in os.listdir(BACKUP_DIR):
        if not name.endswith(".zip"):
            continue
        if not name.startswith(f"{prefix}_library_"):
            continue
        if "_monthly" in name:
            # skip monthly snapshots
            continue
        candidates.append(name)

    if not candidates:
        return None

    # Lexicographic sort is fine due to timestamp format
    candidates.sort()
    latest_name = candidates[-1]
    return os.path.join(BACKUP_DIR, latest_name)


def clear_directory(dir_path: str):
    """Remove all contents of dir_path, but keep the directory itself."""
    os.makedirs(dir_path, exist_ok=True)
    for entry in os.listdir(dir_path):
        full = os.path.join(dir_path, entry)
        if os.path.isdir(full) and not os.path.islink(full):
            shutil.rmtree(full)
        else:
            os.remove(full)


def restore_library_from_backup(prefix: str, backup_path: str, library_dir: str):
    print(f"[{prefix}] Restoring from backup: {backup_path}")
    print(f"[{prefix}] Target library directory: {library_dir}")

    # Ensure library directory exists and is empty
    clear_directory(library_dir)

    # Extract the zip into the library directory
    with zipfile.ZipFile(backup_path, "r") as zf:
        zf.extractall(library_dir)

    print(f"[{prefix}] Restore complete.")


# ===== Docker container control helpers =====

def stop_calibre_container():
    """Stop the Docker container that runs Calibre."""
    print(f"Stopping Docker container '{DOCKER_CONTAINER_NAME}' (if running)...")
    # `docker stop` returns non-zero if not running; that's fine.
    subprocess.run(
        ["docker", "stop", DOCKER_CONTAINER_NAME],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("Docker container stop command issued.")


def start_calibre_container():
    """Start the Docker container that runs Calibre."""
    print(f"Starting Docker container '{DOCKER_CONTAINER_NAME}'...")
    subprocess.run(
        ["docker", "start", DOCKER_CONTAINER_NAME],
        check=False
    )
    print("Docker container start command issued.")


def main():
    if not os.path.isdir(BACKUP_DIR):
        print(f"ERROR: Backup directory does not exist: {BACKUP_DIR}")
        return

    any_restored = False  # Track whether we actually changed anything

    for prefix, library_dir in LIBRARIES.items():
        print(f"\n=== Processing library: {prefix} ===")

        remote_state_path = remote_state_file(prefix)
        local_state_path = local_state_file(prefix)

        remote_state = read_state(remote_state_path)
        if remote_state is None:
            print(f"[{prefix}] No remote state file found at {remote_state_path}. Skipping.")
            continue

        local_state = read_state(local_state_path)

        if local_state == remote_state:
            print(f"[{prefix}] No new backup detected (state unchanged).")
            continue

        print(f"[{prefix}] New backup detected (remote state != local state).")

        # First time we see a change across ANY library, stop Docker container
        if not any_restored:
            stop_calibre_container()

        latest_backup = find_latest_non_monthly_backup(prefix)
        if latest_backup is None:
            print(f"[{prefix}] No non-monthly backups found in {BACKUP_DIR}. Skipping.")
            continue

        # Restore from latest backup
        restore_library_from_backup(prefix, latest_backup, library_dir)

        # Update local "last restored" state to match remote
        write_state(local_state_path, remote_state)
        print(f"[{prefix}] Updated local restored state to match remote.")

        any_restored = True

    # If we restored anything, start the Docker container again
    if any_restored:
        start_calibre_container()
    else:
        print("\nNo libraries changed; leaving Docker container as-is.")

    print("\nAll libraries processed.")


if __name__ == "__main__":
    main()
