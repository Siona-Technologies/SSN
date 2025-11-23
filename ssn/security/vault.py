import os
import json
from cryptography.fernet import Fernet


class Vault:
    """
    Encrypted vault for Samson's most sensitive data.
    Stores:
        - private notes
        - PINs
        - API keys
        - crypto keys
        - secrets
    """

    def __init__(self, key_path="data/vault_master.key", vault_path="data/secret_vault.json"):
        self.key_path = key_path
        self.vault_path = vault_path

        os.makedirs("data", exist_ok=True)

        if not os.path.exists(key_path):
            self.master_key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(self.master_key)
        else:
            with open(key_path, "rb") as f:
                self.master_key = f.read()

        self.fernet = Fernet(self.master_key)

        if not os.path.exists(vault_path):
            with open(vault_path, "w") as f:
                json.dump({}, f)

    def store(self, label: str, value: str):
        """Store encrypted value in the vault."""
        encrypted = self.fernet.encrypt(value.encode())
        data = self._load_vault()
        data[label] = encrypted.decode()
        self._save_vault(data)
        return True

    def retrieve(self, label: str):
        """Retrieve and decrypt value."""
        data = self._load_vault()
        if label not in data:
            return None
        encrypted = data[label].encode()
        return self.fernet.decrypt(encrypted).decode()

    def delete(self, label: str):
        data = self._load_vault()
        if label in data:
            del data[label]
            self._save_vault(data)
            return True
        return False

    def _load_vault(self):
        with open(self.vault_path, "r") as f:
            return json.load(f)

    def _save_vault(self, data):
        with open(self.vault_path, "w") as f:
            json.dump(data, f, indent=4)
