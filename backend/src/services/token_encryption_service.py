"""
Token Encryption Service
Handles encryption and decryption of OAuth tokens using Fernet symmetric encryption
"""
import os
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()


class TokenEncryptionService:
    """
    Service for encrypting and decrypting OAuth tokens

    Uses Fernet (symmetric encryption) from the cryptography library.
    The encryption key is loaded from the GHL_TOKEN_ENCRYPTION_KEY environment variable.

    Usage:
        service = TokenEncryptionService()
        encrypted = service.encrypt("my_access_token")
        decrypted = service.decrypt(encrypted)
    """

    def __init__(self):
        """Initialize the encryption service with key from environment"""
        encryption_key = os.getenv("GHL_TOKEN_ENCRYPTION_KEY")

        if not encryption_key:
            raise ValueError(
                "GHL_TOKEN_ENCRYPTION_KEY environment variable is not set. "
                "Generate a key using: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

        try:
            self.cipher = Fernet(encryption_key.encode())
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")

    def encrypt(self, token: str) -> bytes:
        """
        Encrypt a token string

        Args:
            token: Plain text token to encrypt

        Returns:
            Encrypted token as bytes

        Raises:
            ValueError: If token is empty or invalid
        """
        if not token:
            raise ValueError("Token cannot be empty")

        if not isinstance(token, str):
            raise ValueError("Token must be a string")

        try:
            encrypted_token = self.cipher.encrypt(token.encode())
            return encrypted_token
        except Exception as e:
            raise ValueError(f"Failed to encrypt token: {e}")

    def decrypt(self, encrypted_token: bytes) -> str:
        """
        Decrypt an encrypted token

        Args:
            encrypted_token: Encrypted token bytes

        Returns:
            Decrypted token as string

        Raises:
            ValueError: If decryption fails or token is invalid
        """
        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")

        if not isinstance(encrypted_token, bytes):
            raise ValueError("Encrypted token must be bytes")

        try:
            decrypted_token = self.cipher.decrypt(encrypted_token)
            return decrypted_token.decode()
        except InvalidToken:
            raise ValueError("Invalid or corrupted encrypted token")
        except Exception as e:
            raise ValueError(f"Failed to decrypt token: {e}")

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key

        Returns:
            Base64-encoded encryption key as string

        Note:
            This is a utility method for generating new keys.
            Store the generated key securely in GHL_TOKEN_ENCRYPTION_KEY environment variable.
        """
        return Fernet.generate_key().decode()
