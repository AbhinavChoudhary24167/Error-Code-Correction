// Mapping-only independent-channel shell around the already committed Gate-03R
// package-free SECDED modules.  Their exact identity to the accepted production
// implementation is frozen in Gate-03R proof evidence.
module gate03e_secded_combinational_boundary (
  input  logic [63:0] enc_data_i,
  output logic [71:0] enc_codeword_o,
  input  logic [71:0] dec_codeword_i,
  output logic [63:0] dec_data_o,
  output logic [71:0] dec_corrected_codeword_o,
  output logic        dec_detected_o,
  output logic        dec_corrected_o,
  output logic        dec_uncorrectable_o
);
  gate03r_secded_baseline_encoder u_encoder (
    .data_i(enc_data_i),
    .codeword_o(enc_codeword_o)
  );
  gate03r_secded_baseline_decoder u_decoder (
    .codeword_i(dec_codeword_i),
    .data_o(dec_data_o),
    .corrected_codeword_o(dec_corrected_codeword_o),
    .err_detected_o(dec_detected_o),
    .err_corrected_o(dec_corrected_o),
    .err_uncorrectable_o(dec_uncorrectable_o)
  );
endmodule
