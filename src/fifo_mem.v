module fifo_mem #(
    parameter DATA_WIDTH = 8,
    parameter PTR_WIDTH  = 4
)(
    input                       wclk,
    input                       w_en,
    input  [PTR_WIDTH-1:0]      w_addr,
    input  [DATA_WIDTH-1:0]     data_in,

    input                       rclk,
    input                       r_en,
    input  [PTR_WIDTH-1:0]      r_addr,
    output reg [DATA_WIDTH-1:0] data_out
);

    localparam DEPTH = (1 << PTR_WIDTH);

    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    always @(posedge wclk) begin
        if (w_en)
            mem[w_addr] <= data_in;
    end

    always @(posedge rclk) begin
        if (r_en)
            data_out <= mem[r_addr];
    end

endmodule
