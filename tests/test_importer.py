from pathlib import Path

import pytest

from maquina.importer import load_products, load_video_refs, parse_number


@pytest.mark.parametrize("text,expected", [
    ("R$ 1.299,90", 1299.90),
    ("12,5 mil", 12500),
    ("1,2 mi", 1_200_000),
    ("3k", 3000),
    ("12%", 12),
    ("4.5", 4.5),
    ("1.299", 1299),
])
def test_parse_number_brazilian_formats(text, expected):
    assert parse_number(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["abc", "", None, "   "])
def test_parse_number_unreadable_is_none(text):
    assert parse_number(text) is None


def test_load_products_handles_blank_duplicates_and_missing_columns(tmp_path: Path):
    f = tmp_path / "p.csv"
    f.write_text(
        "Nome;Preço;Comissão;Vendas\n"
        "Teclado X;R$ 199,90;12%;1,5 mil\n"
        "\n"
        "Mouse Y;R$ 89,00;10%;800\n"
        "teclado x;R$ 199,90;;3 mil\n",
        encoding="utf-8",
    )
    products = load_products(f)
    assert [p.name for p in products] == ["Teclado X", "Mouse Y"]
    assert products[0].sales == 3000
    assert products[0].commission_rate == 12
    assert products[0].price == pytest.approx(199.90)
    assert all(p.rating is None for p in products)


def test_load_products_accepts_tab_separated_and_english_headers(tmp_path: Path):
    f = tmp_path / "p.tsv"
    f.write_text("name\tprice\tsales\trating\nHeadset Z\t300\t50\t4.7\n", encoding="utf-8")
    (p,) = load_products(f)
    assert (p.name, p.price, p.sales, p.rating) == ("Headset Z", 300, 50, 4.7)
    assert p.commission_rate is None


def test_load_video_refs_dedups_and_classifies(tmp_path: Path):
    f = tmp_path / "v.txt"
    f.write_text(
        "# comentário\n"
        "https://www.tiktok.com/@a/video/1\n"
        "\n"
        "  /tmp/local.mp4  \n"
        "https://www.tiktok.com/@a/video/1\n",
        encoding="utf-8",
    )
    refs = load_video_refs(f)
    assert len(refs) == 2
    assert refs[0].url == "https://www.tiktok.com/@a/video/1" and refs[0].path is None
    assert refs[1].path == "/tmp/local.mp4" and refs[1].url is None
