"""Pinned fresh OpenRAM 256x72 SKY130 target.

This intentionally preserves the v1.2.48 configuration semantics used by the
earlier Gate-3 attempt.  It is executed in a new namespace and never writes to
the historical attempt directory.
"""

tech_name = "sky130"

word_size = 72
num_words = 256
write_size = 72

num_rw_ports = 1
num_r_ports = 0
num_w_ports = 0
num_banks = 1
words_per_row = 2

# SKY130 requires even array quanta after replica structures are included.
# These spares preserve 256 logical words and 72 logical data bits while the
# compiler exposes the repair interface separately.
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

output_name = "sky130_sram_1rw_72x256_green_v32_matched"
output_path = "/fresh/output/sky130_sram_1rw_72x256_green_v32_matched"
openram_temp = "/fresh/work/openram_tmp_256x72"
