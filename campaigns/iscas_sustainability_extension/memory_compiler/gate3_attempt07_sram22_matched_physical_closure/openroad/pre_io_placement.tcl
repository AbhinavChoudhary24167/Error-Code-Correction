# Identical role-based policy: every external signal pin is placed on the top
# edge so no IO route is forced through the data macro's lower boundary.
set_io_pin_constraint -region top:* -pin_names [get_ports *]
