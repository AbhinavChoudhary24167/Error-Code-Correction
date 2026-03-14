// SRAM + TAEC top wrapper (fixed entry: taec-64).
module sram_taec_top #(
  parameter int DATA_W = 64,
  parameter int ECC_W  = ecc_pkg::hamming_parity_bits(DATA_W) + 1,
  parameter int CODE_W = DATA_W + ECC_W,
  parameter int ADDR_W = 8,
  parameter int DEPTH  = (1 << ADDR_W)
) (
  input  logic              clk,
  input  logic              rst_n,
  input  logic              cs,
  input  logic              we,
  input  logic [ADDR_W-1:0] addr,
  input  logic [DATA_W-1:0] wdata,
  output logic [DATA_W-1:0] rdata,
  output logic              valid,
  output logic              err_detected,
  output logic              err_corrected,
  output logic              err_uncorrectable,
  output logic              double_error,
  output logic              adjacent_error,
  output logic              triple_adjacent_error
);
  logic [CODE_W-1:0] enc_code, rd_code, corr_code;
  logic dec_det, dec_cor, dec_unc, dec_tri;

  taec_64_encoder #(.DATA_W(DATA_W), .ECC_W(ECC_W), .CODE_W(CODE_W)) u_enc (
    .data_i(wdata), .codeword_o(enc_code)
  );

  sram_core #(.ADDR_W(ADDR_W), .CODE_W(CODE_W), .DEPTH(DEPTH)) u_sram (
    .clk(clk), .rst_n(rst_n), .cs(cs), .we(we), .addr(addr),
    .wcode(enc_code), .rcode(rd_code), .rvalid(valid)
  );

  taec_64_decoder #(.DATA_W(DATA_W), .ECC_W(ECC_W), .CODE_W(CODE_W)) u_dec (
    .codeword_i(rd_code), .data_o(rdata), .corrected_codeword_o(corr_code),
    .err_detected_o(dec_det), .err_corrected_o(dec_cor), .err_uncorrectable_o(dec_unc),
    .triple_adjacent_error_o(dec_tri)
  );

  assign err_detected = valid & dec_det;
  assign err_corrected = valid & dec_cor;
  assign err_uncorrectable = valid & dec_unc;
  assign double_error = valid & dec_unc & ~dec_tri;
  assign adjacent_error = 1'b0;
  assign triple_adjacent_error = valid & dec_tri;
endmodule
