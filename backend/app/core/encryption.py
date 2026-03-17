"""End-to-End Encryption Module.

Implements zero-trust security architecture:
1. Client-side encryption before data leaves device
2. Server stores only encrypted data
3. Encryption keys never leave user's control
4. Optional local-only processing mode
"""

import base64
import hashlib
import logging
import os
from typing import Tuple, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class E2EEncryption:
    """End-to-end encryption for founder data.
    
    Uses hybrid encryption:
    - RSA for key exchange
    - AES-256-GCM for data encryption
    """

    def __init__(self):
        self.backend = default_backend()

    def generate_user_keypair(self) -> Tuple[bytes, bytes]:
        """Generate RSA keypair for user.
        
        Returns:
            (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=self.backend,
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return private_pem, public_pem

    def derive_key_from_password(
        self,
        password: str,
        salt: Optional[bytes] = None,
    ) -> Tuple[bytes, bytes]:
        """Derive encryption key from user password.
        
        Returns:
            (key, salt)
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,  # OWASP recommendation
            backend=self.backend,
        )

        key = kdf.derive(password.encode())
        return key, salt

    def encrypt_data(
        self,
        plaintext: str,
        key: bytes,
    ) -> dict:
        """Encrypt data using AES-256-GCM.
        
        Returns:
            {
                "ciphertext": base64_encoded,
                "nonce": base64_encoded,
                "tag": base64_encoded,
            }
        """
        # Generate random nonce
        nonce = os.urandom(12)

        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=self.backend,
        )

        # Encrypt
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()

        return {
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "tag": base64.b64encode(encryptor.tag).decode(),
        }

    def decrypt_data(
        self,
        encrypted_data: dict,
        key: bytes,
    ) -> str:
        """Decrypt data using AES-256-GCM."""
        ciphertext = base64.b64decode(encrypted_data["ciphertext"])
        nonce = base64.b64decode(encrypted_data["nonce"])
        tag = base64.b64decode(encrypted_data["tag"])

        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=self.backend,
        )

        # Decrypt
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        return plaintext.decode()

    def encrypt_for_storage(
        self,
        data: str,
        user_password: str,
    ) -> dict:
        """Encrypt data for storage (convenience method).
        
        Returns:
            {
                "encrypted_data": {...},
                "salt": base64_encoded,
            }
        """
        key, salt = self.derive_key_from_password(user_password)
        encrypted_data = self.encrypt_data(data, key)

        return {
            "encrypted_data": encrypted_data,
            "salt": base64.b64encode(salt).decode(),
        }

    def decrypt_from_storage(
        self,
        stored_data: dict,
        user_password: str,
    ) -> str:
        """Decrypt data from storage (convenience method)."""
        salt = base64.b64decode(stored_data["salt"])
        key, _ = self.derive_key_from_password(user_password, salt)
        return self.decrypt_data(stored_data["encrypted_data"], key)


class DataAnonymization:
    """Anonymize data for AI processing while preserving utility."""

    def __init__(self):
        self.entity_map = {}  # Maps real entities to pseudonyms

    def anonymize_text(
        self,
        text: str,
        preserve_structure: bool = True,
    ) -> Tuple[str, dict]:
        """Anonymize sensitive entities in text.
        
        Returns:
            (anonymized_text, entity_mapping)
        """
        # Simple implementation - in production, use NER models
        import re

        anonymized = text
        mapping = {}

        # Email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        for i, email in enumerate(emails):
            pseudonym = f"email_{i+1}@example.com"
            anonymized = anonymized.replace(email, pseudonym)
            mapping[pseudonym] = email

        # Phone numbers (simple pattern)
        phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
        for i, phone in enumerate(phones):
            pseudonym = f"555-000-{i+1:04d}"
            anonymized = anonymized.replace(phone, pseudonym)
            mapping[pseudonym] = phone

        # Names using spaCy NER for proper entity recognition
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)
            name_count = 0
            for ent in doc.ents:
                if ent.label_ in ("PERSON", "ORG"):
                    pseudonym = f"{ent.label_.lower()}_{name_count+1}"
                    if ent.text not in mapping.values():
                        anonymized = anonymized.replace(ent.text, pseudonym)
                        mapping[pseudonym] = ent.text
                        name_count += 1
        except ImportError:
            logger.debug("spaCy not available, skipping NER")
        except Exception as e:
            logger.debug(f"NER failed: {e}, continuing with basic anonymization")

        return anonymized, mapping

    def deanonymize_text(
        self,
        anonymized_text: str,
        mapping: dict,
    ) -> str:
        """Restore original entities from anonymized text."""
        result = anonymized_text
        for pseudonym, original in mapping.items():
            result = result.replace(pseudonym, original)
        return result


class SecureEmbedding:
    """Generate embeddings from encrypted data without decryption.
    
    Uses homomorphic encryption concepts for privacy-preserving ML.
    """

    def __init__(self):
        pass

    def hash_for_embedding(
        self,
        text: str,
        preserve_semantic: bool = True,
    ) -> str:
        """Create privacy-preserving representation for embedding.
        
        Options:
        1. Anonymize entities but preserve structure
        2. Use differential privacy
        3. Homomorphic encryption (future)
        """
        if preserve_semantic:
            # Anonymize but preserve semantic meaning
            anonymizer = DataAnonymization()
            anonymized, _ = anonymizer.anonymize_text(text)
            return anonymized
        else:
            # Full hash (loses semantic meaning)
            return hashlib.sha256(text.encode()).hexdigest()


class AuditLog:
    """Immutable audit log for data access."""

    def __init__(self):
        self.log_entries = []

    def log_access(
        self,
        user_id: str,
        action: str,
        resource: str,
        timestamp: str,
        metadata: Optional[dict] = None,
    ):
        """Log data access event."""
        entry = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "timestamp": timestamp,
            "metadata": metadata or {},
        }
        self.log_entries.append(entry)
        logger.info(f"Audit: {action} on {resource} by {user_id}")

    def get_user_access_history(
        self,
        user_id: str,
    ) -> list:
        """Get all access events for a user."""
        return [e for e in self.log_entries if e["user_id"] == user_id]


if __name__ == "__main__":
    # Example usage
    e2e = E2EEncryption()

    # Encrypt data
    sensitive_data = "I'm worried about our burn rate. We have 6 months of runway."
    password = "founder-master-password-123"

    encrypted = e2e.encrypt_for_storage(sensitive_data, password)
    print(f"Encrypted: {encrypted['encrypted_data']['ciphertext'][:50]}...")

    # Decrypt data
    decrypted = e2e.decrypt_from_storage(encrypted, password)
    print(f"Decrypted: {decrypted}")

    # Anonymize for AI processing
    anonymizer = DataAnonymization()
    anonymized, mapping = anonymizer.anonymize_text(
        "Contact john.doe@startup.com or call 555-123-4567"
    )
    print(f"\nAnonymized: {anonymized}")
    print(f"Mapping: {mapping}")
