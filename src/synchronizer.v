module synchronizer #(
    parameter WIDTH = 5
)(
    input                  clk,
    input                  rst,
    input  [WIDTH-1:0]     d_in,
    output reg [WIDTH-1:0] d_out
);

    (* ASYNC_REG = "TRUE" *) reg [WIDTH-1:0] stage1;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            stage1 <= {WIDTH{1'b0}};
            d_out  <= {WIDTH{1'b0}};
        end else begin
            stage1 <= d_in;
            d_out  <= stage1;
        end
    end

endmodule
