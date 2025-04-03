import os
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class FileEncryptor:
    def __init__(self):
        # Use a strong salt from environment or generate a secure one
        self.salt = os.getenv('ENCRYPTION_SALT', os.urandom(16)).encode()
    
    def _generate_key(self, password: str = None):
        """
        Generate an encryption key using PBKDF2
        
        :param password: Optional password, uses a system-generated key if not provided
        :return: URL-safe base64 encoded encryption key
        """
        if not password:
            password = os.getenv('FILE_ENCRYPTION_KEY', os.urandom(32).hex())
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt_data(self, data: bytes, password: str = None) -> bytes:
        """
        Encrypt file data
        
        :param data: File content as bytes
        :param password: Optional encryption password
        :return: Encrypted bytes
        """
        key = self._generate_key(password)
        f = Fernet(key)
        return f.encrypt(data)

    def decrypt_data(self, encrypted_data: bytes, password: str = None) -> bytes:
        """
        Decrypt file data
        
        :param encrypted_data: Encrypted file content
        :param password: Optional decryption password
        :return: Decrypted bytes
        """
        key = self._generate_key(password)
        f = Fernet(key)
        return f.decrypt(encrypted_data)

    def hash_data(self, data: bytes) -> str:
        """
        Generate SHA-256 hash of data
        
        :param data: File content as bytes
        :return: Hexadecimal hash string
        """
        return hashlib.sha256(data).hexdigest()