"""X-8G2T SPC MCP server.

A LOCAL Model Context Protocol server that exposes Statistical Process Control /
Six Sigma capabilities as tools. The specialized SPC agent (in the
agent-orchestrator) connects to this server over streamable HTTP and uses these
tools to analyze live time-series and produce control charts.

Tools
-----
  spc_recommend_chart : pick the correct chart type for the data
  spc_control_chart   : compute a variable control chart (I-MR / Xbar-R / Xbar-S)
                        with Nelson + Western-Electric rule detection
  spc_attribute_chart : compute a p / np / c / u attribute chart
  spc_rule_check      : run special-cause rules on a series
  spc_capability      : Cp/Cpk/Pp/Ppk/DPMO/sigma-level capability study
  spc_render_chart    : render a control chart as a PNG image for display

Transport: streamable-http (default path /mcp).
"""
from __future__ import annotations

import json
import os

from mcp.server.fastmcp import FastMCP, Image

import charts
import spc_core as spc

mcp = FastMCP("spc-mcp")
mcp.settings.host = os.getenv("HOST", "0.0.0.0")
mcp.settings.port = int(os.getenv("PORT", "8765"))


def _enrich_with_capability(result: dict, values, usl, lsl, target, sigma_within):
    if usl is not None or lsl is not None:
        result["capability"] = spc.capability(values, usl, lsl, target, sigma_within)
    return result


@mcp.tool()
def spc_recommend_chart(data_type: str = "variable", subgroup_size: int = 1,
                        counts_constant_area: bool = True) -> str:
    """Recommend the correct control chart for the data.

    data_type: 'variable' (measurements), 'defective' (pass/fail units),
    or 'defects' (counts of defects per unit/area).
    """
    return json.dumps(spc.recommend_chart(data_type, subgroup_size, counts_constant_area))


@mcp.tool()
def spc_control_chart(values: list[float], subgroup_size: int = 1,
                      usl: float | None = None, lsl: float | None = None,
                      target: float | None = None) -> str:
    """Compute a variable control chart (auto I-MR / Xbar-R / Xbar-S by
    subgroup_size), detect special-cause signals (Nelson + Western Electric),
    and, if spec limits are given, include a process-capability study.

    Returns a JSON summary with control limits, plotted points, violations and
    an in_control verdict. Use spc_render_chart for the picture.
    """
    res = spc.auto_variable_chart(values, subgroup_size)
    out = res.to_dict()
    _enrich_with_capability(out, values, usl, lsl, target, res.sigma_within)
    return json.dumps(out)


@mcp.tool()
def spc_attribute_chart(kind: str, counts: list[float],
                        sample_size: float | None = None) -> str:
    """Compute an attribute control chart.

    kind: 'p' (proportion defective), 'np' (number defective),
          'c' (defects, constant area), 'u' (defects per unit).
    sample_size is required for p, np and u charts.
    """
    kind = kind.lower()
    if kind in ("p", "np", "u") and sample_size is None:
        return json.dumps({"error": f"sample_size is required for the '{kind}' chart"})
    if kind == "p":
        res = spc.p_chart(counts, int(sample_size))
    elif kind == "np":
        res = spc.np_chart(counts, int(sample_size))
    elif kind == "c":
        res = spc.c_chart(counts)
    elif kind == "u":
        res = spc.u_chart(counts, float(sample_size))
    else:
        return json.dumps({"error": f"unknown attribute chart '{kind}'"})
    return json.dumps(res.to_dict())


@mcp.tool()
def spc_rule_check(values: list[float], subgroup_size: int = 1) -> str:
    """Run Nelson's 8 rules (incl. the Western Electric subset) on a series and
    return only the special-cause signals found, with their rule numbers and
    plain-language descriptions."""
    res = spc.auto_variable_chart(values, subgroup_size)
    return json.dumps({
        "chart_type": res.chart_type,
        "in_control": res.in_control,
        "n_violations": len(res.violations),
        "violations": res.violations,
        "rules_reference": spc.NELSON_DESCRIPTIONS,
    })


@mcp.tool()
def spc_capability(values: list[float], usl: float | None = None,
                   lsl: float | None = None, target: float | None = None,
                   subgroup_size: int = 1) -> str:
    """Run a process-capability study: Cp, Cpk, Pp, Ppk, DPMO, yield and the
    estimated sigma level (with the conventional 1.5σ shift)."""
    sigma_within = None
    if subgroup_size > 1:
        sigma_within = spc.auto_variable_chart(values, subgroup_size).sigma_within
    return json.dumps(spc.capability(values, usl, lsl, target, sigma_within))


@mcp.tool()
def spc_render_chart(values: list[float], subgroup_size: int = 1,
                     title: str | None = None, fmt: str = "png") -> Image:
    """Render a variable control chart (with sigma zones and highlighted rule
    violations) as an image for display in the dashboard/report."""
    res = spc.auto_variable_chart(values, subgroup_size)
    fmt = "png" if fmt not in ("png", "svg") else fmt
    data = charts.render(res, title=title, fmt=fmt)
    return Image(data=data, format=fmt)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
