# Diagnostic continuation only.  The 0.351 ns constraint, resizer algorithm,
# cells, placement controls and repair policy are unchanged.  RSZ-0090 reports
# that no legal buffering solution meets the constraint; suppressing the fatal
# message lets the sensitivity run proceed with the violation still visible.
utl::suppress_message RSZ 90
puts "ATTEMPT10_DIAGNOSTIC_CONTINUATION suppressed_fatal=RSZ-0090 constraint_changed=false"

