// SRAM + BCH top wrapper (fixed entry: bch-63).
// NOTE: Decoder behavior follows bounded-search BCH implementation.
module sram_bch_top #(
  parameter int DATA_W = 51,
  parameter int ECC_W  = 12,
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
  logic dec_det, dec_cor, dec_unc;

  bch_63_encoder #(.DATA_W(DATA_W), .ECC_W(ECC_W), .CODE_W(CODE_W)) u_enc (
    .data_i(wdata), .codeword_o(enc_code)
  );

  sram_core #(.ADDR_W(ADDR_W), .CODE_W(CODE_W), .DEPTH(DEPTH)) u_sram (
    .clk(clk), .rst_n(rst_n), .cs(cs), .we(we), .addr(addr),
    .wcode(enc_code), .rcode(rd_code), .rvalid(valid)
  );

  bch_63_decoder #(.DATA_W(DATA_W), .ECC_W(ECC_W), .CODE_W(CODE_W)) u_dec (
    .codeword_i(rd_code), .data_o(rdata), .corrected_codeword_o(corr_code),
    .err_detected_o(dec_det), .err_corrected_o(dec_cor), .err_uncorrectable_o(dec_unc)
  );

  assign err_detected = valid & dec_det;
  assign err_corrected = valid & dec_cor;
  assign err_uncorrectable = valid & dec_unc;
  assign double_error = valid & dec_unc;
  assign adjacent_error = 1'b0;
  assign triple_adjacent_error = 1'b0;
endmodule
