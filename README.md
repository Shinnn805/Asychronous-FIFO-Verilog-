# Asynchronous FIFO (FIFO Bất Đồng Bộ)  

## Tổng quan dự án  
Dự án hiện thực một bộ **FIFO bất đồng bộ (Asynchronous FIFO)** bằng ngôn ngữ Verilog HDL, phục vụ truyền dữ liệu an toàn giữa hai miền xung nhịp (clock domain) độc lập có tần số và pha khác nhau.  

Thiết kế áp dụng kiến trúc chuẩn công nghiệp (theo Cliff Cummings):  
- Sử dụng **con trỏ mã Gray (Gray Code)** truyền qua **bộ đồng bộ 2 tầng Flip-Flop (2-FF Synchronizer)** để triệt tiêu trạng thái siêu ổn định (metastability).  
- Cờ **Full** và **Empty** được tạo trực tiếp bằng cách so sánh các con trỏ mã Gray, tối ưu tốc độ và giảm trễ logic.  
- Cờ **Almost Full** và **Almost Empty** được tính toán bằng cách giải mã con trỏ Gray đã đồng bộ sang nhị phân (`gray2bin`) để xác định khoảng cách độ đầy (fill level) so với ngưỡng cấu hình.
- Hệ thống kiểm thử toàn diện gồm:  
  - **`golden_model.py`**: Golden Reference Model viết bằng Python 3, mô phỏng cycle-accurate từng chu kỳ xung nhịp và đối soát chéo với hàng đợi lý tưởng (`collections.deque`).  
  - **`async_fifo_TB.sv`**: Self-checking Testbench viết bằng SystemVerilog với Scoreboard và Monitor độc lập, bao phủ kiểm tra chức năng, bảo vệ tràn/cạn và stress test ngẫu nhiên.  

---

## Tại sao cần FIFO bất đồng bộ?
Trong các hệ thống số hiện đại (SoC, FPGA, ASIC), các khối chức năng thường hoạt động trên các miền xung nhịp khác nhau:  
- Bộ xử lý (CPU/DSP) $\leftrightarrow$ Thiết bị ngoại vi (UART, SPI, I2C)  
- Cảm biến Camera $\leftrightarrow$ Bộ xử lý pipeline hiển thị / DDR Controller  

Truyền trực tiếp bus dữ liệu nhiều bit qua ranh giới miền xung nhịp (Clock Domain Crossing - CDC) sẽ gây ra metastability và sai lệch dữ liệu (data corruption). FIFO bất đồng bộ giải quyết vấn đề này bằng cách:
- Đệm dữ liệu qua bộ nhớ Dual-Port RAM.
- Chỉ đồng bộ các con trỏ điều khiển (đã mã hóa Gray - mỗi lần chỉ đổi đúng 1 bit).
- Tự động bảo vệ chống tràn (**Overflow**) và chống cạn (**Underflow**).

---

## Cấu trúc thư mục

```text
Asynchronous_FIFO/
│
├── asynchronous_fifo_top.v   # Top-level module tích hợp FIFO
├── fifo_mem.v                # Dual-Port RAM lưu trữ dữ liệu
├── synchronizer.v            # Bộ đồng bộ 2-FF (chống metastability, có ASYNC_REG)
├── wptr_handler.v            # Xử lý con trỏ ghi, tạo cờ Full & Almost Full
├── rptr_handler.v            # Xử lý con trỏ đọc, tạo cờ Empty & Almost Empty
│
├── golden_model.py           
├── async_fifo_TB.sv          # Self-checking Testbench nâng cao (SystemVerilog)
├── FAP201_Report.pdf.pdf     # Báo cáo đồ án
└── README.md                 # Tài liệu hướng dẫn thiết kế & mô phỏng
```

---

## Thông số thiết kế (Parameters)

| Thông số | Giá trị mặc định | Mô tả |
|:---|:---:|:---|
| `DATA_WIDTH` | `8` | Bề rộng bus dữ liệu vào/ra (bits) |
| `PTR_WIDTH` | `4` (RTL) / `3` (TB) | Số bit địa chỉ; Độ sâu FIFO $DEPTH = 2^{PTR\_WIDTH}$ |
| `ALMOST_FULL_THRESH` | `2` | Ngưỡng kích hoạt `almost_full` khi còn $\le 2$ ô trống |
| `ALMOST_EMPTY_THRESH` | `2` | Ngưỡng kích hoạt `almost_empty` khi còn $\le 2$ phần tử |
| `wclk` (Write Clock) | Độc lập | Xung nhịp miền ghi dữ liệu |
| `rclk` (Read Clock) | Độc lập | Xung nhịp miền đọc dữ liệu |
| `wrst` / `rrst` | Active-High | Tín hiệu reset bất đồng bộ cho từng miền xung nhịp |

---

## Các module thiết kế chính

1. **`synchronizer.v`**:
   - Hiện thực bộ đồng bộ 2 tầng D-Flip-Flop (2-FF).
   - Khai báo chỉ thị `(* ASYNC_REG = "TRUE" *)` để hướng dẫn công cụ tổng hợp / P&R (Vivado, Quartus) đặt 2 FF gần nhau nhất, tối ưu MTBF (Mean Time Between Failures).

2. **`wptr_handler.v`**:
   - Quản lý con trỏ ghi nhị phân (`b_wptr`) và con trỏ mã Gray (`g_wptr`).
   - Tạo địa chỉ ghi RAM: `w_addr = b_wptr[PTR_WIDTH-1:0]`.
   - Tạo cờ **`full`**: Kiểm tra điều kiện đảo 2 bit MSB của `g_wptr` so với `g_rptr_sync`:
     $$\text{wfull} = (g\_wptr\_next == \{\sim g\_rptr\_sync[P:P-1], g\_rptr\_sync[P-2:0]\})$$
   - Tạo cờ **`almost_full`**: Dùng hàm `gray2bin(g_rptr_sync)` tính toán khoảng cách: $fill = b\_wptr\_next - gray2bin(g\_rptr\_sync)$.

3. **`rptr_handler.v`**:
   - Quản lý con trỏ đọc nhị phân (`b_rptr`) và con trỏ mã Gray (`g_rptr`).
   - Tạo địa chỉ đọc RAM: `r_addr = b_rptr[PTR_WIDTH-1:0]`.
   - Tạo cờ **`empty`**: So sánh trực tiếp mã Gray:
     $$\text{rempty} = (g\_rptr\_next == g\_wptr\_sync)$$
   - Tạo cờ **`almost_empty`**: Dùng hàm `gray2bin(g_wptr_sync)` tính: $fill = gray2bin(g\_wptr\_sync) - b\_rptr\_next$.

4. **`fifo_mem.v`**:
   - Bộ nhớ Dual-Port SRAM dung lượng $DEPTH \times DATA\_WIDTH$.
   - Ghi dữ liệu đồng bộ theo cạnh lên `wclk` khi `w_en` tích cực.
   - Đọc dữ liệu dạng registered output theo cạnh lên `rclk` khi `r_en` tích cực.

5. **`asynchronous_fifo_top.v`**:
   - Module đỉnh kết nối các khối chức năng và hai bộ đồng bộ chéo (`sync_wptr`, `sync_rptr`).

---

## Xác minh chức năng (Verification)

Hệ thống xác minh gồm 2 thành phần độc lập:

### 1. SystemVerilog Self-Checking Testbench (`async_fifo_TB.sv`)
Testbench tích hợp **Scoreboard** và **Monitor** độc lập ở cả 2 miền xung nhịp, tự động đối soát toàn vẹn dữ liệu và kiểm tra các cờ trạng thái:
- **TC1 - Ghi/Đọc cơ bản**: Ghi liên tục 8 giá trị (`0x10..0x17`) mỗi chu kỳ, kiểm tra cờ `full` nhảy lên 1 và `empty` về 0 sau khi đồng bộ; đọc toàn bộ và kiểm tra thứ tự FIFO.
- **TC2 - Kiểm tra cờ & Chống tràn/cạn**:
  - Ghi 6 phần tử $\rightarrow$ xác minh `almost_full = 1`, `full = 0`.
  - Ghi tiếp 2 phần tử $\rightarrow$ xác minh `full = 1`.
  - **Overflow check**: Cố tình ghi thêm 5 lần khi đã Full $\rightarrow$ đảm bảo dữ liệu không bị ghi đè, con trỏ ghi không tăng.  
  - Đọc tuần tự $\rightarrow$ xác minh ngưỡng chuyển trạng thái của `almost_empty`.  
  - **Underflow check**: Cố tình đọc khi Empty $\rightarrow$ đảm bảo không đọc dữ liệu rác, con trỏ đọc không tăng.  
  - Lặp lại quy trình trong 3 vòng quay con trỏ (wrap-around).  
- **TC3 - Concurrent Stress Test**:  
  - Chạy đồng thời luồng ghi và luồng đọc ngẫu nhiên bằng `fork ... join`.  
  - Kiểm thử qua 5 phase với các tỉ lệ xung nhịp khác nhau:  
    1. `wclk` nhanh (50 MHz), `rclk` chậm (~14.28 MHz) $\rightarrow$ kiểm tra FIFO thường xuyên bị Full.  
    2. `wclk` chậm (~14.28 MHz), `rclk` nhanh (50 MHz) $\rightarrow$ kiểm tra FIFO thường xuyên bị Empty.    
    3. Tần số gần bằng nhau (50 MHz vs 45.45 MHz).  
    4. Ghi/đọc liên tục mỗi chu kỳ (back-to-back transfer).  
    5. Cùng tần số xung nhịp.  
  - Tổng số giao dịch kiểm thử lên đến hàng nghìn transactions với số lần con trỏ quay vòng $> 200$ lần.  



## Ứng dụng
FIFO bất đồng bộ được ứng dụng rộng rãi trong:
- SoC Interconnect & Cầu nối bus AXI/AHB
- Bộ điều khiển bộ nhớ DDR (DDR Memory Controller)
- Giao tiếp PCIe, USB 3.0/2.0, Ethernet MAC
- Pipeline xử lý hình ảnh và video từ cảm biến Camera
- Hệ thống DSP âm thanh đa miền xung nhịp
- Các thiết kế FPGA và ASIC đa miền clock (Multi-clock domain designs)
