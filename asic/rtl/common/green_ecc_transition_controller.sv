// Transition sequencer only. The read/decode/re-encode/write datapath is not
// implemented here; external completion/verification handshakes are required.
module green_ecc_transition_controller #(
  parameter int MODE_COUNT = 3,
  parameter int MODE_WIDTH = (MODE_COUNT <= 1) ? 1 : $clog2(MODE_COUNT),
  parameter logic [MODE_WIDTH-1:0] SAFE_FALLBACK = '0
) (
  input  logic                  clk_i,
  input  logic                  rst_ni,
  input  logic                  request_i,
  input  logic [MODE_WIDTH-1:0] requested_mode_i,
  input  logic                  quiesce_done_i,
  input  logic                  read_done_i,
  input  logic                  decode_done_i,
  input  logic                  encode_done_i,
  input  logic                  write_done_i,
  input  logic                  verify_done_i,
  input  logic                  verify_ok_i,
  input  logic                  resume_done_i,
  input  logic                  abort_i,
  output logic [MODE_WIDTH-1:0] active_mode_o,
  output logic [MODE_WIDTH-1:0] target_mode_o,
  output logic [3:0]            state_o,
  output logic                  busy_o,
  output logic                  metadata_commit_o,
  output logic                  recovery_o
);
  typedef enum logic [3:0] {
    ST_STABLE      = 4'd0,
    ST_QUIESCE     = 4'd1,
    ST_READ_OLD    = 4'd2,
    ST_DECODE      = 4'd3,
    ST_RE_ENCODE   = 4'd4,
    ST_WRITE_NEW   = 4'd5,
    ST_VERIFY      = 4'd6,
    ST_COMMIT_MODE = 4'd7,
    ST_RESUME      = 4'd8,
    ST_RECOVERY    = 4'd9
  } transition_state_e;

  transition_state_e state_q;
  logic requested_valid;
  assign requested_valid = (requested_mode_i < MODE_COUNT);
  assign state_o = state_q;
  assign busy_o = (state_q != ST_STABLE);

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      state_q           <= ST_STABLE;
      active_mode_o     <= SAFE_FALLBACK;
      target_mode_o     <= SAFE_FALLBACK;
      metadata_commit_o <= 1'b0;
      recovery_o        <= 1'b0;
    end else begin
      metadata_commit_o <= 1'b0;
      recovery_o        <= 1'b0;
      if (abort_i && state_q != ST_STABLE) begin
        state_q <= ST_RECOVERY;
      end else begin
        unique case (state_q)
          ST_STABLE: begin
            if (request_i && !requested_valid) begin
              state_q <= ST_RECOVERY;
            end else if (request_i && requested_mode_i != active_mode_o) begin
              target_mode_o <= requested_mode_i;
              state_q <= ST_QUIESCE;
            end
          end
          ST_QUIESCE:   if (quiesce_done_i) state_q <= ST_READ_OLD;
          ST_READ_OLD:  if (read_done_i)    state_q <= ST_DECODE;
          ST_DECODE:    if (decode_done_i)  state_q <= ST_RE_ENCODE;
          ST_RE_ENCODE: if (encode_done_i)  state_q <= ST_WRITE_NEW;
          ST_WRITE_NEW: if (write_done_i)   state_q <= ST_VERIFY;
          ST_VERIFY: begin
            if (verify_done_i && verify_ok_i) state_q <= ST_COMMIT_MODE;
            else if (verify_done_i) state_q <= ST_RECOVERY;
          end
          ST_COMMIT_MODE: begin
            active_mode_o     <= target_mode_o;
            metadata_commit_o <= 1'b1;
            state_q           <= ST_RESUME;
          end
          ST_RESUME: if (resume_done_i) state_q <= ST_STABLE;
          ST_RECOVERY: begin
            active_mode_o <= SAFE_FALLBACK;
            target_mode_o <= SAFE_FALLBACK;
            recovery_o    <= 1'b1;
            state_q       <= ST_RESUME;
          end
          default: state_q <= ST_RECOVERY;
        endcase
      end
    end
  end
endmodule
