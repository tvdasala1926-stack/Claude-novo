from __future__ import annotations

import argparse
from pathlib import Path

from maquina.produce import FORMATS, produce


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="maquina-produce", description="Produz o vídeo completo a partir de um projeto.")
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--formats", default="9x16", help=f"lista separada por vírgula: {', '.join(FORMATS)}")
    args = ap.parse_args(argv)
    res = produce(args.project, args.out, tuple(args.formats.split(",")))
    for fmt, r in res["results"].items():
        print(fmt, "APROVADO" if r["ok"] else "REPROVADO", f"(tentativas: {r['attempts']})")
    print(res["out_dir"])
    return 0 if all(r["ok"] for r in res["results"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
