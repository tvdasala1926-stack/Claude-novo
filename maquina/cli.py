from __future__ import annotations

import argparse
from pathlib import Path

from maquina.pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="maquina", description="Analisa produtos e vídeos do TikTok.")
    ap.add_argument("--videos", type=Path, help="arquivo com um link ou caminho por linha")
    ap.add_argument("--profiles", type=Path, help="arquivo com um perfil (@usuario) por linha")
    ap.add_argument("--per-profile", type=int, default=10, help="vídeos lidos por perfil")
    ap.add_argument("--only-products", action="store_true", help="só vídeos cujo título cita produto/review/publi")
    ap.add_argument("--top", type=int, default=30, help="quantos vídeos mais vistos analisar")
    ap.add_argument("--products", type=Path, help="CSV/TSV com produtos")
    ap.add_argument("--out", type=Path, default=Path("runs"), help="pasta de saída")
    args = ap.parse_args(argv)
    if not args.videos and not args.profiles:
        ap.error("informe --videos e/ou --profiles")
    run_dir = run_pipeline(args.products, args.videos, args.out,
                           profiles_file=args.profiles, per_profile=args.per_profile, top=args.top,
                           only_products=args.only_products)
    print(run_dir / "report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
