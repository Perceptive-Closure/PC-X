import base64
from copy import deepcopy
from datetime import timedelta
from email.utils import format_datetime
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from custody_checks import (
    CHAIN, RELAYS, authority_payload, check_round, check_signatures, round_time,
)
from evidence import (
    EvidenceError, digest, inspect_run, plan_run, process_document, review_terms, wire,
)
from reference import enumerate_paths, solve_profile
from reproduce import PUBLIC_DOCUMENT, compare_forecast


CATALOGUE = Path(__file__).resolve().parents[1] / "cases" / "catalogue.json"


def open_catalogue():
    return json.loads(CATALOGUE.read_bytes())


class EvidenceTests(unittest.TestCase):
    def test_normalization_tracks_js_spaces_and_codepoint_order(self):
        document = process_document(dict(PUBLIC_DOCUMENT, title="\ufeff  Ａ\u00a0Ｂ\u0085  "))
        self.assertEqual(document.normalized["title"], "A B\u0085")
        self.assertEqual(document.normalized["category"], "local-memo")
        self.assertEqual(document.normalized["body"], "Evidence Alpha 2026 \nBETA alpha.\nRésumé Ω𐐀.")
        self.assertEqual(review_terms("Ｆoo foo FOO; ٠ Ⅲ あΑ 𐐀", 1), [
            "foo", "٠", "ⅲ", "あα", "𐐨", "ｆoo",
        ])
        self.assertEqual(wire({"text": "💡\ud800"}), b'{"text":"\xf0\x9f\x92\xa1\\ud800"}\n')

    def test_native_truth_cannot_replace_missing_stage_file(self):
        profile = next(row for row in open_catalogue()["profiles"] if row["id"] == "split-calls")
        path = enumerate_paths(profile)[0]
        task = dict(id="synthetic-truth-test", document=PUBLIC_DOCUMENT, actions=path.fastest_job_actions)
        document, initial, _, steps = plan_run(profile, path, task)
        actual = dict(
            initial=initial, status="manual-done", verdict=None, reason=None,
            steps=steps, work=1, paid=0, moves=1,
            truth={"complete": True, "document_sha256": document.source_hash},
        )
        with tempfile.TemporaryDirectory(prefix="x16-truth-test-") as local:
            workspace = Path(local)
            with self.assertRaises(FileNotFoundError):
                inspect_run(profile, path, task, actual, workspace, {})

    def test_ed25519_independently_binds_exact_signed_draw_bytes(self):
        secret = Ed25519PrivateKey.generate()
        key = secret.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        authority = dict(
            schema=1, source_commit="0" * 40, catalogue_sha256="1" * 64,
            frozen_manifest_sha256="2" * 64, public_key_pem=key.decode("ascii"),
        )
        signed = lambda value: base64.b64encode(secret.sign(value)).decode("ascii")
        authority["signature"] = signed(authority_payload(authority))
        draw_bytes = b'{"public-training-only":true}\n'
        draw = dict(schema=1, draw_sha256=digest(draw_bytes), signature=signed(draw_bytes))
        self.assertEqual(len(check_signatures(authority, draw, draw_bytes)), 64)
        with self.assertRaisesRegex(EvidenceError, "draw signature bytes"):
            check_signatures(authority, draw, draw_bytes + b"\n")

    def test_require_both_exact_round_relay_timings_and_425_body(self):
        draw, published = dummy_round()
        self.assertEqual(check_round(draw, published), published["beacon"]["randomness"])
        corrupt = deepcopy(draw)
        corrupt["still_unavailable_at_commitment"][0]["reason"] = "arbitrary 425"
        with self.assertRaisesRegex(EvidenceError, "future beacon"):
            check_round(corrupt, published)
        late = deepcopy(draw)
        late["still_unavailable_at_commitment"][1]["observed_utc"] = draw["scheduled_utc"]
        with self.assertRaisesRegex(EvidenceError, "after scheduled lock"):
            check_round(late, published)

    def test_forecast_wire_matches_every_baseline_and_detects_changed_values(self):
        profile = next(row for row in open_catalogue()["profiles"] if row["id"] == "meter-h4")
        reference = {"profiles": {"meter-h4": solve_profile(profile, fixed=True)}}
        catalog = {"valid_profiles": ["meter-h4"]}
        published = dict(schema=1, profiles={"meter-h4": {
            "targets": [
                {"path": ["intake", "route-fresh"], "known_work": 2, "label": "YES"},
                {"path": ["intake", "route-stale"], "known_work": 3, "label": "NO"},
            ],
            "static_target": {"value": 1},
            "static_identity": {"value": 1},
            "static_all": {"value": 8},
            "adaptive_pure_target": {"value": 1},
            "adaptive_pure_identity": {"value": 1},
            "online": {"value": 2},
            "online_identity": {"value": 2},
            "structured_scores": {"value": 2},
            "online_fixed": {"value": 3},
        }})
        self.assertEqual(compare_forecast(catalog, reference, published)["discrepancies"], [])
        published["profiles"]["meter-h4"]["online"]["value"] = 1
        failures = compare_forecast(catalog, reference, published)["discrepancies"]
        self.assertEqual(len(failures), 1)
        self.assertIn("sealed forecast online", failures[0]["failure"])


def dummy_round():
    previous = 54321
    target = previous + 120
    registered = round_time(previous) + timedelta(seconds=2)

    def reading(relay, route, status, time, **extra):
        return dict(
            url=f"{relay}/{CHAIN['hash']}{route}", status=status,
            http_date=format_datetime(time, usegmt=True), observed_utc=time.isoformat(), **extra,
        )

    def fake(beacon_round):
        signature = "f" * 96
        return dict(round=beacon_round, signature=signature, randomness=digest(bytes.fromhex(signature)))

    pending = f"/public/{target}"
    local_observed = registered + timedelta(seconds=2)
    release = round_time(target) + timedelta(seconds=3)
    draw = dict(
        chain=CHAIN, selector="PCX-X16-draw-v1", round=target,
        scheduled_utc=round_time(target).isoformat(), registered_utc=registered.isoformat(),
        reference_beacons=[
            dict(http=reading(relay, "/public/latest", 200, registered), beacon=fake(previous))
            for relay in RELAYS
        ],
        still_unavailable_at_commitment=[
            reading(RELAYS[0], pending, 425, local_observed, reason="Requested future beacon (training)"),
            reading(RELAYS[1], pending, 404, local_observed),
        ],
    )
    published = dict(
        schema=1, beacon=fake(target), verified_utc=release.isoformat(),
        fetched=[reading(relay, pending, 200, release) for relay in RELAYS],
    )
    return draw, published


if __name__ == "__main__":
    unittest.main()
