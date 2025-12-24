# Công cụ Truy vấn An toàn (BA Safe Query)

## 1. Tổng quan
**BA Safe Query** là một ứng dụng Python (Giao diện Tkinter) được thiết kế riêng cho các Business Analyst (BA) hoặc người dùng cần truy vấn dữ liệu từ SQL Server một cách nhanh chóng, trực quan và đặc biệt là **an toàn**. 

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

## 3. Chi tiết Giao diện

### Khu vực Cấu hình (Top)
- **Server & Database:** Cho phép chọn máy chủ và cơ sở dữ liệu (Mặc định: `Pa-vm90` / `LiveEpicor1015`).
- **Windows Authentication:** Tự động sử dụng tài khoản Windows đang đăng nhập (Trusted Connection), không cần nhập mật khẩu thủ công.

### Khu vực Nhập liệu (Middle)
- **SQL Editor:** Sử dụng font chữ `Consolas` chuyên dụng cho lập trình.
- **Phím tắt F5:** Nhấn F5 để thực thi câu lệnh nhanh chóng giống như trong SQL Management Studio.
- **Chạy vùng chọn:** Nếu bạn bôi đen một đoạn code, tool sẽ chỉ thực hiện đoạn đó.

### Khu vực Kết quả (Bottom)
- **Canvas cuộn dọc:** Toàn bộ các bảng kết quả được đặt trong một vùng cuộn lớn.
- **Thanh công cụ riêng:** Mỗi bảng kết quả đều có nút **Copy** và **Save CSV** riêng biệt.
- **Trạng thái (StatusBar):** Hiển thị thời gian thực thi chi tiết đến từng mili giây và tổng số dòng dữ liệu.

---

## 4. Xử lý Lỗi Thông minh
Ứng dụng dịch các mã lỗi SQL thô cứng thành thông báo tiếng Việt dễ hiểu:
- **Timeout:** "⏱️ Hệ thống bận."
- **Quá tải:** "🛑 Query quá nặng."
- **Đăng nhập:** "🔐 Kiểm tra Server/DB hoặc Quyền Windows."

---

## 5. Hướng dẫn Sử dụng & Xuất dữ liệu
- **Copy to Excel:** Nhấn nút "COPY TẤT CẢ" để đưa toàn bộ các bảng vào Clipboard. Định dạng Tab-separated giúp dán trực tiếp vào Excel mà không bị lệch cột.
- **Save CSV:** Xuất dữ liệu ra file `.csv` với mã hóa `utf-8-sig` (đảm bảo không lỗi font tiếng Việt khi mở bằng Excel).
- **Cuộn chuột:** Hỗ trợ cuộn chuột trên toàn bộ vùng kết quả để duyệt dữ liệu nhanh.

---

## 6. Yêu cầu Hệ thống
- **Ngôn ngữ:** Python 3.x
- **Thư viện:** `pyodbc`, `tkinter`
- **Driver:** Microsoft ODBC Driver 17 for SQL Server.
