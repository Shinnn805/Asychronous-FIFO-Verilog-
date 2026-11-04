## Tổng quan dự án
  Thiết kế sử dụng đồng bộ 2 con trỏ Gray code và đồng bộ 2 flip-flop để truyền thông tin con trỏ giữa các miền xung nhịp một cách an toàn, đồng thời giảm thiểu metastability.  
  Các con trỏ Gray sau khi đồng bộ được so sánh trực tiếp để tạo cờ full và empty, không chuyển ngược lại sang nhị phân.  
  Dự án được thiết kế RTL kiểu chia module và SystemVerilog testbench để tự kiểm tra để xác minh chức năng.  

## Tại sao cần FIFO bất đồng bộ?
Trong các hệ thống số hiện đại, các thiết bị thường có tần số  xung nhịp hoạt động khác nhau.  
Ví dụ:  
  Bộ xử lí <-> Ngoại vi  
  Camera <-> pipeline hiển thị  

Truyền trực tiếp các thiết bị nhiều bit ở các miền xung nhịp có thể gây ra metastability và hỏng dữ liệu.  
FIFO bất đồng bộ có thể giải quyết bằng cách:  
  - Đệm dữ liệu giữa 2 miền xung nhịp.  
  - Bảo toàn dữ liệu an toàn.  
  - Chỉ đồng bộ con trỏ điều khiển.
  - Ngăn tràn(overflow) và cạn(underflow).  

## Cấu trúc thư mục

Asynchronous_FIFO/  
│  
├── asynchronous_fifo.v      # Top-level module  
├── fifo_mem.v               # FIFO memory  
├── synchronizer.v           # Two-FF synchronizer  
├── wptr_handler.v           # Write pointer & Full flag  
├── rptr_handler.v           # Read pointer & Empty flag  
├── async_fifo_TB.sv         # Self-checking testbench  
├── README.md  

## Thông số thiết kế  

| Thông số | Mô tả |
|-----------|-------------|
| Language | Verilog HDL |
| Testbench | SystemVerilog |
| FIFO Type | Asynchronous FIFO |
| Synchronization | Gray Code + 2FF Synchronizer |  
| Memory | Dual-Port FIFO Memory |
| Read Clock | Independent |
| Write Clock | Independent |
| Verification | Self-checking Testbench |  
    
## Các module thiết kế chính

1. synchronizer.v  
Hiện thực bộ đồng bộ flip-flop hai tầng để truyền các con trỏ mã Gray giữa các miền xung nhịp bất đồng bộ một cách an toàn.

2. wptr_handler.v  
 -Tạo con trỏ ghi nhị phân  
 -Chuyển đổi sang mã Gray  
 -Tạo cờ Full

3. rptr_handler.v  
  -Tạo con trỏ đọc nhị phân  
  -Chuyển đổi sang mã Gray  
  -Tạo cờ Empty
   
5. fifo_mem.v  
  -Thao tác ghi diễn ra trong miền xung nhịp ghi.  
  -Thao tác đọc diễn ra trong miền xung nhịp đọc.
   
5. asynchronous_fifo.v    
   Module top-level tích hợp:  
      -Bộ nhớ FIFO  
      -Các bộ xử lý con trỏ  
      -Các bộ đồng bộ    

Cung cấp giao diện FIFO hoàn chỉnh cho hệ thống bên ngoài.

## Ứng dụng  

FIFO bất đồng bộ được dùng rộng rãi trong:
  -SoC Interconnect  
  -Cầu nối bus AXI/AHB  
  -DDR Memory Controller  
  -Giao tiếp PCIe  
  -USB Controller  
  -Ethernet MAC  
  -Giao tiếp camera  
  -Pipeline xử lý video  
  -Hệ thống DSP âm thanh 
  -Thiết kế FPGA  
