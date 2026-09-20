"""Backup utility: Creates a rollback snapshot of the stable Phase 1 platform."""
import shutil
import os
from pathlib import Path

def create_backup():
    base_dir = Path(__file__).resolve().parent.parent
    backup_dir = base_dir / "backups" / "phase1_v1.2_stable"
    backup_dir.mkdir(parents=True, exist_ok=True)

    items_to_backup = [
        ("backend/app", backup_dir / "backend" / "app"),
        ("frontend/dist", backup_dir / "frontend" / "dist"),
        (".agents/skills", backup_dir / ".agents" / "skills"),
        ("build_guided_frontend.py", backup_dir / "build_guided_frontend.py")
    ]

    for src_rel, dst_path in items_to_backup:
        src_path = base_dir / src_rel
        if src_path.exists():
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
            print(f"[OK] Backed up {src_rel} -> {dst_path}")

    print(f"\n[SUCCESS] Snapshot created successfully at: {backup_dir}")

if __name__ == "__main__":
    create_backup()
