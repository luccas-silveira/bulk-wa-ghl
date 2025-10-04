"""
Unit tests for TokenEncryptionService
"""
import pytest
import os
from cryptography.fernet import Fernet
from src.services.token_encryption_service import TokenEncryptionService


class TestTokenEncryptionService:
    """Test suite for TokenEncryptionService"""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up test encryption key in environment"""
        # Generate a valid test key
        test_key = Fernet.generate_key().decode()
        monkeypatch.setenv("GHL_TOKEN_ENCRYPTION_KEY", test_key)

    def test_service_initialization(self):
        """Test service can be initialized with valid key"""
        service = TokenEncryptionService()
        assert service.cipher is not None

    def test_service_initialization_without_key(self, monkeypatch):
        """Test service raises error when encryption key is missing"""
        monkeypatch.delenv("GHL_TOKEN_ENCRYPTION_KEY", raising=False)

        with pytest.raises(ValueError) as exc_info:
            TokenEncryptionService()

        assert "GHL_TOKEN_ENCRYPTION_KEY environment variable is not set" in str(exc_info.value)

    def test_service_initialization_with_invalid_key(self, monkeypatch):
        """Test service raises error with invalid encryption key"""
        monkeypatch.setenv("GHL_TOKEN_ENCRYPTION_KEY", "invalid_key_123")

        with pytest.raises(ValueError) as exc_info:
            TokenEncryptionService()

        assert "Invalid encryption key format" in str(exc_info.value)

    def test_encrypt_token(self):
        """Test encrypting a token"""
        service = TokenEncryptionService()
        token = "test_access_token_12345"

        encrypted = service.encrypt(token)

        assert isinstance(encrypted, bytes)
        assert encrypted != token.encode()  # Should be different from plain text

    def test_decrypt_token(self):
        """Test decrypting a token"""
        service = TokenEncryptionService()
        original_token = "test_access_token_12345"

        encrypted = service.encrypt(original_token)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original_token

    def test_encrypt_decrypt_roundtrip(self):
        """Test full encryption/decryption roundtrip"""
        service = TokenEncryptionService()
        test_tokens = [
            "short",
            "a_longer_access_token_with_special_chars_!@#$%",
            "ghl_Hashed9182y3hjdkas8d7asd89a7sd89a7sd",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ]

        for token in test_tokens:
            encrypted = service.encrypt(token)
            decrypted = service.decrypt(encrypted)
            assert decrypted == token, f"Roundtrip failed for token: {token}"

    def test_encrypt_empty_token(self):
        """Test encrypting empty token raises error"""
        service = TokenEncryptionService()

        with pytest.raises(ValueError) as exc_info:
            service.encrypt("")

        assert "Token cannot be empty" in str(exc_info.value)

    def test_encrypt_non_string_token(self):
        """Test encrypting non-string token raises error"""
        service = TokenEncryptionService()

        with pytest.raises(ValueError) as exc_info:
            service.encrypt(12345)  # Integer instead of string

        assert "Token must be a string" in str(exc_info.value)

    def test_decrypt_empty_token(self):
        """Test decrypting empty encrypted token raises error"""
        service = TokenEncryptionService()

        with pytest.raises(ValueError) as exc_info:
            service.decrypt(b"")

        assert "Encrypted token cannot be empty" in str(exc_info.value)

    def test_decrypt_non_bytes_token(self):
        """Test decrypting non-bytes token raises error"""
        service = TokenEncryptionService()

        with pytest.raises(ValueError) as exc_info:
            service.decrypt("not_bytes")

        assert "Encrypted token must be bytes" in str(exc_info.value)

    def test_decrypt_invalid_encrypted_token(self):
        """Test decrypting invalid encrypted token raises error"""
        service = TokenEncryptionService()

        with pytest.raises(ValueError) as exc_info:
            service.decrypt(b"invalid_encrypted_data_12345")

        assert "Invalid or corrupted encrypted token" in str(exc_info.value)

    def test_decrypt_with_wrong_key(self, monkeypatch):
        """Test decrypting with different key fails"""
        # Encrypt with one key
        key1 = Fernet.generate_key().decode()
        monkeypatch.setenv("GHL_TOKEN_ENCRYPTION_KEY", key1)
        service1 = TokenEncryptionService()
        encrypted = service1.encrypt("test_token")

        # Try to decrypt with different key
        key2 = Fernet.generate_key().decode()
        monkeypatch.setenv("GHL_TOKEN_ENCRYPTION_KEY", key2)
        service2 = TokenEncryptionService()

        with pytest.raises(ValueError) as exc_info:
            service2.decrypt(encrypted)

        assert "Invalid or corrupted encrypted token" in str(exc_info.value)

    def test_generate_key(self):
        """Test generating a new encryption key"""
        key = TokenEncryptionService.generate_key()

        assert isinstance(key, str)
        assert len(key) > 0

        # Verify generated key is valid Fernet key
        try:
            Fernet(key.encode())
        except Exception:
            pytest.fail("Generated key is not a valid Fernet key")

    def test_generated_keys_are_unique(self):
        """Test that generated keys are unique"""
        key1 = TokenEncryptionService.generate_key()
        key2 = TokenEncryptionService.generate_key()

        assert key1 != key2
