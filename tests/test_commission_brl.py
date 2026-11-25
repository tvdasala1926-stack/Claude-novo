from pathlib import Path

from maquina.importer import load_products
from maquina.models import Product
from maquina.rank import rank_products
from maquina.report import build_report


def test_importer_reads_ganho_column_as_commission_brl(tmp_path: Path):
    f = tmp_path / "p.csv"
    f.write_text("nome;preco;ganho;vendas\nMouse;62,62;5,64;3,8K\n", encoding="utf-8")
    (p,) = load_products(f)
    assert p.commission_brl == 5.64 and p.sales == 3800 and p.commission_rate is None


def test_default_ranking_uses_commission_brl():
    ps = [Product("barato", sales=100, commission_brl=1.0), Product("rende", sales=100, commission_brl=20.0)]
    assert rank_products(ps)[0]["product"].name == "rende"


def test_report_shows_commission_brl():
    text = build_report(rank_products([Product("x", sales=1, commission_brl=5.64)]), [], [])
    assert "5.64" in text
