import os
import base64
import secrets

def generate_encryption_key(length=32):
    """
    Generate a cryptographically secure random encryption key
    
    :param length: Length of the key in bytes (default 32 bytes = 256 bits)
    :return: URL-safe base64 encoded key
    """
    # Generate random bytes
    key = secrets.token_bytes(length)
    
    # Encode to base64 for safe storage
    return base64.urlsafe_b64encode(key).decode('utf-8')

def generate_salt(length=16):
    """
    Generate a cryptographically secure random salt
    
    :param length: Length of the salt in bytes (default 16 bytes)
    :return: Hex-encoded salt
    """
    # Generate random bytes
    salt = secrets.token_bytes(length)
    
    # Encode to hex for easy storage
    return salt.hex()

# Generate and print keys
print("FILE_ENCRYPTION_KEY:", generate_encryption_key())
print("ENCRYPTION_SALT:", generate_salt())

# Optional: Write to .env file
def write_to_env_file(file_path='.env'):
    """
    Write generated keys to .env file
    """
    with open(file_path, 'a') as f:
        f.write(f"\nFILE_ENCRYPTION_KEY={generate_encryption_key()}\n")
        f.write(f"ENCRYPTION_SALT={generate_salt()}\n")

# Uncomment to write to .env file
write_to_env_file()