from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[2] / "scripts" / "gate03e" / "validate_mapping.py"
SPEC = importlib.util.spec_from_file_location("gate03e_validate_mapping", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parse_ports_and_cell_masters() -> None:
    text = """
module top(clk_i, data_i, data_o);
  input clk_i;
  input [63:0] data_i;
  output [71:0] data_o;
  sky130_fd_sc_hd__dfxtp_1 ff_0 (.CLK(clk_i));
  sky130_fd_sc_hd__xor2_1 comb_0 (.A(data_i[0]));
endmodule
"""
    assert MODULE.parse_ports(text) == {
        "input clk_i": "scalar",
        "input data_i": "[63:0]",
        "output data_o": "[71:0]",
    }
    assert MODULE.parse_cell_masters(text) == {
        "sky130_fd_sc_hd__dfxtp_1": 1,
        "sky130_fd_sc_hd__xor2_1": 1,
    }


def test_generic_cells_are_visible_to_parser() -> None:
    text = """
module top(a, y);
  input a;
  output y;
  $_NOT_ generic_0 (.A(a), .Y(y));
endmodule
"""
    assert MODULE.parse_cell_masters(text) == {"$_NOT_": 1}


def test_normalized_hash_ignores_comments_attributes_and_spacing() -> None:
    left = """/* generated */\n(* src = \"a:1\" *)\nmodule top(a);\n input a;\nendmodule\n"""
    right = """/* different */\n(* src = \"b:9\" *)\nmodule   top(a);\ninput a;\nendmodule\n"""
    assert MODULE.normalized_netlist_sha256(left) == MODULE.normalized_netlist_sha256(right)


def test_sequential_and_latch_master_patterns_are_disjoint() -> None:
    assert MODULE.SEQUENTIAL_MASTER_RE.search("sky130_fd_sc_hd__dfxtp_1")
    assert not MODULE.LATCH_MASTER_RE.search("sky130_fd_sc_hd__dfxtp_1")
    assert MODULE.LATCH_MASTER_RE.search("sky130_fd_sc_hd__dlxtp_1")
    assert not MODULE.LATCH_MASTER_RE.search("sky130_fd_sc_hd__dlygate4sd1_1")
