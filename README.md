# Công cụ Truy vấn An toàn (SafeQuery)

## 1. Tổng quan
**SafeQuery** là một ứng dụng Python (Giao diện Tkinter) được thiết kế riêng cho các Business Analyst (BA) hoặc người dùng cần truy vấn dữ liệu từ SQL Server một cách nhanh chóng, trực quan và đặc biệt là **an toàn**. 

Ứng dụng giúp ngăn chặn các rủi ro làm treo hệ thống hoặc thay đổi dữ liệu ngoài ý muốn bằng các lớp bảo vệ phần cứng và phần mềm tích hợp sẵn.

---

## 2. Các Tính Năng Nổi Bật

### 🛡️ Cơ chế An toàn Tuyệt đối (Safety First)
- **Chặn lệnh ghi dữ liệu:** Hệ thống tự động kiểm tra và chặn các từ khóa nguy hiểm như `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `INSERT`. Chỉ cho phép lệnh `SELECT`.
- **Cấu hình SQL bảo vệ (Safety Injection):** Mỗi câu truy vấn khi gửi đi đều được đính kèm các thiết lập hệ thống:
    - `SET DEADLOCK_PRIORITY LOW`: Ưu tiên giải phóng tài nguyên nếu xảy ra tranh chấp (Deadlock).
    - `SET LOCK_TIMEOUT 3000`: Tự động ngắt nếu bảng bị khóa quá 3 giây.
    - `SET QUERY_GOVERNOR_COST_LIMIT 3000`: Ngăn chặn các câu lệnh quá nặng gây tốn tài nguyên server.
    - `SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED`: Cho phép đọc dữ liệu mà không gây khóa bảng (Dirty Read), tối ưu cho báo cáo.

### 🚀 Hiệu năng & Đa luồng (Multi-threading)
- **Không treo giao diện:** Quá trình kết nối và truy vấn được thực hiện trên một luồng (thread) riêng biệt. Người dùng vẫn có thể thao tác trên UI trong khi chờ dữ liệu trả về.
- **Xử lý Multi-Result Set:** Hỗ trợ hiển thị nhiều bảng kết quả cùng lúc nếu câu lệnh SQL trả về nhiều tập dữ liệu.

### 📊 Trải nghiệm Người dùng (UI/UX)
- **Bảng dữ liệu thông minh:**
    - **Zebra Stripping:** Hiệu ứng dòng kẻ sọc (trắng/xám) giúp dễ theo dõi dữ liệu dọc.
    - **Dynamic Height:** Chiều cao mỗi bảng tự động điều chỉnh theo số dòng (tối đa 18 dòng trước khi xuất hiện thanh cuộn riêng).
    - **Auto-width:** Tự động tính toán chiều rộng cột dựa trên độ dài tiêu đề.
- **Giới hạn hiển thị:** Chỉ hiển thị tối đa 1000 dòng đầu tiên trên giao diện để đảm bảo ứng dụng luôn mượt mà, nhưng vẫn cho phép xuất toàn bộ dữ liệu ra file.

---

## 3. Cài đặt và Chạy Ứng dụng

### Yêu cầu Hệ thống
- **Hệ điều hành:** Windows 10 hoặc 11 (hỗ trợ tốt nhất).
- **Python:** Phiên bản 3.8 trở lên.
- **ODBC Driver:** Microsoft ODBC Driver 17 hoặc 18 for SQL Server.
- **Quyền truy cập:** Tài khoản Windows có quyền SELECT trên database đích.

### Cài đặt
1. **Cài đặt Python:** Tải từ [python.org](https://www.python.org/downloads/).
2. **Cài đặt ODBC Driver:** Tải từ [Microsoft Download](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).
3. **Cài đặt thư viện Python:**
   ```bash
   pip install -r requirements.txt
   ```

### Chạy Ứng dụng
- **Từ mã nguồn:**
  ```bash
  python app.py
  ```
- **Từ file executable (nếu có):** Chạy file `SafeQuery.exe` trực tiếp.

---

## 4. Chi tiết Giao diện

### Khu vực Cấu hình (Top)
- **Server & Database:** Cho phép chọn máy chủ và cơ sở dữ liệu từ danh sách lịch sử.
- **Driver:** Tự động chọn driver ODBC tốt nhất có sẵn.
- **Windows Authentication:** Tự động sử dụng tài khoản Windows đang đăng nhập (Trusted Connection), không cần nhập mật khẩu thủ công.

### Khu vực Nhập liệu (Middle)
- **SQL Editor:** Sử dụng font chữ `Consolas` chuyên dụng cho lập trình, với syntax highlighting.
- **Phím tắt F5:** Nhấn F5 để thực thi câu lệnh nhanh chóng giống như trong SQL Management Studio.
- **Chạy vùng chọn:** Nếu bạn bôi đen một đoạn code, tool sẽ chỉ thực hiện đoạn đó.

### Khu vực Kết quả (Bottom)
- **Canvas cuộn dọc:** Toàn bộ các bảng kết quả được đặt trong một vùng cuộn lớn.
- **Thanh công cụ riêng:** Mỗi bảng kết quả đều có nút **Copy** và **Save CSV** riêng biệt.
- **Trạng thái (StatusBar):** Hiển thị thời gian thực thi chi tiết đến từng mili giây và tổng số dòng dữ liệu.

---

## 5. Xử lý Lỗi Thông minh
Ứng dụng dịch các mã lỗi SQL thô cứng thành thông báo tiếng Việt dễ hiểu:
- **Timeout:** "⏱️ LỖI TIMEOUT: Hệ thống bận bị lock quá 3 giây."
- **Quá tải:** "🛑 LỖI QUÁ TẢI: Query quá nặng. Chi phí Est thực thi quá 3000 Cost"
- **Đăng nhập:** "🔐 LỖI ĐĂNG NHẬP: Kiểm tra Server/DB hoặc Quyền Windows."

---

## 6. Hướng dẫn Sử dụng & Xuất dữ liệu
- **Copy to Excel:** Nhấn nút "COPY TẤT CẢ" để đưa toàn bộ các bảng vào Clipboard. Định dạng Tab-separated giúp dán trực tiếp vào Excel mà không bị lệch cột.
- **Save CSV:** Xuất dữ liệu ra file `.csv` với mã hóa `utf-8-sig` (đảm bảo không lỗi font tiếng Việt khi mở bằng Excel).
- **Cuộn chuột:** Hỗ trợ cuộn chuột trên toàn bộ vùng kết quả để duyệt dữ liệu nhanh.

### Ví dụ Sử dụng
1. Chọn Server và Database.
2. Nhập câu lệnh SQL SELECT, ví dụ:
   ```sql
   SELECT TOP 10 * FROM Customers;
   ```
3. Nhấn F5 hoặc nút "CHẠY TRUY VẤN".
4. Xem kết quả và xuất dữ liệu nếu cần.

---

## 7. Khắc phục Sự cố
- **Lỗi Driver not found:** Cài đặt Microsoft ODBC Driver.
- **Lỗi Login failed:** Kiểm tra quyền truy cập Windows trên SQL Server.
- **Lỗi Timeout:** Kiểm tra kết nối mạng hoặc giảm tải query.
- Xem chi tiết trong file `SYSTEM_REQUIREMENTS.md`.

---

## 8. Đóng góp
Nếu bạn muốn đóng góp, vui lòng tạo issue hoặc pull request trên GitHub.

## 9. Giấy phép
Dự án này được phân phối dưới giấy phép Apache License 2.0. Xem file `LICENSE` để biết thêm chi tiết.

---

*Tác giả: tranlammankg*
