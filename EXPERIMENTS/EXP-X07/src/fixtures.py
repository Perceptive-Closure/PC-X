"""Inert local certificate generation and signed-byte audit observations."""

import secrets
from collections import Counter

from cryptography import __version__ as cryptography_version, x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, SignatureAlgorithmOID

from .records import (
    PROTOCOL_FILE,
    canonical,
    cases,
    cert_ids,
    check_git_sha,
    digest,
    file_digest,
    parse_utc,
    require,
    utc_now,
    write_json,
)


CA_FILES = ("approved-root.pem", "other-root.pem", "approved-issuer.pem", "other-issuer.pem")


def name(common_name):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def profile_extensions(public_key, issuer_key, path_length, hostname):
    ca = path_length is not None
    extensions = {
        x509.BasicConstraints: (x509.BasicConstraints(ca, path_length), True),
        x509.KeyUsage: (
            x509.KeyUsage(
                digital_signature=not ca, content_commitment=False,
                key_encipherment=not ca, data_encipherment=False, key_agreement=False,
                key_cert_sign=ca, crl_sign=ca, encipher_only=False, decipher_only=False,
            ),
            True,
        ),
        x509.SubjectKeyIdentifier: (x509.SubjectKeyIdentifier.from_public_key(public_key), False),
        x509.AuthorityKeyIdentifier: (
            x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key), False
        ),
    }
    if not ca:
        extensions.update({
            x509.ExtendedKeyUsage: (x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False),
            x509.SubjectAlternativeName: (x509.SubjectAlternativeName([x509.DNSName(hostname)]), False),
        })
    return extensions


def issue(spec, common_name, path_length, dates, issuer=None):
    """Keys live in this process, with certificate-only serialization."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=spec["certificates"]["rsa_bits"])
    subject = name(common_name)
    issuer_key, issuer_name = issuer if issuer else (key, subject)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(parse_utc(dates[0]))
        .not_valid_after(parse_utc(dates[1]))
    )
    for value, critical in profile_extensions(
        key.public_key(), issuer_key.public_key(), path_length, spec["native"]["hostname"]
    ).values():
        builder = builder.add_extension(value, critical)
    return key, builder.sign(issuer_key, hashes.SHA256())


def names_for(spec):
    return [*CA_FILES, *(f"{case}.pem" for case in cert_ids(spec))]


def manifest(spec, public):
    expected = names_for(spec)
    require({p.name for p in public.iterdir()} == set(expected), "Unexpected public fixture inventory")
    return {filename: file_digest(public / filename) for filename in expected}


def write_fixtures(spec, public, assignments):
    public.mkdir()
    profiles = spec["certificates"]
    for side in ("approved", "other"):
        root_key, root = issue(spec, profiles[f"{side}_root_name"], 1, profiles["ca_dates"])
        chain_key, chain = issue(
            spec, profiles["intermediate_name"], 0, profiles["ca_dates"], (root_key, root.subject)
        )
        for role, certificate in (("root", root), ("issuer", chain)):
            (public / f"{side}-{role}.pem").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        for case, profile in assignments.items():
            issuer, window = profile.split("-")
            if issuer == side:
                _, leaf = issue(
                    spec, spec["native"]["hostname"], None, profiles[f"leaf_{window}_dates"],
                    (chain_key, chain.subject),
                )
                (public / f"{case}.pem").write_bytes(leaf.public_bytes(serialization.Encoding.PEM))


def seed(spec, run, protocol_commit, registered_at):
    check_git_sha(protocol_commit)
    require(parse_utc(registered_at) <= parse_utc(utc_now()), "Remote registration is in the future")
    run.mkdir()
    evidence = run / "evidence"
    evidence.mkdir()
    public = evidence / "public"
    profiles = [row["id"] for row in spec["completions"]] * spec["sample"]["held_out_per_completion"]
    secrets.SystemRandom().shuffle(profiles)
    assignments = dict(zip(cases(spec), profiles, strict=True))
    for role in ("positive", "negative"):
        control = spec["controls"][role]
        assignments[control["id"]] = control["completion"]
    write_fixtures(spec, public, assignments)
    reveal = {
        "schema": 1, "protocol_commit": protocol_commit, "protocol_registered_at": registered_at,
        "protocol_sha256": file_digest(PROTOCOL_FILE), "created_at": utc_now(),
        "fixture_library": f"cryptography {cryptography_version}",
        "nonce": secrets.token_hex(32), "assignments": assignments,
        "public_sha256": manifest(spec, public),
    }
    commitment = {
        key: reveal[key] for key in (
            "schema", "protocol_commit", "protocol_registered_at", "protocol_sha256",
            "created_at", "fixture_library", "public_sha256",
        )
    }
    commitment["reveal_sha256"] = digest(canonical(reveal))
    write_json(run / "reveal.json", reveal)
    write_json(evidence / "commitment.json", commitment)
    return commitment


def check_inventory(spec, public, commitment):
    check_git_sha(commitment["protocol_commit"])
    require(commitment["schema"] == 1, "Unexpected commitment schema")
    require(file_digest(PROTOCOL_FILE) == commitment["protocol_sha256"], "Protocol digest differs")
    require(manifest(spec, public) == commitment["public_sha256"], "Public fixture digest differs")
    require(
        parse_utc(commitment["protocol_registered_at"]) <= parse_utc(commitment["created_at"]),
        "Fixture commitment predates remote protocol registration",
    )


def check_reveal(spec, commitment, reveal, observed):
    require(digest(canonical(reveal)) == commitment["reveal_sha256"], "Custody digest differs")
    common = set(commitment) - {"reveal_sha256"}
    require(all(commitment[key] == reveal[key] for key in common), "Reveal metadata differs")
    expected = Counter({row["id"]: spec["sample"]["held_out_per_completion"] for row in spec["completions"]})
    require(Counter(reveal["assignments"][case] for case in cases(spec)) == expected, "Unbalanced reveal")
    require(set(reveal["assignments"]) == set(cert_ids(spec)), "Unexpected reveal inventory")
    by_profile = {row["id"]: row for row in spec["completions"]}
    for case, profile_id in reveal["assignments"].items():
        expected_answers = {query: by_profile[profile_id][query] for query in spec["queries"]}
        require(observed["cases"][case]["answers"] == expected_answers, f"Reveal conflicts with {case}")
    for role in ("positive", "negative"):
        control = spec["controls"][role]
        require(reveal["assignments"][control["id"]] == control["completion"], "Control assignment differs")


def read_certificate(path):
    raw = path.read_bytes()
    cert = x509.load_pem_x509_certificate(raw)
    require(cert.public_bytes(serialization.Encoding.PEM) == raw, f"Unexpected PEM content: {path.name}")
    return cert


def dates_of(cert):
    return [cert.not_valid_before_utc.isoformat(), cert.not_valid_after_utc.isoformat()]


def signed_by(cert, issuer):
    if cert.issuer != issuer.subject:
        return False
    try:
        cert.verify_directly_issued_by(issuer)
    except InvalidSignature:
        return False
    return True


def validate_profile(spec, cert, issuer, common_name, path_length, dates):
    key = cert.public_key()
    require(
        isinstance(key, rsa.RSAPublicKey) and key.key_size == spec["certificates"]["rsa_bits"]
        and key.public_numbers().e == 65537,
        "Unexpected certificate key",
    )
    require(
        cert.version == x509.Version.v3 and cert.signature_algorithm_oid == SignatureAlgorithmOID.RSA_WITH_SHA256,
        "Unexpected certificate version or signature algorithm",
    )
    require(cert.subject == name(common_name) and cert.issuer == issuer.subject, "Unexpected X.509 name")
    require(dates_of(cert) == dates, "Outside frozen certificate validity profiles")
    expected = profile_extensions(key, issuer.public_key(), path_length, spec["native"]["hostname"])
    actual = {type(ext.value): (ext.value, ext.critical) for ext in cert.extensions}
    require(actual == expected, "Certificate extension profile differs")
    require(signed_by(cert, issuer), "Certificate is not directly signed by stated issuer")


def audit(spec, public):
    """Read only immutable certificate bytes. No path verifier or saved outcome is read."""
    profiles = spec["certificates"]
    certs = {filename: read_certificate(public / filename) for filename in names_for(spec)}
    root = {side: certs[f"{side}-root.pem"] for side in ("approved", "other")}
    issuer = {side: certs[f"{side}-issuer.pem"] for side in ("approved", "other")}
    at = parse_utc(spec["native"]["evaluation_utc"])
    for side in root:
        validate_profile(spec, root[side], root[side], profiles[f"{side}_root_name"], 1, profiles["ca_dates"])
        validate_profile(spec, issuer[side], root[side], profiles["intermediate_name"], 0, profiles["ca_dates"])
        require(root[side].not_valid_before_utc <= at < root[side].not_valid_after_utc, "CA dates out of scope")
    require(
        issuer["approved"].subject == issuer["other"].subject
        and issuer["approved"].public_key().public_numbers() != issuer["other"].public_key().public_numbers(),
        "Fixture issuer alternatives must have equal names and distinct public keys",
    )
    require(not signed_by(issuer["approved"], root["other"]), "Wrong anchor unexpectedly signs approved issuer")

    result = {
        "method": "independent direct-signature, profile and signed-validity inspection",
        "library": f"cryptography {cryptography_version}",
        "time": at.isoformat(), "authorities": {},
        "wrong_anchor_links_approved_issuer": False, "cases": {},
    }
    for filename in CA_FILES:
        cert = certs[filename]
        result["authorities"][filename] = {
            "der_sha256": cert.fingerprint(hashes.SHA256()).hex(),
            "subject": cert.subject.rfc4514_string(), "issuer": cert.issuer.rfc4514_string(),
            "dates": dates_of(cert),
            "ski": cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value.digest.hex(),
        }
    for label in cert_ids(spec):
        leaf = certs[f"{label}.pem"]
        links = {side: signed_by(leaf, ca) for side, ca in issuer.items()}
        require(sum(links.values()) == 1, f"{label} has unsupported issuer evidence")
        signer = next(side for side in links if links[side])
        validity = dates_of(leaf)
        require(
            validity in (profiles["leaf_current_dates"], profiles["leaf_expired_dates"]),
            f"{label} has an unsupported validity window",
        )
        validate_profile(spec, leaf, issuer[signer], spec["native"]["hostname"], None, validity)
        result["cases"][label] = {
            "der_sha256": leaf.fingerprint(hashes.SHA256()).hex(),
            "issuer": leaf.issuer.rfc4514_string(),
            "aki": leaf.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier).value.key_identifier.hex(),
            "dates": validity, "direct_signature_checks": links,
            "answers": {
                "issuer_binding": links["approved"],
                "leaf_validity": leaf.not_valid_before_utc <= at < leaf.not_valid_after_utc,
            },
        }
    return result
