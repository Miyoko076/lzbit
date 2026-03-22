import secrets
import base64
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet, InvalidToken

class CryptoManager:
    def _get_fernet(self, secret_string: str, salt: bytes) -> Fernet:
        """Generates a secure Fernet object using PBKDF2HMAC with the provided secret string and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000, 
        )
        aes_key = base64.urlsafe_b64encode(kdf.derive(secret_string.encode('utf-8')))
        return Fernet(aes_key)

    def encrypt_and_save(self, raw_data: bytes, secret_string: str, save_path: str | Path):
        """Encrypts the raw data using the secret string and saves it to the specified path."""
        if len(raw_data) != 32:
            raise ValueError(f"Expected 32 bytes of raw_data, got {len(raw_data)} bytes.")

        salt = secrets.token_bytes(16)
        fernet = self._get_fernet(secret_string, salt)
        
        encrypted_data = fernet.encrypt(raw_data)
        
        del raw_data

        Path(save_path).write_bytes(salt + encrypted_data)

    def load_and_decrypt(self, file_path: str | Path, secret_string: str) -> bytes:
        """Loads the encrypted file, extracts the salt, and decrypts the raw data using the secret string."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Encrypted file not found: {file_path}")

        data = path.read_bytes()
        
        if len(data) < 16:
            raise ValueError("Corrupted file: Data is too short to contain a valid salt.")
            
        salt = data[:16]
        encrypted_data = data[16:]
        
        fernet = self._get_fernet(secret_string, salt)
        
        try:
            decrypted_raw_data = fernet.decrypt(encrypted_data)
            return decrypted_raw_data
        except InvalidToken:
            raise ValueError("Decryption failed. Invalid secret string, incorrect key combination, or corrupted file.")