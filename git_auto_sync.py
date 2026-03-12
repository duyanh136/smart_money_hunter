import os
import time
import subprocess
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitSyncHandler(FileSystemEventHandler):
    def __init__(self, debounce_seconds=10):
        self.debounce_seconds = debounce_seconds
        self.last_modified_time = 0
        self.pending_sync = False

    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Skip internal/ignored files
        path = event.src_path.replace("\\", "/")
        if "/.git/" in path or "/__pycache__/" in path or "/.env" in path or "/.tcbs_token" in path:
            return
            
        logger.info(f"Detected change in: {event.src_path}")
        self.last_modified_time = time.time()
        self.pending_sync = True

    def on_created(self, event):
        self.on_modified(event)

    def on_deleted(self, event):
        self.on_modified(event)

def sync_to_github():
    try:
        logger.info("Starting sync to GitHub...")
        
        status = subprocess.check_output(["C:/Program Files/Git/cmd/git.exe", "status", "--porcelain"], shell=True).decode().strip()
        if not status:
            logger.info("No changes to sync.")
            return

        # Git operations
        subprocess.run(["C:/Program Files/Git/cmd/git.exe", "add", "."], shell=True, check=True)
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"Auto-sync: {timestamp}"
        subprocess.run(["C:/Program Files/Git/cmd/git.exe", "commit", "-m", commit_msg], shell=True, check=True)
        
        subprocess.run(["C:/Program Files/Git/cmd/git.exe", "push", "origin", "main"], shell=True, check=True)
        logger.info(f"Sync successful: {commit_msg}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}")
    except Exception as e:
        logger.error(f"Sync error: {e}")

if __name__ == "__main__":
    path = "."
    handler = GitSyncHandler(debounce_seconds=10)
    observer = Observer()
    observer.schedule(handler, path, recursive=True)
    observer.start()
    
    logger.info("Sync service started. Watching for changes...")
    
    try:
        while True:
            # Check for pending sync with debounce
            if handler.pending_sync:
                if time.time() - handler.last_modified_time > handler.debounce_seconds:
                    handler.pending_sync = False
                    sync_to_github()
            
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
