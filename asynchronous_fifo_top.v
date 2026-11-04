module asynchronous_fifo #(
    parameter DATA_WIDTH          = 8,
    parameter PTR_WIDTH           = 4,
    parameter ALMOST_FULL_THRESH  = 2,
    parameter ALMOST_EMPTY_THRESH = 2
)(
    // Write domain
    input                   wclk,
    input                   wrst,        // active-high, asynchronous
    input                   w_en,
    input  [DATA_WIDTH-1:0] data_in,
    output                  full,
    output                  almost_full,

    // Read domain
    input                   rclk,
    input                   rrst,        // active-high, asynchronous
    input                   r_en,
    output [DATA_WIDTH-1:0] data_out,    // updates after rclk edge with valid r_en
    output                  empty,
    output                  almost_empty
);

    wire [PTR_WIDTH:0]   b_wptr, b_rptr;
    wire [PTR_WIDTH:0]   g_wptr, g_rptr;
    wire [PTR_WIDTH:0]   g_wptr_sync, g_rptr_sync;
    wire [PTR_WIDTH-1:0] w_addr, r_addr;

    fifo_mem #(.DATA_WIDTH(DATA_WIDTH), .PTR_WIDTH(PTR_WIDTH)) fifom (
        .wclk    (wclk),
        .w_en    (w_en && !full),
        .w_addr  (w_addr),
        .data_in (data_in),
        .rclk    (rclk),
        .r_en    (r_en && !empty),
        .r_addr  (r_addr),
        .data_out(data_out)
    );

    wptr_handler #(.PTR_WIDTH(PTR_WIDTH),
                   .ALMOST_FULL_THRESH(ALMOST_FULL_THRESH)) wptr_h (
        .wclk       (wclk),
        .wrst       (wrst),
        .w_en       (w_en),
        .g_rptr_sync(g_rptr_sync),
        .b_wptr     (b_wptr),
        .g_wptr     (g_wptr),
        .full       (full),
        .almost_full(almost_full),
        .w_addr     (w_addr)
    );

    rptr_handler #(.PTR_WIDTH(PTR_WIDTH),
                   .ALMOST_EMPTY_THRESH(ALMOST_EMPTY_THRESH)) rptr_h (
        .rclk        (rclk),
        .rrst        (rrst),
        .r_en        (r_en),
        .g_wptr_sync (g_wptr_sync),
        .b_rptr      (b_rptr),
        .g_rptr      (g_rptr),
        .empty       (empty),
        .almost_empty(almost_empty),
        .r_addr      (r_addr)
    );

    // Gray wptr -> read clock domain
    synchronizer #(.WIDTH(PTR_WIDTH+1)) sync_wptr (
        .clk  (rclk),
        .rst  (rrst),
        .d_in (g_wptr),
        .d_out(g_wptr_sync)
    );

    // Gray rptr -> write clock domain
    synchronizer #(.WIDTH(PTR_WIDTH+1)) sync_rptr (
        .clk  (wclk),
        .rst  (wrst),
        .d_in (g_rptr),
        .d_out(g_rptr_sync)
    );

endmodule
