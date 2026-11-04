module rptr_handler #(
    parameter PTR_WIDTH           = 4,
    parameter ALMOST_EMPTY_THRESH = 2
)(
    input                       rclk,
    input                       rrst,
    input                       r_en,
    input  [PTR_WIDTH:0]        g_wptr_sync,

    output reg [PTR_WIDTH:0]    b_rptr,
    output reg [PTR_WIDTH:0]    g_rptr,
    output reg                  empty,
    output reg                  almost_empty,
    output     [PTR_WIDTH-1:0]  r_addr
);

    function [PTR_WIDTH:0] gray2bin;
        input [PTR_WIDTH:0] g;
        integer i;
        begin
            gray2bin[PTR_WIDTH] = g[PTR_WIDTH];
            for (i = PTR_WIDTH-1; i >= 0; i = i - 1)
                gray2bin[i] = gray2bin[i+1] ^ g[i];
        end
    endfunction

    assign r_addr = b_rptr[PTR_WIDTH-1:0];

    wire [PTR_WIDTH:0] b_rptr_next = b_rptr + (r_en && !empty);
    wire [PTR_WIDTH:0] g_rptr_next = (b_rptr_next >> 1) ^ b_rptr_next;

    // Empty: next Gray rptr equals synced Gray wptr
    wire rempty = (g_rptr_next == g_wptr_sync);

    // Almost empty: count = (wptr - rptr) mod 2*DEPTH.
    // Synced wptr is slightly old, so the flag can be early but not late
    // (assuming coordinated reset and reads blocked by empty).
    wire [PTR_WIDTH:0] fill_next     = gray2bin(g_wptr_sync) - b_rptr_next;
    wire               ralmost_empty = (fill_next <= ALMOST_EMPTY_THRESH);

    always @(posedge rclk or posedge rrst) begin
        if (rrst) begin
            b_rptr       <= {(PTR_WIDTH+1){1'b0}};
            g_rptr       <= {(PTR_WIDTH+1){1'b0}};
            empty        <= 1'b1;
            almost_empty <= 1'b1;
        end else begin
            b_rptr       <= b_rptr_next;
            g_rptr       <= g_rptr_next;
            empty        <= rempty;
            almost_empty <= ralmost_empty;
        end
    end

endmodule
