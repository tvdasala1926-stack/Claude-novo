from __future__ import annotations

import argparse
from pathlib import Path

from maquina.pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="maquina", description="Analisa produtos e vídeos do TikTok.")
    ap.add_argument("--videos", required=True, type=Path, help="arquivo com um link ou caminho por linha")
    ap.add_argument("--products", type=Path, help="CSV/TSV com produtos")
    ap.add_argument("--out", type=Path, default=Path("runs"), help="pasta de saída")
    args = ap.parse_args(argv)
    run_dir = run_pipeline(args.products, args.videos, args.out)
    print(run_dir / "report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
