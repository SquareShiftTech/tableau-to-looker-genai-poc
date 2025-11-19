"""Utility script to move existing chunk files to the chunks directory."""

import shutil
from pathlib import Path
from workflow.config import CHUNKS_DIR, PROJECT_ROOT


def move_chunks():
    """Move all chunk files from project root to chunks directory."""
    print("=" * 80)
    print("MOVING CHUNK FILES TO chunks/ DIRECTORY")
    print("=" * 80)
    print()
    
    # Ensure chunks directory exists
    CHUNKS_DIR.mkdir(exist_ok=True)
    
    # Find all chunk files in project root
    root = Path(PROJECT_ROOT)
    chunk_patterns = [
        "chunk_*_connection.json",
        "chunk_*_fields_*.json",
        "chunk_worksheet_batch_*.json",
        "chunk_dashboard_batch_*.json"
    ]
    
    moved_count = 0
    skipped_count = 0
    
    for pattern in chunk_patterns:
        chunk_files = list(root.glob(pattern))
        for chunk_file in chunk_files:
            # Skip if already in chunks directory
            if chunk_file.parent == CHUNKS_DIR:
                continue
            
            dest = CHUNKS_DIR / chunk_file.name
            
            # Check if file already exists in destination
            if dest.exists():
                print(f"⚠️  Skipping {chunk_file.name} (already exists in chunks/)")
                skipped_count += 1
            else:
                try:
                    shutil.move(str(chunk_file), str(dest))
                    print(f"✓ Moved: {chunk_file.name}")
                    moved_count += 1
                except Exception as e:
                    print(f"✗ Error moving {chunk_file.name}: {e}")
    
    print()
    print("=" * 80)
    print(f"MOVED {moved_count} file(s)")
    if skipped_count > 0:
        print(f"SKIPPED {skipped_count} file(s) (already in chunks/)")
    print("=" * 80)
    
    # Verify chunks directory
    all_chunks = (
        list(CHUNKS_DIR.glob("chunk_*_connection.json")) +
        list(CHUNKS_DIR.glob("chunk_*_fields_*.json")) +
        list(CHUNKS_DIR.glob("chunk_worksheet_batch_*.json")) +
        list(CHUNKS_DIR.glob("chunk_dashboard_batch_*.json"))
    )
    
    print(f"\nTotal chunk files in chunks/: {len(all_chunks)}")


if __name__ == "__main__":
    move_chunks()

