"""Self-contained sanity tests for the SPC core (run where numpy/scipy exist).

    docker compose run --rm --entrypoint python spc-mcp test_spc.py
or, on the Jetson with deps installed:
    python services/spc-mcp/test_spc.py
"""
import math

import spc_core as spc


def approx(a, b, tol=1e-3):
    return abs(a - b) <= tol


def test_individuals_limits():
    data = [10, 11, 9, 10, 12, 8, 10, 11, 9, 10]
    r = spc.individuals_mr(data)
    assert approx(r.center, sum(data) / len(data))
    assert r.ucl > r.center > r.lcl
    print("OK individuals limits:", round(r.center, 2), round(r.ucl, 2), round(r.lcl, 2))


def test_rule1_out_of_control():
    data = [10, 10, 10, 10, 10, 10, 10, 10, 10, 50]  # last point is a clear outlier
    r = spc.individuals_mr(data)
    assert not r.in_control
    assert any(v["rule"] == 1 for v in r.violations)
    print("OK rule 1 detected:", [v["rule"] for v in r.violations])


def test_rule2_shift():
    data = [11, 12, 11, 13, 12, 11, 12, 13, 12, 11] + [5]  # then add a stable baseline
    # 9-in-a-row same side relative to overall mean
    base = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 9, 9]
    r = spc.individuals_mr(base)
    assert not r.in_control
    print("OK rule(s) on shift sample:", sorted({v['rule'] for v in r.violations}))


def test_xbar_r():
    # 5 subgroups of size 4
    data = [
        20, 22, 21, 19,
        21, 20, 22, 20,
        19, 21, 20, 22,
        23, 22, 21, 20,
        20, 19, 21, 22,
    ]
    r = spc.xbar_r(data, 4)
    assert r.chart_type == "Xbar-R"
    assert r.secondary["name"] == "R"
    assert r.ucl > r.center > r.lcl
    print("OK Xbar-R:", round(r.center, 2), round(r.ucl, 2), round(r.lcl, 2))


def test_capability():
    # Centered process, sigma ~1, specs +/- 3 => Cp ~1.0
    import numpy as np
    rng = np.random.default_rng(42)
    data = (rng.normal(100, 1.0, 200)).tolist()
    cap = spc.capability(data, usl=103, lsl=97, target=100)
    assert cap["Cp"] is not None and cap["Cpk"] is not None
    assert 0.7 < cap["Cp"] < 1.3
    assert "DPMO" in cap and "sigma_level" in cap
    print("OK capability:", {k: cap[k] for k in ("Cp", "Cpk", "Pp", "Ppk", "sigma_level", "DPMO")})


def test_attribute():
    p = spc.p_chart([2, 3, 1, 4, 2, 3, 5, 2, 1, 3], sample_size=100)
    assert 0 <= p.lcl <= p.center <= p.ucl <= 1
    c = spc.c_chart([5, 6, 4, 7, 5, 6, 8, 5, 4, 6])
    assert c.lcl >= 0 and c.ucl > c.center
    print("OK attribute charts: p.center=", round(p.center, 4), "c.center=", round(c.center, 2))


def test_recommend():
    assert spc.recommend_chart("variable", 1)["recommended_chart"] == "I-MR"
    assert spc.recommend_chart("variable", 4)["recommended_chart"] == "Xbar-R"
    assert spc.recommend_chart("variable", 12)["recommended_chart"] == "Xbar-S"
    assert spc.recommend_chart("defects", counts_constant_area=False)["recommended_chart"] == "u"
    print("OK recommend chart")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nAll {len(fns)} SPC tests passed.")
