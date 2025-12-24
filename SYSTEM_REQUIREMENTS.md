# System Requirements - SafeQuery

Để ứng dụng **SafeQuery** hoạt động ổn định trên máy tính của bạn, vui lòng đảm bảo các yêu cầu sau được đáp ứng:

## 1. Yêu cầu Hệ điều hành
- **Windows 10 hoặc 11** (Hỗ trợ tốt nhất).
- Quyền truy cập mạng tới Server SQL Server.

## 2. Phần mềm cần thiết (Prerequisites)
### 🐍 Python
- **Phiên bản**: Python 3.8 trở lên.
- **Tải về**: [python.org](https://www.python.org/downloads/)

### 🗄️ Microsoft ODBC Driver for SQL Server (QUAN TRỌNG)
Đây là thư viện giúp Python kết nới với SQL Server. Nếu thiếu bản này, bạn sẽ gặp lỗi `IM002`.
- **Phiên bản khuyến nghị**: ODBC Driver 17 hoặc 18.
- **Link tải**: [Microsoft ODBC Driver Download](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
  - *Lưu ý: Bạn nên tải bản x64 nếu dùng Windows 64-bit.*

## 3. Thư viện Python (Dependencies)
Nếu bạn chạy từ mã nguồn (.py), hãy cài đặt các thư viện sau:
```bash
pip install pyodbc pygments
```

## 4. Quyền truy cập (Authentication)
- Ứng dụng này sử dụng **Windows Authentication** (Trusted Connection). 
- Tài khoản Windows đang đăng nhập vào máy tính của bạn phải có quyền `SELECT` trên Database đích.

## 5. Khắc phục sự cố nhanh
- **Lỗi Driver not found**: Cài đặt link ở mục số 2 phía trên.
- **Lỗi Login failed**: Kiểm tra lại quyền hạn của tài khoản Windows của bạn trên SQL Server.
- **Lỗi Timeout**: Kiểm tra kết nối mạng (VPN nếu làm việc từ xa) tới Server.
