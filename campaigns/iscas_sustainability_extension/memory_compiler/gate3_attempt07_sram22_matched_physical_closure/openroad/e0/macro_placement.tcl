# Common rule: data macro uses the same location/orientation as U0. The ECC
# macro is stacked above it with a nominal 60 um face-to-face signal channel.
place_macro -macro_name {u_protected_memory.u_data} -location {30.36 31.23} -orientation MX -exact
place_macro -macro_name {u_protected_memory.u_ecc} -location {30.36 382.84} -orientation R0 -exact

