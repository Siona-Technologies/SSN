from ssn.memory.semantic_store import SemanticStore
from ssn.memory.episodic_memory import EpisodicMemory
from ssn.memory.personal_profile import PersonalProfile
from ssn.memory.backups import BackupManager

# Populate some data
semantic = SemanticStore()
semantic.set("samson.favorite_language", "Python")

episodic = EpisodicMemory()
episodic.record_event("test", "Samson", {"message": "backup test event"})

profile = PersonalProfile()
profile.set_preference("theme", "dark")

# Create backup
manager = BackupManager()
backup_path = manager.create_backup(label="test")

print("Backup created at:", backup_path)
print("Available backups:", manager.list_backups())

# Load last backup content
backups = manager.list_backups()
if backups:
    last = backups[-1]
    snapshot = manager.load_backup(last)
    print("Loaded snapshot label:", snapshot["label"])
    print("Semantic in snapshot:", snapshot["semantic"])
