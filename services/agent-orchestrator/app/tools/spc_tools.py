"""SPC agent tools.

These are thin adapters that expose the local SPC MCP server's tools through
the agent's tool registry. Each call is dispatched to the `spc-mcp` service over
the Model Context Protocol. Importing this module registers the tools.
"""
from __future__ import annotations

from ..core import mcp_client
from .registry import tool


@tool(
    "spc_recommend_chart",
    "Recommend the correct SPC control chart for a dataset. data_type is "
    "'variable' (measurements), 'defective' (pass/fail units) or 'defects' "
    "(counts of defects per unit/area).",
    {"data_type": {"type": "string", "enum": ["variable", "defective", "defects"]},
     "subgroup_size": {"type": "integer", "description": "samples per subgroup (default 1)"},
     "counts_constant_area": {"type": "boolean", "description": "constant sample size/area?"}},
    ["data_type"],
)
async def spc_recommend_chart(data_type: str, subgroup_size: int = 1,
                              counts_constant_area: bool = True) -> str:
    return await mcp_client.call_text("spc_recommend_chart", {
        "data_type": data_type, "subgroup_size": subgroup_size,
        "counts_constant_area": counts_constant_area})


@tool(
    "spc_control_chart",
    "Compute a variable control chart (auto I-MR / Xbar-R / Xbar-S by "
    "subgroup_size) over a list of measurements: control limits, plotted points, "
    "Nelson + Western-Electric rule violations, and (if USL/LSL given) capability.",
    {"values": {"type": "array", "items": {"type": "number"}},
     "subgroup_size": {"type": "integer", "description": "default 1 (individuals)"},
     "usl": {"type": "number", "description": "upper spec limit (optional)"},
     "lsl": {"type": "number", "description": "lower spec limit (optional)"},
     "target": {"type": "number", "description": "target value (optional)"}},
    ["values"],
)
async def spc_control_chart(values: list[float], subgroup_size: int = 1,
                            usl: float | None = None, lsl: float | None = None,
                            target: float | None = None) -> str:
    args: dict = {"values": values, "subgroup_size": subgroup_size}
    if usl is not None:
        args["usl"] = usl
    if lsl is not None:
        args["lsl"] = lsl
    if target is not None:
        args["target"] = target
    return await mcp_client.call_text("spc_control_chart", args)


@tool(
    "spc_rule_check",
    "Run Nelson's 8 special-cause rules (incl. the Western-Electric subset) over "
    "a series and return only the out-of-control signals found.",
    {"values": {"type": "array", "items": {"type": "number"}},
     "subgroup_size": {"type": "integer"}},
    ["values"],
)
async def spc_rule_check(values: list[float], subgroup_size: int = 1) -> str:
    return await mcp_client.call_text("spc_rule_check", {
        "values": values, "subgroup_size": subgroup_size})


@tool(
    "spc_capability",
    "Run a Six Sigma process-capability study: Cp, Cpk, Pp, Ppk, DPMO, yield and "
    "estimated sigma level. Requires at least one of usl/lsl.",
    {"values": {"type": "array", "items": {"type": "number"}},
     "usl": {"type": "number"}, "lsl": {"type": "number"},
     "target": {"type": "number"}, "subgroup_size": {"type": "integer"}},
    ["values"],
)
async def spc_capability(values: list[float], usl: float | None = None,
                         lsl: float | None = None, target: float | None = None,
                         subgroup_size: int = 1) -> str:
    args: dict = {"values": values, "subgroup_size": subgroup_size}
    if usl is not None:
        args["usl"] = usl
    if lsl is not None:
        args["lsl"] = lsl
    if target is not None:
        args["target"] = target
    return await mcp_client.call_text("spc_capability", args)


@tool(
    "spc_attribute_chart",
    "Compute an attribute control chart. kind: p (proportion defective), np "
    "(number defective), c (defects, constant area), u (defects per unit). "
    "sample_size is required for p, np and u.",
    {"kind": {"type": "string", "enum": ["p", "np", "c", "u"]},
     "counts": {"type": "array", "items": {"type": "number"}},
     "sample_size": {"type": "number"}},
    ["kind", "counts"],
)
async def spc_attribute_chart(kind: str, counts: list[float],
                              sample_size: float | None = None) -> str:
    args: dict = {"kind": kind, "counts": counts}
    if sample_size is not None:
        args["sample_size"] = sample_size
    return await mcp_client.call_text("spc_attribute_chart", args)


# The tool names the SPC agent is allowed to use.
SPC_TOOL_NAMES = [
    "spc_recommend_chart", "spc_control_chart", "spc_rule_check",
    "spc_capability", "spc_attribute_chart",
]
