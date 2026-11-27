"""Check the standalone paper and its local index. Requires pypdf and Python 3.10+."""
import argparse
import re
from pathlib import Path

from pypdf import PdfReader


def assert_complete(paper: Path, pdf_path: Path, aux_path: Path | None) -> None:
    manuscript = paper / "manuscript"
    sources = list(manuscript.rglob("*.tex"))
    texts = {p: p.read_text(encoding="utf-8") for p in sources}
    full = "\n".join(texts.values())
    labels = re.findall(r"\\label\{([\w:.-]+)\}", full)
    labels.extend(re.findall(r"(?m)^\\figpc\{[^\n]+\}\{(fig:[\w.-]+)\}\s*$", full))
    assert len(labels) == len(set(labels)), "Duplicate source label"
    refs = set(re.findall(r"\\(?:ref|eqref)\*?\{([^}]+)\}", full))
    assert not refs - set(labels), f"Unresolved source references: {refs - set(labels)}"
    for path, source_text in texts.items():
        for relative in re.findall(r"\\input\{([^}]+)\}", source_text):
            assert (manuscript / (relative + ".tex")).is_file(), (path, relative)
    figures = re.findall(r"\\figpc\{([^}]+)\}", full)
    assert len(figures) == len(set(figures)) == 5
    assert all((manuscript / "figures" / (f + ".pdf")).is_file() for f in figures)
    bib = (manuscript / "references.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    cited = {key for group in re.findall(r"\\cite[pt]?\{([^}]+)\}", full) for key in group.split(",")}
    assert keys == cited, (keys - cited, cited - keys)

    crosswalk = (paper / "THEOREM-CROSSWALK.md").read_text(encoding="utf-8")
    for label, path, line in re.findall(r"\[([a-z0-9:]+)\]\((manuscript/[^)#]+)#L(\d+)\)", crosswalk):
        given = texts[(paper / path).resolve()].splitlines()[int(line) - 1]
        assert "\\label{" + label + "}" in given, (label, path, line)
    for i in range(1, 31):
        assert f"| T{i:02} |" in crosswalk
    for i in range(1, 8):
        assert f"| P{i:02} |" in crosswalk
    for i in range(1, 9):
        assert f"| M{i:02} |" in crosswalk
    evidence = (paper / "EXPERIMENTAL-EVIDENCE-MAP.md").read_text(encoding="utf-8")
    for i in range(1, 18):
        assert f"## X{i:02} " in evidence

    reader = PdfReader(pdf_path)
    dest = reader.named_destinations
    internal = 0
    external = 0
    for number, page in enumerate(reader.pages, 1):
        txt = page.extract_text()
        assert txt.strip() and "??" not in txt, f"Empty text or unresolved reference on p. {number}"
        for ref in page.get("/Annots", []):
            obj = ref.get_object()
            action = obj.get("/A", {})
            if action.get("/S") == "/URI":
                assert str(action["/URI"]).startswith(("https://", "http://")), (number, action)
                external += 1
            elif action.get("/S") == "/GoTo" or "/Dest" in obj:
                target = action.get("/D", obj.get("/Dest"))
                if isinstance(target, str):
                    assert target in dest, (number, target)
                else:
                    assert isinstance(target, list) and target, (number, target)
                internal += 1
    if aux_path:
        aux = aux_path.read_text(encoding="utf-8")
        # Section/theorem titles may have nested braces. The anchor field is after the title.
        anchors = {}
        for line in aux.splitlines():
            entry = re.match(r"\\newlabel\{([^}]+)\}\{\{", line)
            target = re.search(r"\}\{([^{}]*)\}\{\}\}$", line)
            if entry and target:
                anchors[entry[1]] = target[1]
        assert set(labels) <= anchors.keys(), set(labels) - anchors.keys()
        assert all(anchors[l] in dest for l in labels), [l for l in labels if anchors[l] not in dest]
    print(f"{len(reader.pages)} pages, {len(labels)} labels, {len(cited)} cited bibliography entries, "
          f"{len(figures)} figures, {internal} internal and {external} external PDF link annotations")


if __name__ == "__main__":
    package = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=package / "PC-X-FULL-PAPER.pdf")
    parser.add_argument("--aux", type=Path, help="also verify typeset label destinations using build/main.aux")
    args = parser.parse_args()
    assert_complete(package, args.pdf, args.aux)
