"""Ed25519 cryptographic signing and verification for VajraX sync envelopes.

Every message leaving the Edge is signed with the station's Ed25519 private key.
The Cloud receiver verifies the signature before processing any payload.
This provides:
  - Authenticity: the message came from the station that claims to have sent it.
  - Integrity: the payload was not modified in transit.

Key files are loaded from the filesystem at service startup.
In production, these would be stored in a hardware security module (HSM).
For the prototype, they are filesystem-secured PEM files.

Usage:
    from shared.crypto.signing import Signer, Verifier

    # At the Edge (startup):
    signer = Signer.from_pem_file("/etc/vajrax/certs/maitri.key")
    signature = signer.sign(payload_bytes)

    # At the Cloud receiver:
    verifier = Verifier.from_pem_file("/etc/vajrax/certs/maitri.pub")
    verifier.verify(payload_bytes, signature)  # raises if invalid
"""
from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
    load_pem_public_key,
)


class SigningError(Exception):
    """Raised when signing fails."""


class VerificationError(Exception):
    """Raised when signature verification fails — payload must be rejected."""


class Signer:
    """Signs payloads with an Ed25519 private key."""

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._key = private_key

    @classmethod
    def from_pem_file(cls, path: str, password: bytes | None = None) -> "Signer":
        """Load an Ed25519 private key from a PEM file.

        Args:
            path: Absolute path to the PEM-encoded private key file.
            password: Optional password bytes if the key is encrypted.
        """
        with open(path, "rb") as f:
            pem_data = f.read()
        key = load_pem_private_key(pem_data, password=password)
        if not isinstance(key, Ed25519PrivateKey):
            raise SigningError(f"Key at {path!r} is not an Ed25519 private key.")
        return cls(key)

    @classmethod
    def from_pem_bytes(cls, pem_data: bytes, password: bytes | None = None) -> "Signer":
        """Load an Ed25519 private key from PEM bytes."""
        key = load_pem_private_key(pem_data, password=password)
        if not isinstance(key, Ed25519PrivateKey):
            raise SigningError("Provided key is not an Ed25519 private key.")
        return cls(key)

    def sign(self, payload: bytes) -> bytes:
        """Sign the payload and return the 64-byte Ed25519 signature.

        Args:
            payload: The raw bytes to sign. For SyncEnvelopes, this is the
                     uncompressed serialized inner message bytes.

        Returns:
            64-byte Ed25519 signature.
        """
        return self._key.sign(payload)

    def public_key_pem(self) -> bytes:
        """Export the corresponding public key as PEM bytes."""
        return self._key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)


class Verifier:
    """Verifies Ed25519 signatures from a known public key."""

    def __init__(self, public_key: Ed25519PublicKey) -> None:
        self._key = public_key

    @classmethod
    def from_pem_file(cls, path: str) -> "Verifier":
        """Load an Ed25519 public key from a PEM file."""
        with open(path, "rb") as f:
            pem_data = f.read()
        key = load_pem_public_key(pem_data)
        if not isinstance(key, Ed25519PublicKey):
            raise VerificationError(f"Key at {path!r} is not an Ed25519 public key.")
        return cls(key)

    @classmethod
    def from_pem_bytes(cls, pem_data: bytes) -> "Verifier":
        """Load an Ed25519 public key from PEM bytes."""
        key = load_pem_public_key(pem_data)
        if not isinstance(key, Ed25519PublicKey):
            raise VerificationError("Provided key is not an Ed25519 public key.")
        return cls(key)

    def verify(self, payload: bytes, signature: bytes) -> None:
        """Verify that the signature is valid for the given payload.

        Args:
            payload: The original uncompressed payload bytes.
            signature: The 64-byte Ed25519 signature from the SyncEnvelope.

        Raises:
            VerificationError: If the signature is invalid. The caller MUST
                               reject the payload and log the incident.
        """
        try:
            self._key.verify(signature, payload)
        except InvalidSignature as exc:
            raise VerificationError(
                "Ed25519 signature verification FAILED — payload rejected. "
                "This may indicate tampering or a misconfigured station key."
            ) from exc


def generate_station_keypair() -> tuple[bytes, bytes]:
    """Generate a new Ed25519 keypair for a station.

    Returns:
        (private_key_pem, public_key_pem) as bytes.

    NOTE: For production, key generation should happen on station hardware
    and private keys should never leave the device. This function is provided
    for dev/test use and initial station provisioning only.
    """
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    return private_pem, public_pem
