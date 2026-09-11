"""Gate-3 attempt03 known-good-control configuration.

Classification: upstream configuration.

This is the pinned OpenRAM SKY130 shipped ``sky130_sram_1rw_tiny`` geometry:
16 words, eight data bits, 1RW, one spare row and one spare column.  Attempt03
adds only explicit corner, qualification, reproducibility, and output settings.
It does not patch OpenRAM or disable DRC, LVS, or SPICE characterization.
"""

tech_name = "sky130"

word_size = 8
num_words = 16
write_size = 2

num_rw_ports = 1
num_r_ports = 0
num_w_ports = 0
num_banks = 1

num_spare_rows = 1
num_spare_cols = 1

process_corners = ["TT"]
supply_voltages = [1.8]
temperatures = [25]
nominal_corner_only = True
only_use_config_corners = True

route_supplies = "ring"
check_lvsdrc = True
inline_lvsdrc = False
uniquify = True
perimeter_pins = True

analytical_delay = False
use_pex = False

use_nix = False
use_conda = False
num_threads = 4
num_sim_threads = 2
keep_temp = True
output_extended_config = True
output_datasheet_info = True

output_name = "sky130_sram_1rw_8x16_gate3a03_control"
output_path = "/attempt/output/control_8x16"
openram_temp = "/attempt/work/control_8x16"
