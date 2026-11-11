module wptr_handler #(
    parameter PTR_WIDTH          = 4,
    parameter ALMOST_FULL_THRESH = 2
)(
    input                       wclk,
    input                       wrst,
    input                       w_en,
    input  [PTR_WIDTH:0]        g_rptr_sync,

    output reg [PTR_WIDTH:0]    b_wptr,
    output reg [PTR_WIDTH:0]    g_wptr,
    output reg                  full,
    output reg                  almost_full,
    output     [PTR_WIDTH-1:0]  w_addr
);

    localparam [PTR_WIDTH:0] AF_LEVEL = (1 << PTR_WIDTH) - ALMOST_FULL_THRESH;

    function [PTR_WIDTH:0] gray2bin;
        input [PTR_WIDTH:0] g;
        integer i;
        begin
            gray2bin[PTR_WIDTH] = g[PTR_WIDTH];
            for (i = PTR_WIDTH-1; i >= 0; i = i - 1)
                gray2bin[i] = gray2bin[i+1] ^ g[i];
        end
    endfunction

    assign w_addr = b_wptr[PTR_WIDTH-1:0];

    wire [PTR_WIDTH:0] b_wptr_next = b_wptr + (w_en && !full);
    wire [PTR_WIDTH:0] g_wptr_next = (b_wptr_next >> 1) ^ b_wptr_next;

    // Full: Gray wptr equals synced Gray rptr with the top 2 bits inverted
    wire wfull = (g_wptr_next ==
                  {~g_rptr_sync[PTR_WIDTH:PTR_WIDTH-1],
                    g_rptr_sync[PTR_WIDTH-2:0]});

    // Almost full: count = (wptr - rptr) mod 2*DEPTH.
    // Synced rptr is slightly old, so the flag can be early but not late
    // (assuming coordinated reset and writes blocked by full).
    wire [PTR_WIDTH:0] fill_next    = b_wptr_next - gray2bin(g_rptr_sync);
    wire               walmost_full = (fill_next >= AF_LEVEL);

    always @(posedge wclk or posedge wrst) begin
        if (wrst) begin
            b_wptr      <= {(PTR_WIDTH+1){1'b0}};
            g_wptr      <= {(PTR_WIDTH+1){1'b0}};
            full        <= 1'b0;
            almost_full <= 1'b0;
        end else begin
            b_wptr      <= b_wptr_next;
            g_wptr      <= g_wptr_next;
            full        <= wfull;
            almost_full <= walmost_full;
        end
    end

endmodule
