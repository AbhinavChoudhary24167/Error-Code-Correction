if { ![info exists ::env(ATTEMPT10_LIBERTY)] } {
  puts stderr "ATTEMPT10_LIBERTY is required"
  exit 2
}
read_liberty $::env(ATTEMPT10_LIBERTY)
puts "ATTEMPT10_LIBERTY_PARSE_PASS $::env(ATTEMPT10_LIBERTY)"
