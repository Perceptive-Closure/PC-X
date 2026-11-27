"""Public domain separation and verification for the independent X17 sampling seeds."""

from hashlib import sha256
import re


def role_root(private_seed, expected_digest, beacon_randomness, frozen_commit):
    if (len(private_seed) != 32 or sha256(private_seed).hexdigest() != expected_digest
            or not re.fullmatch(r"[0-9a-f]{64}", beacon_randomness)
            or not re.fullmatch(r"[0-9a-f]{40}", frozen_commit)):
        raise ValueError("sampling seed commitment or frozen input differs")
    return sha256(b"PCX-X17-trials-v1\x00independent\x00" + bytes.fromhex(frozen_commit)
                  + bytes.fromhex(beacon_randomness) + private_seed).digest()


def trial_stream(root, world_id, arm, attempt, stream):
    if (len(root) != 32 or not re.fullmatch("[a-z0-9_-]+", world_id)
            or not re.fullmatch("[a-z0-9_]+", arm) or type(attempt) is not int or attempt < 0
            or stream not in ("policy", "native")):
        raise ValueError("invalid independent trial domain")
    label = f"{world_id}\n{arm}\n{attempt}\n{stream}\n".encode("ascii")
    return sha256(root + b"\x00" + label).hexdigest()
