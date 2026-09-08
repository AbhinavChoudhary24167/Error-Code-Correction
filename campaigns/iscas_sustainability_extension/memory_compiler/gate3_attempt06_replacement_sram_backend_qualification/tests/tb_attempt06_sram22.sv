`timescale 1ns/1ps

module tb_attempt06_sram22;
  logic clk = 1'b0;
  always #5 clk = ~clk;

  logic rstb64, ce64, we64;
  logic [7:0] wmask64, addr64;
  logic [63:0] din64;
  wire [63:0] dout64;

  logic rstb8, ce8, we8;
  logic [7:0] wmask8, addr8, din8;
  wire [7:0] dout8;

  logic rstbe, cee, wee;
  logic [7:0] addre;
  logic [63:0] payload_in;
  logic [71:0] fault_mask;
  wire [63:0] payload_out;
  wire corrected, uncorrectable;

  integer i, j;
  integer single_count = 0;
  integer double_count = 0;
  reg [31:0] prng;
  reg [63:0] pattern64;

  sram22_256x64m4w8 dut64 (
    .clk(clk), .rstb(rstb64), .ce(ce64), .we(we64),
    .wmask(wmask64), .addr(addr64), .din(din64), .dout(dout64)
  );

  sram22_256x8m8w1 dut8 (
    .clk(clk), .rstb(rstb8), .ce(ce8), .we(we8),
    .wmask(wmask8), .addr(addr8), .din(din8), .dout(dout8)
  );

  ecc_sram_256x72_sram22 dute (
    .clk(clk), .rstb(rstbe), .ce(cee), .we(wee), .addr(addre),
    .payload_in(payload_in), .qualification_fault_mask(fault_mask),
    .payload_out(payload_out), .correction_applied(corrected),
    .detected_uncorrectable(uncorrectable)
  );

  task automatic tick;
    begin
      @(negedge clk);
      @(posedge clk);
      #1;
    end
  endtask

  task automatic write64(input [7:0] a, input [63:0] d, input [7:0] m);
    begin
      addr64 = a; din64 = d; wmask64 = m; ce64 = 1; we64 = 1; tick();
    end
  endtask

  task automatic read64(input [7:0] a, input [63:0] expected);
    begin
      addr64 = a; ce64 = 1; we64 = 0; tick();
      if (dout64 !== expected) begin
        $display("FAIL64 addr=%0d expected=%016h actual=%016h", a, expected, dout64);
        $fatal(1);
      end
    end
  endtask

  task automatic write8(input [7:0] a, input [7:0] d, input [7:0] m);
    begin
      addr8 = a; din8 = d; wmask8 = m; ce8 = 1; we8 = 1; tick();
    end
  endtask

  task automatic read8(input [7:0] a, input [7:0] expected);
    begin
      addr8 = a; ce8 = 1; we8 = 0; tick();
      if (dout8 !== expected) begin
        $display("FAIL8 addr=%0d expected=%02h actual=%02h", a, expected, dout8);
        $fatal(1);
      end
    end
  endtask

  task automatic write_ecc(input [7:0] a, input [63:0] d);
    begin
      addre = a; payload_in = d; cee = 1; wee = 1; fault_mask = 0; tick();
    end
  endtask

  task automatic read_ecc(input [7:0] a, input [63:0] expected);
    begin
      addre = a; cee = 1; wee = 0; fault_mask = 0; tick();
      if ((payload_out !== expected) || corrected || uncorrectable) begin
        $display("FAIL_ECC_BASE addr=%0d expected=%016h actual=%016h c=%b u=%b",
                 a, expected, payload_out, corrected, uncorrectable);
        $fatal(1);
      end
    end
  endtask

  initial begin
    rstb64 = 0; ce64 = 0; we64 = 0; wmask64 = 0; addr64 = 0; din64 = 0;
    rstb8 = 0; ce8 = 0; we8 = 0; wmask8 = 0; addr8 = 0; din8 = 0;
    rstbe = 0; cee = 0; wee = 0; addre = 0; payload_in = 0; fault_mask = 0;
    repeat (2) tick();
    rstb64 = 1; rstb8 = 1; rstbe = 1;

    // 256x64: zero/one/checkerboard, address bounds, and byte masks.
    write64(8'h00, 64'h0000000000000000, 8'hff);
    write64(8'hff, 64'hffffffffffffffff, 8'hff);
    write64(8'h55, 64'haaaa5555aaaa5555, 8'hff);
    read64(8'h00, 64'h0000000000000000);
    read64(8'hff, 64'hffffffffffffffff);
    read64(8'h55, 64'haaaa5555aaaa5555);
    write64(8'h33, 64'h0000000000000000, 8'hff);
    write64(8'h33, 64'hffeeddccbbaa9988, 8'ha5);
    read64(8'h33, 64'hff00dd0000aa0088);

    // Deterministic pseudo-random round-trip at multiple addresses.
    prng = 32'h1aceb00c;
    for (i = 0; i < 32; i = i + 1) begin
      prng = {prng[30:0], prng[31] ^ prng[21] ^ prng[1] ^ prng[0]};
      pattern64 = {prng, ~prng};
      write64(i[7:0], pattern64, 8'hff);
    end
    prng = 32'h1aceb00c;
    for (i = 0; i < 32; i = i + 1) begin
      prng = {prng[30:0], prng[31] ^ prng[21] ^ prng[1] ^ prng[0]};
      pattern64 = {prng, ~prng};
      read64(i[7:0], pattern64);
    end
    $display("SRAM22_256X64_FUNCTIONAL_PASS");

    // 256x8: zero/one/checkerboard, address bounds, and per-bit masks.
    write8(8'h00, 8'h00, 8'hff);
    write8(8'hff, 8'hff, 8'hff);
    write8(8'h5a, 8'haa, 8'hff);
    read8(8'h00, 8'h00);
    read8(8'hff, 8'hff);
    read8(8'h5a, 8'haa);
    write8(8'h33, 8'h00, 8'hff);
    write8(8'h33, 8'hff, 8'ha5);
    read8(8'h33, 8'ha5);
    for (i = 0; i < 32; i = i + 1) begin
      write8((8'h80 + i[7:0]), (i * 8'h3d) ^ 8'ha7, 8'hff);
    end
    for (i = 0; i < 32; i = i + 1) begin
      read8((8'h80 + i[7:0]), (i * 8'h3d) ^ 8'ha7);
    end
    $display("SRAM22_256X8_FUNCTIONAL_PASS");

    // Published reset is an operation inhibit, not memory initialization.
    read64(8'h55, 64'haaaa5555aaaa5555);
    rstb64 = 0; addr64 = 8'hff; ce64 = 1; we64 = 0; tick();
    if (dout64 !== 64'haaaa5555aaaa5555) begin
      $display("FAIL_RESET_INHIBIT actual=%016h", dout64);
      $fatal(1);
    end
    rstb64 = 1;
    $display("SRAM22_RESET_INHIBIT_SEMANTICS_PASS");

    // Atomic 64+8 composition and Hsiao SECDED read path.
    write_ecc(8'h00, 64'h0000000000000000);
    write_ecc(8'hff, 64'hffffffffffffffff);
    write_ecc(8'h42, 64'h0123456789abcdef);
    write_ecc(8'h24, 64'haaaa55555a5aa5a5);
    read_ecc(8'h00, 64'h0000000000000000);
    read_ecc(8'hff, 64'hffffffffffffffff);
    read_ecc(8'h42, 64'h0123456789abcdef);
    read_ecc(8'h24, 64'haaaa55555a5aa5a5);
    $display("SRAM22_256X72_COMPOSITION_PASS");

    // Exercise every one of the 72 single-bit fault locations.
    addre = 8'h42; cee = 1; wee = 0; fault_mask = 0; tick();
    for (i = 0; i < 72; i = i + 1) begin
      fault_mask = (72'b1 << i); #1;
      if ((payload_out !== 64'h0123456789abcdef) || !corrected || uncorrectable) begin
        $display("FAIL_SINGLE bit=%0d data=%016h c=%b u=%b",
                 i, payload_out, corrected, uncorrectable);
        $fatal(1);
      end
      single_count = single_count + 1;
    end

    // Exhaust all 2,556 double-bit pairs (stronger than representative-only).
    for (i = 0; i < 72; i = i + 1) begin
      for (j = i + 1; j < 72; j = j + 1) begin
        fault_mask = (72'b1 << i) | (72'b1 << j); #1;
        if (corrected || !uncorrectable) begin
          $display("FAIL_DOUBLE bits=%0d,%0d c=%b u=%b", i, j, corrected, uncorrectable);
          $fatal(1);
        end
        double_count = double_count + 1;
      end
    end
    fault_mask = 0; #1;
    if ((payload_out !== 64'h0123456789abcdef) || corrected || uncorrectable) begin
      $display("FAIL_POST_INJECTION");
      $fatal(1);
    end
    $display("HSIAO_SECDED_PASS singles=%0d doubles=%0d", single_count, double_count);
    $display("ATTEMPT06_FUNCTIONAL_QUALIFICATION_PASS");
    $finish;
  end
endmodule
