"""The registered digest-ranked holdout selector and synthetic workload."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def labelled(entropy, label, fields):
    material = "\n".join(("PCX-X16-draw-v1", entropy, label, canonical(fields), ""))
    return sha256(material.encode("ascii")).hexdigest()


def select_installations(catalogue, entropy):
    if len(entropy) != 64 or any(character not in "0123456789abcdef" for character in entropy):
        raise ValueError("expected lowercase, hex-encoded, 32-byte verified randomness")
    heldouts = []
    for profile in sorted(catalogue["profiles"], key=lambda p: p["id"]):
        paths = [(profile["start"], (), 0)]
        for stage in profile["stages"]:
            paths = [
                (edge["head"], prefix + (edge["id"],),
                 score + stage["base"] + stage["premium"] * edge["stale"])
                for vertex, prefix, score in paths for edge in stage["edges"]
                if edge["tail"] == vertex
            ]
        for verdict in ("YES", "NO"):
            group = [
                (labelled(entropy, "rank", (profile["id"], verdict, path)), path)
                for vertex, path, score in paths if vertex in profile["accept"]
                and (score <= profile["deadline"]) == (verdict == "YES")
            ]
            for rank, (_, path) in enumerate(sorted(group)[:2], start=1):
                key = labelled(entropy, "document", (profile["id"], verdict, path))
                document = {
                    "id": "intake-" + key[:18],
                    "title": f"  Synthetic   intake  {key[18:26]}  ",
                    "category": ("Registry Forms", "Dispatch Notice", "Local Correspondence")[int(key[26:28], 16) % 3],
                    "body": f"Review case {key[28:38]}.\r\nArchive the approved packet.\r\nRoute the synthetic registry.",
                }
                heldouts.append({
                    "id": f"{profile['id']}-{verdict.lower()}-{rank}",
                    "profile": profile["id"], "path": path,
                    "nominal_stratum": verdict, "document": document,
                })
    return heldouts


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("catalogue", type=Path)
    cli.add_argument("verified_beacon", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    catalogue = json.loads(args.catalogue.read_text(encoding="utf-8"))
    sealed = json.loads(args.verified_beacon.read_text(encoding="utf-8"))
    selected = select_installations(catalogue, sealed["beacon"]["randomness"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(selected, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
