`timescale 1ns/1ps
module reference_encoder_tb;
  reg [63:0] payloads [0:255];
  reg [63:0] data;
  wire [71:0] codeword;
  integer i, output_file;
  gate03r_secded_baseline_encoder encoder(.data_i(data), .codeword_o(codeword));
  initial begin
    $readmemh("/mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/fresh_runs/secded_clk10p0ns_seed23/attempt01/workloads/payloads.hex", payloads);
    output_file = $fopen("/mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/fresh_runs/secded_clk10p0ns_seed23/attempt01/workloads/codewords_clean.hex", "w");
    if (output_file == 0) $fatal(1, "cannot open codeword output");
    for (i = 0; i < 256; i = i + 1) begin
      data = payloads[i]; #1;
      if (^codeword === 1'bx) $fatal(1, "unknown reference codeword at %0d", i);
      $fdisplay(output_file, "%018h", codeword);
    end
    $fclose(output_file);
  end
endmodule
