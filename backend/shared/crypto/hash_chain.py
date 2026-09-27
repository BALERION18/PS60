"""Black-box hash chain utilities for VajraX.

Each BlackBoxFrame in a critical event window is hash-chained:
  - frame_hash = SHA-256(serialized frame bytes, excluding frame_hash field)
  - prev_hash of frame N = frame_hash of frame N-1
  - prev_hash of frame 0 = SHA-256(trigger_alert_id.encode("utf-8"))

This creates a tamper-evident chain: modifying any frame invalidates all
subsequent frames' prev_hash values, making tampering detectable.

Usage:
    from shared.crypto.hash_chain import compute_frame_hash, verify_chain

    # When writing a frame:
    frame_bytes = serialize_frame_without_hash(frame)
    frame.frame_hash = compute_frame_hash(frame_bytes)

    # When verifying integrity:
    is_valid = verify_chain(frames)
"""
from __future__ import annotations

import hashlib


def sha256(data: bytes) -> bytes:
    """Compute SHA-256 hash of data, returning 32 raw bytes."""
    return hashlib.sha256(data).digest()


def initial_prev_hash(trigger_alert_id: str) -> bytes:
    """Compute the prev_hash for the first frame in a black-box window.

    The first frame's prev_hash anchors the chain to the triggering alert ID.
    SHA-256(trigger_alert_id.encode("utf-8"))
    """
    return sha256(trigger_alert_id.encode("utf-8"))


def compute_frame_hash(frame_bytes_without_hash: bytes) -> bytes:
    """Compute the frame_hash for a black-box frame.

    Args:
        frame_bytes_without_hash: The serialized Protobuf bytes of the frame
            with the frame_hash field set to b"" (empty bytes / zero bytes).
            The caller is responsible for serializing the frame without the hash.

    Returns:
        32 bytes: SHA-256 of the frame content.
    """
    return sha256(frame_bytes_without_hash)


def verify_chain(frames: list[dict]) -> tuple[bool, str]:
    """Verify the hash chain integrity of a list of black-box frames.

    Args:
        frames: List of dicts with keys:
            - frame_index (int)
            - trigger_alert_id (str) — only used for frame 0
            - prev_hash (bytes)
            - frame_hash (bytes)
            - frame_bytes_without_hash (bytes) — frame serialized without frame_hash

    Returns:
        (is_valid: bool, reason: str)
        reason is empty string if valid, or describes the first failure.
    """
    if not frames:
        return True, ""

    # Sort by frame_index to ensure order
    frames = sorted(frames, key=lambda f: f["frame_index"])

    for i, frame in enumerate(frames):
        # 1. Check frame_index is sequential
        if frame["frame_index"] != i:
            return False, (
                f"Frame index gap: expected {i}, got {frame['frame_index']}. "
                "Frames may have been deleted."
            )

        # 2. Verify prev_hash
        if i == 0:
            expected_prev = initial_prev_hash(frame["trigger_alert_id"])
        else:
            expected_prev = frames[i - 1]["frame_hash"]

        if frame["prev_hash"] != expected_prev:
            return False, (
                f"Frame {i}: prev_hash mismatch. "
                f"Expected {expected_prev.hex()!r}, got {frame['prev_hash'].hex()!r}. "
                "Chain integrity violated — possible tampering."
            )

        # 3. Verify frame_hash
        expected_hash = compute_frame_hash(frame["frame_bytes_without_hash"])
        if frame["frame_hash"] != expected_hash:
            return False, (
                f"Frame {i}: frame_hash mismatch. "
                f"Expected {expected_hash.hex()!r}, got {frame['frame_hash'].hex()!r}. "
                "Frame content has been modified."
            )

    return True, ""
