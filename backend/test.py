import secrets
jwt_secret = secrets.token_urlsafe(64)  # Generates a 512-bit (64-char) secure key
print(jwt_secret)