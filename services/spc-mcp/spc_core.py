"""Statistical Process Control (SPC) computation core.

Implements the textbook control-chart maths used across the X-8G2T SPC MCP:
  * Variable charts : I-MR (individuals), Xbar-R, Xbar-S
  * Attribute charts: p, np, c, u
  * Special-cause detection: Nelson's 8 rules + the Western Electric subset
  * Process capability: Cp, Cpk, Pp, Ppk, Z-bench, DPMO, sigma level

References: Oakland, "Statistical Process Control" (5th ed.); "The Book of SPC";
Montgomery control-chart constants; AIAG SPC manual.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

# -----------------------------------------------------------------------------
# Control-chart constants, indexed by subgroup size n (2..10).
# -----------------------------------------------------------------------------
A2 = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}
A3 = {2: 2.659, 3: 1.954, 4: 1.628, 5: 1.427, 6: 1.287, 7: 1.182, 8: 1.099, 9: 1.032, 10: 0.975}
D3 = {2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223}
D4 = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}
B3 = {2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.030, 7: 0.118, 8: 0.185, 9: 0.239, 10: 0.284}
B4 = {2: 3.267, 3: 2.568, 4: 2.266, 5: 2.089, 6: 1.970, 7: 1.882, 8: 1.815, 9: 1.761, 10: 1.716}
d2 = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}
c4 = {2: 0.7979, 3: 0.8862, 4: 0.9213, 5: 0.9400, 6: 0.9515, 7: 0.9594, 8: 0.9650, 9: 0.9693, 10: 0.9727}

D2_MR = 1.128  # d2 for moving range of length 2 (individuals chart)


@dataclass
class ChartResult:
    chart_type: str
    points: list[float]                 # the plotted statistic (X, Xbar, p, ...)
    center: float
    ucl: float
    lcl: float
    sigma_chart: float                  # (UCL - center) / 3 for the plotted statistic
    # Optional secondary chart (range/MR/S) for variable charts:
    secondary: dict | None = None
    sigma_within: float | None = None   # individual-level sigma estimate
    violations: list[dict] = field(default_factory=list)
    in_control: bool = True
    labels: list[int] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "chart_type": self.chart_type,
            "center": round(self.center, 6),
            "ucl": round(self.ucl, 6),
            "lcl": round(self.lcl, 6),
            "sigma_chart": round(self.sigma_chart, 6),
            "sigma_within": round(self.sigma_within, 6) if self.sigma_within else None,
            "n_points": len(self.points),
            "points": [round(p, 6) for p in self.points],
            "secondary": self.secondary,
            "in_control": self.in_control,
            "n_violations": len(self.violations),
            "violations": self.violations,
            "meta": self.meta,
        }


def _subgroups(values: list[float], n: int) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    usable = (len(arr) // n) * n
    if usable == 0:
        raise ValueError(f"need at least {n} values to form one subgroup")
    return arr[:usable].reshape(-1, n)


# -----------------------------------------------------------------------------
# Variable control charts
# -----------------------------------------------------------------------------
def individuals_mr(values: list[float]) -> ChartResult:
    x = np.asarray(values, dtype=float)
    if x.size < 2:
        raise ValueError("I-MR needs at least 2 points")
    mr = np.abs(np.diff(x))
    mr_bar = float(mr.mean())
    xbar = float(x.mean())
    sigma = mr_bar / D2_MR if mr_bar > 0 else float(x.std(ddof=1))
    ucl, lcl = xbar + 3 * sigma, xbar - 3 * sigma
    res = ChartResult(
        chart_type="I-MR",
        points=x.tolist(), center=xbar, ucl=ucl, lcl=lcl, sigma_chart=sigma,
        sigma_within=sigma,
        secondary={"name": "MR", "points": [round(v, 6) for v in mr.tolist()],
                   "center": round(mr_bar, 6),
                   "ucl": round(D4[2] * mr_bar, 6), "lcl": 0.0},
        labels=list(range(1, x.size + 1)),
    )
    _apply_rules(res)
    return res


def xbar_r(values: list[float], n: int) -> ChartResult:
    if not 2 <= n <= 10:
        raise ValueError("Xbar-R supports subgroup size 2..10 (use Xbar-S for n>10)")
    g = _subgroups(values, n)
    means = g.mean(axis=1)
    ranges = g.max(axis=1) - g.min(axis=1)
    xbarbar = float(means.mean())
    rbar = float(ranges.mean())
    sigma_within = rbar / d2[n] if rbar > 0 else float(means.std(ddof=1))
    ucl, lcl = xbarbar + A2[n] * rbar, xbarbar - A2[n] * rbar
    res = ChartResult(
        chart_type="Xbar-R",
        points=means.tolist(), center=xbarbar, ucl=ucl, lcl=lcl,
        sigma_chart=(ucl - xbarbar) / 3, sigma_within=sigma_within,
        secondary={"name": "R", "points": [round(v, 6) for v in ranges.tolist()],
                   "center": round(rbar, 6),
                   "ucl": round(D4[n] * rbar, 6), "lcl": round(D3[n] * rbar, 6)},
        labels=list(range(1, len(means) + 1)),
        meta={"subgroup_size": n},
    )
    _apply_rules(res)
    return res


def xbar_s(values: list[float], n: int) -> ChartResult:
    if n < 2:
        raise ValueError("Xbar-S needs subgroup size >= 2")
    nn = min(n, 10)
    g = _subgroups(values, n)
    means = g.mean(axis=1)
    stds = g.std(axis=1, ddof=1)
    xbarbar = float(means.mean())
    sbar = float(stds.mean())
    c4n = c4.get(nn, 1 - 1 / (4 * nn))
    a3 = A3.get(nn, 3 / (c4n * math.sqrt(nn)))
    b3 = B3.get(nn, max(0.0, 1 - 3 / (c4n * math.sqrt(2 * (nn - 1)))))
    b4 = B4.get(nn, 1 + 3 / (c4n * math.sqrt(2 * (nn - 1))))
    sigma_within = sbar / c4n if sbar > 0 else float(means.std(ddof=1))
    ucl, lcl = xbarbar + a3 * sbar, xbarbar - a3 * sbar
    res = ChartResult(
        chart_type="Xbar-S",
        points=means.tolist(), center=xbarbar, ucl=ucl, lcl=lcl,
        sigma_chart=(ucl - xbarbar) / 3, sigma_within=sigma_within,
        secondary={"name": "S", "points": [round(v, 6) for v in stds.tolist()],
                   "center": round(sbar, 6),
                   "ucl": round(b4 * sbar, 6), "lcl": round(b3 * sbar, 6)},
        labels=list(range(1, len(means) + 1)),
        meta={"subgroup_size": n},
    )
    _apply_rules(res)
    return res


# -----------------------------------------------------------------------------
# Attribute control charts
# -----------------------------------------------------------------------------
def p_chart(defectives: list[float], sample_size: int) -> ChartResult:
    d = np.asarray(defectives, dtype=float)
    p = d / sample_size
    pbar = float(d.sum() / (sample_size * d.size))
    sigma = math.sqrt(max(pbar * (1 - pbar) / sample_size, 0))
    res = ChartResult(
        chart_type="p", points=p.tolist(), center=pbar,
        ucl=min(pbar + 3 * sigma, 1.0), lcl=max(pbar - 3 * sigma, 0.0),
        sigma_chart=sigma, labels=list(range(1, d.size + 1)),
        meta={"sample_size": sample_size},
    )
    _apply_rules(res, clamp_lcl0=True)
    return res


def np_chart(defectives: list[float], sample_size: int) -> ChartResult:
    d = np.asarray(defectives, dtype=float)
    npbar = float(d.mean())
    pbar = npbar / sample_size
    sigma = math.sqrt(max(npbar * (1 - pbar), 0))
    res = ChartResult(
        chart_type="np", points=d.tolist(), center=npbar,
        ucl=npbar + 3 * sigma, lcl=max(npbar - 3 * sigma, 0.0),
        sigma_chart=sigma, labels=list(range(1, d.size + 1)),
        meta={"sample_size": sample_size},
    )
    _apply_rules(res, clamp_lcl0=True)
    return res


def c_chart(counts: list[float]) -> ChartResult:
    c = np.asarray(counts, dtype=float)
    cbar = float(c.mean())
    sigma = math.sqrt(max(cbar, 0))
    res = ChartResult(
        chart_type="c", points=c.tolist(), center=cbar,
        ucl=cbar + 3 * sigma, lcl=max(cbar - 3 * sigma, 0.0),
        sigma_chart=sigma, labels=list(range(1, c.size + 1)),
    )
    _apply_rules(res, clamp_lcl0=True)
    return res


def u_chart(counts: list[float], sample_size: float) -> ChartResult:
    c = np.asarray(counts, dtype=float)
    u = c / sample_size
    ubar = float(c.sum() / (sample_size * c.size))
    sigma = math.sqrt(max(ubar / sample_size, 0))
    res = ChartResult(
        chart_type="u", points=u.tolist(), center=ubar,
        ucl=ubar + 3 * sigma, lcl=max(ubar - 3 * sigma, 0.0),
        sigma_chart=sigma, labels=list(range(1, c.size + 1)),
        meta={"sample_size": sample_size},
    )
    _apply_rules(res, clamp_lcl0=True)
    return res


# -----------------------------------------------------------------------------
# Special-cause rules (Nelson 1..8, includes the Western Electric subset)
# -----------------------------------------------------------------------------
NELSON_DESCRIPTIONS = {
    1: "1 point beyond 3σ (special cause / out of control)",
    2: "9 points in a row on one side of the center line (shift)",
    3: "6 points in a row steadily increasing or decreasing (trend)",
    4: "14 points in a row alternating up and down (overcontrol)",
    5: "2 of 3 consecutive points beyond 2σ on the same side",
    6: "4 of 5 consecutive points beyond 1σ on the same side",
    7: "15 points in a row within 1σ (reduced variation / stratification)",
    8: "8 points in a row beyond 1σ on both sides (mixture)",
}
WESTERN_ELECTRIC = {1, 5, 6, 2}  # the classic WE rule subset


def _apply_rules(res: ChartResult, clamp_lcl0: bool = False) -> None:
    pts = np.asarray(res.points, dtype=float)
    cl, sigma = res.center, res.sigma_chart
    if sigma <= 0:
        res.in_control = True
        return
    side = np.sign(pts - cl)                       # +1 above, -1 below, 0 on CL
    z = (pts - cl) / sigma
    viols: list[dict] = []

    def add(rule: int, idxs: list[int]):
        for i in idxs:
            viols.append({"index": int(i), "label": res.labels[i] if res.labels else i + 1,
                          "rule": rule, "value": round(float(pts[i]), 6),
                          "description": NELSON_DESCRIPTIONS[rule],
                          "western_electric": rule in WESTERN_ELECTRIC})

    # Rule 1: beyond 3σ
    add(1, np.where(np.abs(z) > 3)[0].tolist())

    # Rule 2: 9 in a row same side
    add(2, _run_same_side(side, 9))

    # Rule 3: 6 in a row monotonic
    add(3, _run_monotonic(pts, 6))

    # Rule 4: 14 alternating
    add(4, _run_alternating(pts, 14))

    # Rule 5: 2 of 3 beyond 2σ same side
    add(5, _k_of_m_beyond(z, side, k=2, m=3, thresh=2))

    # Rule 6: 4 of 5 beyond 1σ same side
    add(6, _k_of_m_beyond(z, side, k=4, m=5, thresh=1))

    # Rule 7: 15 in a row within 1σ
    add(7, _run_within(z, 15, 1))

    # Rule 8: 8 in a row beyond 1σ both sides
    add(8, _run_beyond_both(z, 8, 1))

    # Deduplicate (index, rule)
    seen, dedup = set(), []
    for v in sorted(viols, key=lambda d: (d["index"], d["rule"])):
        key = (v["index"], v["rule"])
        if key not in seen:
            seen.add(key); dedup.append(v)
    res.violations = dedup
    res.in_control = len(dedup) == 0


def _run_same_side(side: np.ndarray, length: int) -> list[int]:
    out, run, cur = [], 0, 0
    for i, s in enumerate(side):
        if s != 0 and s == cur:
            run += 1
        elif s != 0:
            cur, run = s, 1
        else:
            cur, run = 0, 0
        if run >= length:
            out.extend(range(i - length + 1, i + 1))
    return out


def _run_monotonic(pts: np.ndarray, length: int) -> list[int]:
    out, inc, dec = [], 1, 1
    for i in range(1, len(pts)):
        inc = inc + 1 if pts[i] > pts[i - 1] else 1
        dec = dec + 1 if pts[i] < pts[i - 1] else 1
        if inc >= length or dec >= length:
            out.extend(range(i - length + 1, i + 1))
    return out


def _run_alternating(pts: np.ndarray, length: int) -> list[int]:
    """length consecutive points alternating up/down (length-1 alternating diffs)."""
    signs = np.sign(np.diff(pts))
    out, run = [], 1
    for i in range(1, len(signs)):
        if signs[i] != 0 and signs[i] == -signs[i - 1]:
            run += 1
        else:
            run = 1
        if run + 1 >= length:                 # run alternating diffs -> run+1 points
            out.extend(range(i - run, i + 2))  # diff i spans pts[i], pts[i+1]
    return out


def _k_of_m_beyond(z: np.ndarray, side: np.ndarray, k: int, m: int, thresh: float) -> list[int]:
    out = []
    for i in range(len(z) - m + 1):
        window = range(i, i + m)
        for sgn in (1, -1):
            hits = [j for j in window if side[j] == sgn and abs(z[j]) > thresh]
            if len(hits) >= k:
                out.extend(hits)
    return out


def _run_within(z: np.ndarray, length: int, thresh: float) -> list[int]:
    out, run = [], 0
    for i in range(len(z)):
        run = run + 1 if abs(z[i]) < thresh else 0
        if run >= length:
            out.extend(range(i - length + 1, i + 1))
    return out


def _run_beyond_both(z: np.ndarray, length: int, thresh: float) -> list[int]:
    out, run = [], 0
    for i in range(len(z)):
        run = run + 1 if abs(z[i]) > thresh else 0
        if run >= length:
            out.extend(range(i - length + 1, i + 1))
    return out


# -----------------------------------------------------------------------------
# Process capability
# -----------------------------------------------------------------------------
def capability(values: list[float], usl: float | None, lsl: float | None,
               target: float | None = None, sigma_within: float | None = None) -> dict:
    x = np.asarray(values, dtype=float)
    mu = float(x.mean())
    sigma_overall = float(x.std(ddof=1))
    # Within (short-term) sigma from average moving range if not supplied.
    if sigma_within is None:
        mr = np.abs(np.diff(x))
        sigma_within = float(mr.mean() / D2_MR) if mr.size and mr.mean() > 0 else sigma_overall
    out: dict = {"mean": round(mu, 6),
                 "sigma_within": round(sigma_within, 6),
                 "sigma_overall": round(sigma_overall, 6),
                 "n": int(x.size)}

    def _indices(sig):
        cp = cpk = None
        if usl is not None and lsl is not None and sig > 0:
            cp = (usl - lsl) / (6 * sig)
        if sig > 0:
            cpu = (usl - mu) / (3 * sig) if usl is not None else None
            cpl = (mu - lsl) / (3 * sig) if lsl is not None else None
            candidates = [v for v in (cpu, cpl) if v is not None]
            cpk = min(candidates) if candidates else None
        return cp, cpk

    cp, cpk = _indices(sigma_within)
    pp, ppk = _indices(sigma_overall)
    out["Cp"] = round(cp, 4) if cp is not None else None
    out["Cpk"] = round(cpk, 4) if cpk is not None else None
    out["Pp"] = round(pp, 4) if pp is not None else None
    out["Ppk"] = round(ppk, 4) if ppk is not None else None

    # DPMO + sigma level from the overall normal fit.
    if sigma_overall > 0 and (usl is not None or lsl is not None):
        p_above = (1 - stats.norm.cdf(usl, mu, sigma_overall)) if usl is not None else 0.0
        p_below = stats.norm.cdf(lsl, mu, sigma_overall) if lsl is not None else 0.0
        p_defect = float(p_above + p_below)
        dpmo = p_defect * 1_000_000
        out["DPMO"] = round(dpmo, 2)
        out["yield_pct"] = round((1 - p_defect) * 100, 6)
        # Long-term Z then add the conventional 1.5σ shift for the sigma level.
        z_lt = stats.norm.ppf(1 - p_defect) if 0 < p_defect < 1 else (6.0 if p_defect == 0 else 0.0)
        out["sigma_level"] = round(float(z_lt) + 1.5, 3)
    if target is not None:
        out["target"] = target
        out["off_target"] = round(mu - target, 6)
    out["verdict"] = _capability_verdict(out.get("Cpk"))
    return out


def _capability_verdict(cpk: float | None) -> str:
    if cpk is None:
        return "Capability not computed (provide USL and/or LSL)."
    if cpk >= 2.0:
        return "World-class (Six Sigma): Cpk ≥ 2.0."
    if cpk >= 1.33:
        return "Capable: Cpk ≥ 1.33 (meets the common industry minimum)."
    if cpk >= 1.0:
        return "Marginally capable: 1.0 ≤ Cpk < 1.33 — improvement recommended."
    return "Not capable: Cpk < 1.0 — process produces out-of-spec output."


# -----------------------------------------------------------------------------
# Chart-type recommendation (decision logic from the SPC literature)
# -----------------------------------------------------------------------------
def recommend_chart(data_type: str, subgroup_size: int = 1,
                    counts_constant_area: bool = True) -> dict:
    dt = data_type.lower()
    if dt in ("variable", "continuous", "measurement"):
        if subgroup_size <= 1:
            choice, why = "I-MR", "Continuous data collected as individual measurements."
        elif subgroup_size <= 9:
            choice, why = "Xbar-R", "Continuous data in small subgroups (2–9); range estimates spread well."
        else:
            choice, why = "Xbar-S", "Continuous data in large subgroups (≥10); use S rather than R."
    elif dt in ("defective", "binary", "pass_fail", "proportion"):
        choice = "np" if counts_constant_area else "p"
        why = ("Counting defective units (pass/fail). Use np when the sample size "
               "is constant, p when it varies.")
    elif dt in ("defects", "count", "poisson"):
        choice = "c" if counts_constant_area else "u"
        why = "Counting defects per unit/area. Use c for constant area/size, u for varying."
    else:
        choice, why = "I-MR", "Defaulting to individuals chart; specify data_type for a better fit."
    return {"recommended_chart": choice, "rationale": why,
            "inputs": {"data_type": data_type, "subgroup_size": subgroup_size,
                       "constant_size_or_area": counts_constant_area}}


def auto_variable_chart(values: list[float], subgroup_size: int = 1) -> ChartResult:
    """Pick and compute the right variable chart for the data."""
    if subgroup_size <= 1:
        return individuals_mr(values)
    if subgroup_size <= 9:
        return xbar_r(values, subgroup_size)
    return xbar_s(values, subgroup_size)
