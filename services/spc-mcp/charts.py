"""Control-chart rendering (matplotlib, headless Agg backend).

Produces publication-style control charts as PNG or SVG bytes for display in
the X-8G2T UI / SPC reports.
"""
from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from spc_core import ChartResult  # noqa: E402

_ZONE_COLORS = ["#e8f5e9", "#fff8e1", "#ffebee"]  # C (green), B (amber), A (red)


def _draw_primary(ax, res: ChartResult, title: str) -> None:
    pts = res.points
    xs = res.labels or list(range(1, len(pts) + 1))
    cl, sig = res.center, res.sigma_chart
    ucl, lcl = res.ucl, res.lcl

    # Sigma zone shading (only meaningful when sigma > 0).
    if sig > 0:
        for k, color in zip((1, 2, 3), _ZONE_COLORS):
            ax.axhspan(cl + (k - 1) * sig, cl + k * sig, color=color, alpha=0.5, zorder=0)
            ax.axhspan(cl - k * sig, cl - (k - 1) * sig, color=color, alpha=0.5, zorder=0)

    ax.axhline(cl, color="#2e7d32", lw=1.4, label=f"CL={cl:.3g}")
    ax.axhline(ucl, color="#c62828", lw=1.4, ls="--", label=f"UCL={ucl:.3g}")
    ax.axhline(lcl, color="#c62828", lw=1.4, ls="--", label=f"LCL={lcl:.3g}")

    ax.plot(xs, pts, "-o", color="#1565c0", ms=4, lw=1.2, zorder=3)

    # Highlight rule violations in red.
    bad = {v["index"] for v in res.violations}
    if bad:
        bx = [xs[i] for i in bad]
        by = [pts[i] for i in bad]
        ax.plot(bx, by, "o", color="#d50000", ms=8, mfc="none", mew=1.8, zorder=4,
                label="rule violation")

    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel("value")
    ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
    ax.grid(True, axis="x", alpha=0.2)


def _draw_secondary(ax, res: ChartResult) -> None:
    sec = res.secondary
    pts = sec["points"]
    xs = list(range(1, len(pts) + 1))
    ax.axhline(sec["center"], color="#2e7d32", lw=1.2)
    ax.axhline(sec["ucl"], color="#c62828", lw=1.2, ls="--")
    ax.axhline(sec["lcl"], color="#c62828", lw=1.2, ls="--")
    ax.plot(xs, pts, "-o", color="#6a1b9a", ms=3, lw=1.0)
    ax.set_title(f"{sec['name']} chart (variation)", fontsize=10)
    ax.set_ylabel(sec["name"])
    ax.set_xlabel("subgroup / sample")
    ax.grid(True, axis="x", alpha=0.2)


def render(res: ChartResult, title: str | None = None, fmt: str = "png") -> bytes:
    title = title or f"{res.chart_type} control chart"
    has_secondary = res.secondary is not None
    if has_secondary:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=False,
                                       gridspec_kw={"height_ratios": [2, 1]})
        _draw_primary(ax1, res, title)
        _draw_secondary(ax2, res)
    else:
        fig, ax1 = plt.subplots(figsize=(9, 4.5))
        _draw_primary(ax1, res, title)
        ax1.set_xlabel("sample")

    status = "IN CONTROL" if res.in_control else f"OUT OF CONTROL ({len(res.violations)} signals)"
    color = "#2e7d32" if res.in_control else "#c62828"
    fig.text(0.01, 0.01, status, color=color, fontsize=9, fontweight="bold")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
