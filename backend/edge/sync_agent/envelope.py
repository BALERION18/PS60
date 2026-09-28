"""SyncEnvelope — wire format for all Edge→Cloud satellite messages.

Build (at Edge):
  1. JSON-serialize the payload dict
  2. zstd-compress the JSON bytes (level 3)
  3. Ed25519-sign the compressed bytes with the station's private key
  4. Base64-encode compressed payload and signature for MQTT transport

Unpack (at Cloud receiver):
  1. Base64-decode compressed_payload and signature
  2. Verify Ed25519 signature — raises VerificationError on failure
  3. zstd-decompress → original JSON payload bytes

This module is pure-function with no asyncio or DB dependencies.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict

import zstandard as zstd

from shared.crypto.signing import Signer, VerificationError, Verifier
from shared.utils.time import utcnow

_COMPRESSOR = zstd.ZstdCompressor(level=3)
_DECOMPRESSOR = zstd.ZstdDecompressor()


def build_envelope(
    station_id: str,
    message_type: str,
    payload: Dict[str, Any],
    sequence_number: int,
    signer: Signer,
) -> Dict[str, Any]:
    """Build a signed, compressed SyncEnvelope from a payload dict.

    Args:
        station_id: Source station ("maitri" | "bharati").
        message_type: SENSOR_BATCH | ALERT | ALERT_ACK | BLACK_BOX_FRAME
                      | INVENTORY_SNAPSHOT | LINK_HEARTBEAT.
        payload: The message body — must be JSON-serializable.
        sequence_number: Monotonically increasing counter per station.
        signer: Ed25519 Signer loaded with this station's private key.

    Returns:
        A JSON-serializable dict (the SyncEnvelope).
    """
    payload_json = json.dumps(payload, default=str).encode("utf-8")
    compressed = _COMPRESSOR.compress(payload_json)
    signature = signer.sign(compressed)

    return {
        "station_id": station_id,
        "message_type": message_type,
        "sequence_number": sequence_number,
        "compressed_payload": base64.b64encode(compressed).decode("ascii"),
        "signature": base64.b64encode(signature).decode("ascii"),
        "timestamp_utc": utcnow().isoformat(),
        "payload_size_bytes": len(payload_json),
        "compressed_size_bytes": len(compressed),
    }


def unpack_envelope(
    envelope: Dict[str, Any],
    verifier: Verifier,
) -> Dict[str, Any]:
    """Verify signature and decompress a received SyncEnvelope.

    Returns:
        The original payload dict.

    Raises:
        VerificationError: If the Ed25519 signature is invalid.
        zstandard.ZstdError: If decompression fails (indicates tampering).
    """
    compressed = base64.b64decode(envelope["compressed_payload"])
    signature = base64.b64decode(envelope["signature"])
    # Raises VerificationError on failure — caller MUST reject payload
    verifier.verify(compressed, signature)
    payload_bytes = _DECOMPRESSOR.decompress(compressed)
    return json.loads(payload_bytes.decode("utf-8"))


def envelope_wire_size(envelope: Dict[str, Any]) -> int:
    """Approximate wire size of a serialized envelope in bytes."""
    return envelope.get("compressed_size_bytes", 0) + 300  # 300 = header overhead
