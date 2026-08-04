// SafeForge certified abstaining syndrome policy.
module safeforge_robust_8_4_v1_safe_safe_decoder(
  input  logic [7:0] word,
  input  logic envelope_valid,
  input  logic fallback_select,
  output logic [3:0] data_out,
  output logic correction_applied,
  output logic abstain,
  output logic detected_uncorrectable,
  output logic fallback_selected,
  output logic no_certified_mode,
  output logic [127:0] safety_envelope_id
);
  logic [3:0] syndrome;
  logic [7:0] correction_mask;
  logic [7:0] corrected_word;
  logic action_correct;
  safeforge_robust_8_4_v1_safe_syndrome u_syndrome(.word(word), .syndrome(syndrome));
  always_comb begin
    action_correct = 1'b0;
    correction_mask = '0;
    unique case (syndrome)
      4'b0001: begin action_correct = 1'b1; correction_mask = 8'b00010000; end
      4'b0010: begin action_correct = 1'b1; correction_mask = 8'b00100000; end
      4'b0101: begin action_correct = 1'b1; correction_mask = 8'b00000010; end
      4'b1000: begin action_correct = 1'b1; correction_mask = 8'b10000000; end
      4'b1001: begin action_correct = 1'b1; correction_mask = 8'b00000110; end
      4'b1011: begin action_correct = 1'b1; correction_mask = 8'b00001100; end
      4'b1101: begin action_correct = 1'b1; correction_mask = 8'b00001001; end
      4'b1111: begin action_correct = 1'b1; correction_mask = 8'b00000011; end
      default: begin end
    endcase
  end
  assign safety_envelope_id = 128'he8bdc4a8cfff447d1ab8c4ab3212ea44;
  assign fallback_selected = !envelope_valid && fallback_select;
  assign no_certified_mode = !envelope_valid && !fallback_select;
  assign correction_applied = envelope_valid && (syndrome != '0) && action_correct;
  assign abstain = (syndrome != '0) && (!envelope_valid || !action_correct);
  assign detected_uncorrectable = abstain;
  assign corrected_word = word ^ ({8{correction_applied}} & correction_mask);
  assign data_out = corrected_word[3:0];
endmodule
