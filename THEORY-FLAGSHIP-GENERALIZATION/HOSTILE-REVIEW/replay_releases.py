"""Fetch and replay immutable authorized source checks from Perceptive-Closure/PC-X."""

import base64
import hashlib
import json
import subprocess
import sys


REPOSITORY = "repos/Perceptive-Closure/PC-X"
SCRIPT_PINS = (
    (
        "95b3576a3bf65824b9e09e689aad80f6ae4f46df",
        "THEORY-FLAGSHIP-GENERALIZATION/COMPUTATIONAL-CHECKS/A-check.py",
        "1b245e56e02d2d11faca24860e2e7af20593f55d",
    ),
    (
        "95b3576a3bf65824b9e09e689aad80f6ae4f46df",
        "THEORY-FLAGSHIP-GENERALIZATION/FORMAL-PROOFS/A-StrategicAudit.lean",
        "a0082f24d782933bbb2117b30467df31fd1f0424",
    ),
    (
        "b66188584a3509a96f03c561290672515d9c848f",
        "THEORY-FLAGSHIP-GENERALIZATION/VERIFICATION/check_a_blind.py",
        "614740258f81840148a3e8a5e096a496a4ea5c42",
    ),
    (
        "bebeea2f1be63f89bd6a3bffb8b2651b625a06d2",
        "THEORY-FLAGSHIP-GENERALIZATION/T30-P-GENERALIZED/check_finite.py",
        "0d1ec74f20961dc9cdd16ce41b3a6c3e5380b87f",
    ),
    (
        "bebeea2f1be63f89bd6a3bffb8b2651b625a06d2",
        "THEORY-FLAGSHIP-GENERALIZATION/T30-P-GENERALIZED/TransportChecks.lean",
        "e030ea3d12f6808e8785a722572b1f32aa651593",
    ),
    (
        "19cd95ccfb3b0c4e4f6eb24132516a488d723f84",
        "THEORY-FLAGSHIP-GENERALIZATION/VERIFICATION/check_p_blind.py",
        "dda826de442257a67b721747d3754bd3b701c909",
    ),
    (
        "b4ba949ab516d685324d22ba73c383572c99ea8e",
        "THEORY-FLAGSHIP-GENERALIZATION/COMPUTATIONAL-CHECKS/U-check.py",
        "f2c561dfc3675111f8852542051f395ab6d541f4",
    ),
    (
        "b4ba949ab516d685324d22ba73c383572c99ea8e",
        "THEORY-FLAGSHIP-GENERALIZATION/FORMAL-PROOFS/U-Selected.lean",
        "dc375c415ce18c6bb73905b52da2cdf6e10d81ae",
    ),
    (
        "e09f81e2181445eb4aad4814573a5db2cd2334cc",
        "THEORY-FLAGSHIP-GENERALIZATION/VERIFICATION/check_u_blind.py",
        "6ededeb0b4a571437332262b61705c746cac812b",
    ),
)


def replay(commit, path, expected_blob):
    api_path = f"{REPOSITORY}/contents/{path}?ref={commit}"
    response = json.loads(subprocess.check_output(["gh", "api", api_path]))
    source = base64.b64decode(response["content"])
    git_blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    if response["sha"] != expected_blob or git_blob != expected_blob:
        raise ValueError(f"GitHub blob mismatch for {commit}:{path}")

    print(f"{commit} {git_blob} {path}", flush=True)
    command = [sys.executable, "-"] if path.endswith(".py") else ["lean", "--stdin"]
    subprocess.run(command, input=source, check=True)


if __name__ == "__main__":
    for pin in SCRIPT_PINS:
        replay(*pin)
