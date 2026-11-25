import pytest

from maquina.models import Product
from maquina.rank import rank_products


def test_orders_by_sales_when_only_sales_known():
    ps = [Product("b", sales=500), Product("a", sales=100), Product("c", sales=1000)]
    ranked = rank_products(ps)
    assert [r["product"].name for r in ranked] == ["c", "b", "a"]
    assert ranked[0]["score"] == pytest.approx(1.0)
    assert ranked[-1]["score"] == pytest.approx(0.0)


def test_missing_field_is_not_treated_as_zero():
    ps = [Product("a", sales=None, rating=5.0), Product("b", sales=100, rating=1.0),
          Product("c", sales=1000, rating=3.0)]
    by_name = {r["product"].name: r for r in rank_products(ps)}
    assert "sales" not in by_name["a"]["used_fields"]
    assert "sales" in by_name["a"]["missing_fields"]
    assert by_name["a"]["used_fields"] == ["rating"]
    assert by_name["a"]["score"] == pytest.approx(1.0)


def test_empty_list():
    assert rank_products([]) == []


def test_products_with_no_metrics_score_zero_and_go_last():
    ps = [Product("vazio"), Product("ok", sales=10), Product("ok2", sales=20)]
    ranked = rank_products(ps)
    assert ranked[-1]["product"].name == "vazio"
    assert ranked[-1]["score"] == 0.0
    assert ranked[-1]["used_fields"] == []


def test_custom_weights_change_order():
    ps = [Product("vende", sales=1000, commission_rate=1), Product("paga", sales=10, commission_rate=50)]
    assert rank_products(ps)[0]["product"].name == "vende"
    ranked = rank_products(ps, weights={"sales": 0.0, "commission_rate": 1.0, "rating": 0.0})
    assert ranked[0]["product"].name == "paga"
