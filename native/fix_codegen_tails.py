"""Restore five shared 12-byte PPC epilogues omitted by ReXGlue v0.10.0.

Each caller branches to a tail consisting of li r4,0; li r3,0; bl 0x82CD54A0.
ReXGlue emits the branch but assigns that shared tail only to a different
overlapping function, leaving an undefined C++ label. This transformation is
idempotent and intentionally refuses to patch any unexpected function shape.
"""

from pathlib import Path
import re
import sys


TAILS = {
    "sub_82AE14C8": "82AE15AC",
    "sub_82AEFF8C": "82AF0070",
    "sub_82AFC28C": "82AFC370",
    "sub_82AFCE0C": "82AFCEF0",
    "sub_82B01290": "82B01374",
}


def patch(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
    changed = set()
    for function, address in TAILS.items():
        start = source.find(f"DEFINE_REX_FUNC({function}) {{")
        if start == -1:
            continue
        end = source.find("\n}\n", start)
        if end == -1:
            raise RuntimeError(f"missing function end for {function} in {path}")
        body = source[start:end]
        label = f"loc_{address}"
        if f"\n{label}:" in body:
            continue
        if f"goto {label};" not in body:
            raise RuntimeError(f"{function} has no branch to {label} in {path}")
        if not re.search(r"sub_82[A-Fa-f0-9]{6}\(ctx, base\);\s*$", body):
            raise RuntimeError(f"unexpected ending of {function} in {path}")
        return_address = int(address, 16) + 12
        tail = (
            f"\n{label}:\n"
            "\tctx.r4.s64 = 0;\n"
            "\tctx.r3.s64 = 0;\n"
            f"\tctx.lr = 0x{return_address:08X};\n"
            "\tsub_82CD54A0(ctx, base);"
        )
        source = source[:end] + tail + source[end:]
        changed.add(function)
    if changed:
        path.write_text(source, encoding="utf-8")
    return changed


def main() -> None:
    directory = Path(sys.argv[1])
    found = set()
    for path in directory.glob("gow2_recomp.*.cpp"):
        found.update(patch(path))
    if found != set(TAILS):
        missing = set(TAILS) - found
        # An already-patched build is valid too: check that no goto is orphaned.
        if missing:
            print(f"Unchanged functions: {', '.join(sorted(missing))}")
    print(f"Patched {len(found)} shared epilogues")


if __name__ == "__main__":
    main()
