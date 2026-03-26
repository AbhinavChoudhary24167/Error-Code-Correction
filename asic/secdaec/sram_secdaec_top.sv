// SRAM + SEC-DAEC top wrapper (fixed entry: sec-daec-64).
// Note: keep syntax Verilog-2001 compatible for synthesis flows that do not
// enable full SystemVerilog package parsing at read time.
module sram_secdaec_top #(
  parameter DATA_W = 64,
  parameter ECC_W  = 8,
  parameter CODE_W = DATA_W + ECC_W,
  parameter ADDR_W = 8,
  parameter DEPTH  = (1 << ADDR_W)
) (
  input                   clk,
  input                   rst_n,
  input                   cs,
  input                   we,
  input      [ADDR_W-1:0] addr,
  input      [DATA_W-1:0] wdata,
  output     [DATA_W-1:0] rdata,
  output                  valid,
  output                  err_detected,
  output                  err_corrected,
  output                  err_uncorrectable,
  output                  double_error,
  output                  adjacent_error,
  output                  triple_adjacent_error
);
  wire [CODE_W-1:0] enc_code;
  wire [CODE_W-1:0] rd_code;
  wire [CODE_W-1:0] corr_code;
  wire dec_det;
  wire dec_cor;
  wire dec_unc;
  wire dec_adj;

  secdaec_64_encoder #(.DATA_W(DATA_W), .ECC_W(ECC_W), .CODE_W(CODE_W)) u_enc (
    .data_i(wdata), .codeword_o(enc_code)
  );

  sram_core #(.ADDR_W(ADDR_W), .CODE_W(CODE_W), .DEPTH(DEPTH)) u_sram (
    .clk(clk), .rst_n(rst_n), .cs(cs), .we(we), .addr(addr),
    .wcode(enc_code), .rcode(rd_code), .rvalid(valid)
  );

  secdaec_64_decoder #(.DATA_W(DATA_W), .ECC_W(ECC_W), .CODE_W(CODE_W)) u_dec (
    .codeword_i(rd_code), .data_o(rdata), .corrected_codeword_o(corr_code),
    .err_detected_o(dec_det), .err_corrected_o(dec_cor), .err_uncorrectable_o(dec_unc),
    .adjacent_error_o(dec_adj)
  );

  assign err_detected = valid & dec_det;
  assign err_corrected = valid & dec_cor;
  assign err_uncorrectable = valid & dec_unc;
  assign double_error = valid & dec_unc & ~dec_adj;
  assign adjacent_error = valid & dec_adj;
  assign triple_adjacent_error = 1'b0;
endmodule
