"""Gate-3 attempt-02 scientific OpenRAM configuration.

This is the required 256-word by 72-bit, one-read/write-port target.  It is
not an infrastructure-only smoke-test macro.
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

# SKY130's single-port array also places one dummy/replica row beside the
# logical rows.  One physical spare row makes 128 + 1 spare + 1 replica = 130,
# satisfying the technology's two-row quantum.  It does not add a logical
# addressable word; this is the setting used by OpenRAM's shipped SKY130 SRAM
# configurations.
num_spare_rows = 1
# SKY130's 1RW array has one replica-bitline column.  With 72 bits and the
# compiler-selected 2:1 column mux, one physical spare column is required to
# make the 146 total columns divisible by the technology's two-column quantum.
# This does not change the 72-bit logical payload; the compiler exposes its
# documented repair interface in addition to the 72 normal data bits.
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

# Require SPICE-based characterization rather than the analytical default.
analytical_delay = False
use_pex = False

use_nix = False
use_conda = False
num_threads = 4
num_sim_threads = 2
keep_temp = True
output_extended_config = True
output_datasheet_info = True

output_name = "sky130_sram_1rw_72x256_gate3a02"
output_path = "/attempt/output/sky130_sram_1rw_72x256_gate3a02"
openram_temp = "/attempt/work/openram_tmp_256x72"
