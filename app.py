import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import pyodbc
import threading
import csv
import io
import time
from pygments import lex
from pygments.lexers import SqlLexer
from pygments.styles import get_style_by_name
import re
import json
import os
import sys

# =================================================================================
# CẤU HÌNH MẶC ĐỊNH
# =================================================================================
DEFAULT_SERVER = ""
DEFAULT_DB = ""

# CÁC LỆNH BẢO VỆ HỆ THỐNG (HARDCODED)
SAFETY_INJECTION = """
SET DEADLOCK_PRIORITY LOW;
SET LOCK_TIMEOUT 3000;              -- 3 giây
SET QUERY_GOVERNOR_COST_LIMIT 3000; -- Cost limit
"""

# Xử lý đường dẫn file config cho file đóng gói (PyInstaller)
if getattr(sys, 'frozen', False):
    # Nếu đang chạy file .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Nếu đang chạy script .py bình thường
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

class LineNumberCanvas(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.text_widget = None

    def set_text_widget(self, text_widget):
        self.text_widget = text_widget

    def redraw(self):
        self.delete("all")
        if not self.text_widget: return

        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(25, y, anchor="ne", text=linenum, fill="#adb5bd", font=("Consolas", 10))
            i = self.text_widget.index("%s+1line" % i)

class CustomScrolledText(scrolledtext.ScrolledText):
    def __init__(self, *args, **kwargs):
        scrolledtext.ScrolledText.__init__(self, *args, **kwargs)
        self.line_numbers = None
        self.lexer = SqlLexer()
        self._highlight_timer = None
        
        # Cấu hình màu sắc (Gần giống Notepad++ SQL)
        self.tag_configure("Token.Keyword", foreground="#0000FF", font=("Consolas", 11, "bold"))
        self.tag_configure("Token.Keyword.Declaration", foreground="#0000FF", font=("Consolas", 11, "bold"))
        self.tag_configure("Token.Operator", foreground="#800000")
        self.tag_configure("Token.String", foreground="#FF0000")
        self.tag_configure("Token.Literal.String.Single", foreground="#FF0000")
        self.tag_configure("Token.Literal.Number.Integer", foreground="#FF00FF")
        self.tag_configure("Token.Comment.Single", foreground="#008000")
        self.tag_configure("Token.Comment.Multiline", foreground="#008000")
        self.tag_configure("Token.Name.Builtin", foreground="#0000FF")
        self.tag_configure("Token.Name.Function", foreground="#808000")

        self.bind("<<Modified>>", self._on_modified)
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<MouseWheel>", self._on_scroll)
        self.vbar.bind("<B1-Motion>", self._on_scroll)
        self.vbar.bind("<Button-1>", self._on_scroll)

    def set_line_numbers(self, line_numbers):
        self.line_numbers = line_numbers

    def _on_scroll(self, event=None):
        if self.line_numbers:
            self.after_idle(self.line_numbers.redraw)

    def _on_key_release(self, event=None):
        if event and event.keysym in ("Up", "Down", "Prior", "Next", "Home", "End"):
            self._on_scroll()

    def _on_modified(self, event=None):
        if self.edit_modified():
            self._trigger_highlight()
            if self.line_numbers:
                self.line_numbers.redraw()
            self.edit_modified(False)

    def _trigger_highlight(self):
        if self._highlight_timer:
            self.after_cancel(self._highlight_timer)
        self._highlight_timer = self.after(100, self.highlight_all)

    def highlight_all(self):
        content = self.get("1.0", tk.END)
        for tag in self.tag_names():
            if tag.startswith("Token."):
                self.tag_remove(tag, "1.0", tk.END)

        for index, token_type, value in self.lexer.get_tokens_unprocessed(content):
            tag = str(token_type)
            if tag.startswith("Token."):
                start = f"1.0 + {index} chars"
                end = f"1.0 + {index + len(value)} chars"
                self.tag_add(tag, start, end)
        
        self._on_scroll() # Cập nhật lại số dòng nếu cần

class VirtualTreeview(tk.Frame):
    def __init__(self, parent, columns, data, height=18, **kwargs):
        super().__init__(parent, background="white", **kwargs)
        self.columns = columns
        self.all_data = data
        self.height = height
        self.current_offset = 0
        
        # Chuyển đổi dữ liệu sang string để hiển thị
        self.formatted_data = []
        for row in data:
            self.formatted_data.append([str(item) if item is not None else "" for item in row])

        # Treeview để hiển thị
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=height)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.tag_configure('oddrow', background="#f2f2f2")
        self.tree.tag_configure('evenrow', background="white")

        for col in columns:
            self.tree.heading(col, text=col)
            w = max(100, len(col) * 10)
            self.tree.column(col, width=w, anchor="w", stretch=False)

        # Thanh cuộn dọc
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self._on_scrollbar_move)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Thanh cuộn ngang
        self.hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=self.hsb.set, yscrollcommand=self.vsb.set)
        self.hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Bind sự kiện cuộn chuột
        self.tree.bind("<MouseWheel>", self._on_mousewheel)

        # Khởi tạo các ID dòng (reuse row objects)
        self.item_ids = []
        num_to_create = min(len(self.formatted_data), self.height)
        for i in range(num_to_create):
            item_id = self.tree.insert("", "end", values=self.formatted_data[i])
            self.item_ids.append(item_id)
        
        self._update_scrollbar()
        self._refresh_display()

    def _update_scrollbar(self):
        if not self.formatted_data:
            self.vsb.set(0, 1)
            return
        
        total = len(self.formatted_data)
        if total <= self.height:
            self.vsb.set(0, 1)
        else:
            first = self.current_offset / total
            last = (self.current_offset + self.height) / total
            self.vsb.set(first, last)

    def _on_scrollbar_move(self, *args):
        if not self.formatted_data or len(self.formatted_data) <= self.height:
            return

        cmd = args[0]
        total = len(self.formatted_data)
        
        if cmd == "scroll":
            number = int(args[1])
            units = args[2]
            if units == "units":
                self.current_offset += number
            elif units == "pages":
                self.current_offset += number * self.height
        elif cmd == "moveto":
            fraction = float(args[1])
            self.current_offset = int(fraction * total)

        self._clamp_offset()
        self._refresh_display()
        self._update_scrollbar()

    def _on_mousewheel(self, event):
        if not self.formatted_data or len(self.formatted_data) <= self.height:
            return
            
        if event.delta < 0:
            self.current_offset += 2 # Cuộn nhanh hơn 1 chút
        else:
            self.current_offset -= 2
        
        self._clamp_offset()
        self._refresh_display()
        self._update_scrollbar()
        return "break" # Ngăn việc cuộn frame cha khi đang hover trên bảng

    def _clamp_offset(self):
        total = len(self.formatted_data)
        max_offset = max(0, total - self.height)
        if self.current_offset < 0:
            self.current_offset = 0
        if self.current_offset > max_offset:
            self.current_offset = max_offset

    def _refresh_display(self):
        for i, item_id in enumerate(self.item_ids):
            data_idx = self.current_offset + i
            if data_idx < len(self.formatted_data):
                tag = 'evenrow' if data_idx % 2 == 0 else 'oddrow'
                self.tree.item(item_id, values=self.formatted_data[data_idx], tags=(tag,))

class SafeQueryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Công cụ Truy vấn An toàn (Safe Query)")
        self.root.geometry("1100x850") # Tăng kích thước cửa sổ
        self.root.configure(bg="#f8f9fa") # Màu nền dịu mắt hơn
        
        # Thêm style cho Treeview Header đậm và màu sắc hiện đại
        self.style = ttk.Style()
        self.style.theme_use("clam") # Dùng theme clam để dễ tùy biến màu sắc
        
        self.style.configure("Treeview", 
                            background="white", 
                            fieldbackground="white", 
                            rowheight=25, 
                            font=("Arial", 9))
        
        self.style.configure("Treeview.Heading", 
                            font=("Arial", 9, "bold"), 
                            background="#e9ecef", 
                            foreground="#495057")
        
        # Màu khi chọn dòng
        self.style.map("Treeview", background=[('selected', '#007acc')])

        # Biến lưu trữ kết quả tạm để Export
        self.last_results = [] # Lưu danh sách (columns, rows) cho từng kết quả
        self.current_conn = None # Lưu kết nối đang chạy để Stop

        # Tải cấu hình
        self.config = self.load_config()

        # --- Giao diện nhập liệu ---
        frame_top = tk.Frame(root, pady=10, bg="#f8f9fa")
        frame_top.pack(fill=tk.X, padx=15)
        
        # --- Config Section (Server & Database) ---
        config_frame = tk.LabelFrame(frame_top, text="⚡ Cấu hình Kết nối", padx=15, pady=10, 
                                     bg="#ffffff", font=("Segoe UI", 10, "bold"), fg="#1a73e8",
                                     relief="flat", highlightthickness=1, highlightbackground="#e0e0e0")
        config_frame.pack(fill=tk.X, pady=(0, 15))

        # Grid configuration for better layout
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)
        config_frame.columnconfigure(5, weight=2)

        # Server Selection
        tk.Label(config_frame, text="🖥️ Server:", bg="#ffffff", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.cbo_server = ttk.Combobox(config_frame, values=self.config.get("servers", [DEFAULT_SERVER]), width=20)
        self.cbo_server.set(self.config.get("last_server", DEFAULT_SERVER))
        self.cbo_server.grid(row=0, column=1, sticky="ew", padx=(0, 15))

        # Database Selection
        tk.Label(config_frame, text="🗄️ Database:", bg="#ffffff", font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.cbo_database = ttk.Combobox(config_frame, values=self.config.get("databases", [DEFAULT_DB]), width=20)
        self.cbo_database.set(self.config.get("last_database", DEFAULT_DB))
        self.cbo_database.grid(row=0, column=3, sticky="ew", padx=(0, 15))
        
        # Driver Selection
        tk.Label(config_frame, text="⚙️ Driver:", bg="#ffffff", font=("Segoe UI", 9)).grid(row=0, column=4, sticky="w", padx=(0, 5))
        self.all_drivers = self.get_sql_drivers()
        self.cbo_driver = ttk.Combobox(config_frame, values=self.all_drivers, width=30, state="readonly")
        
        # Chọn driver tốt nhất mặc định
        best_driver = self.config.get("last_driver")
        if not best_driver or best_driver not in self.all_drivers:
            best_driver = self.get_best_driver(self.all_drivers)

        if best_driver in self.all_drivers:
            self.cbo_driver.set(best_driver)
        elif self.all_drivers:
            self.cbo_driver.current(0)
            
        self.cbo_driver.grid(row=0, column=5, sticky="ew")
        self.driver = self.cbo_driver.get()
        
        # Bind sự kiện thay đổi driver
        self.cbo_driver.bind("<<ComboboxSelected>>", self.on_driver_change)

        # Hàng thứ 2: Nút Test Connection
        self.btn_test_conn = tk.Button(config_frame, text="🔍 Kiểm tra Kết nối", command=self.test_connection,
                                      bg="#f1f3f4", fg="#3c4043", font=("Segoe UI", 8),
                                      relief="flat", padx=10, cursor="hand2")
        self.btn_test_conn.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        if not self.all_drivers:
            self.lbl_no_driver = tk.Label(config_frame, text="⚠️ Không tìm thấy SQL Driver", 
                                          font=("Segoe UI", 8, "bold"), fg="#d93025", bg="#ffffff")
            self.lbl_no_driver.grid(row=1, column=4, columnspan=2, sticky="e", pady=(10, 0))

        # Query Section
        self.lbl_query_desc = tk.Label(frame_top, text="Nhập câu lệnh SQL (SELECT only):", 
                 font=("Arial", 10, "bold"), bg="#f8f9fa", fg="#212529")
        self.lbl_query_desc.pack(anchor="w")
        tk.Label(frame_top, text="(Đang đăng nhập bằng tài khoản Windows của bạn)", 
                 font=("Arial", 8, "italic"), fg="#6c757d", bg="#f8f9fa").pack(anchor="w")
        
        # --- Nhãn hiển thị lỗi Inline (Thay cho popup) ---
        self.lbl_error = tk.Label(frame_top, text="", font=("Segoe UI", 9), fg="#d0021b", bg="#fff5f5", 
                                  anchor="w", justify="left", wraplength=1050, padx=10, pady=5,
                                  highlightthickness=1, highlightbackground="#fcd3d3")
        # Không pack ngay, chỉ pack khi có lỗi
        editor_frame = tk.Frame(frame_top, bg="white", highlightthickness=1, highlightbackground="#ced4da")
        editor_frame.pack(fill=tk.X, pady=5)

        self.line_numbers = LineNumberCanvas(editor_frame, width=30, bg="#f1f3f5", highlightthickness=0)
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.txt_query = CustomScrolledText(editor_frame, height=12, font=("Consolas", 11), undo=True)
        self.txt_query.pack(fill=tk.X, side=tk.LEFT, expand=True)

        # Kết nối Line Numbers với Text
        self.txt_query.set_line_numbers(self.line_numbers)
        self.line_numbers.set_text_widget(self.txt_query)
        
        btn_frame = tk.Frame(frame_top, bg="#f8f9fa")
        btn_frame.pack(fill=tk.X)
        
        # Nút Chạy
        self.btn_run = tk.Button(btn_frame, text="▶ CHẠY TRUY VẤN (F5)", command=self.run_query_thread, 
                                 bg="#007acc", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5)
        self.btn_run.pack(side=tk.LEFT)

        # Nút Stop
        self.btn_stop = tk.Button(btn_frame, text="🛑 STOP", command=self.stop_query, 
                                  bg="#dc3545", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        # Nút Copy
        self.btn_copy = tk.Button(btn_frame, text="📋 COPY TẤT CẢ (Excel)", command=self.copy_to_clipboard,
                                  state=tk.DISABLED, font=("Arial", 9), padx=10)
        self.btn_copy.pack(side=tk.LEFT, padx=5)

        # Nút Lưu CSV
        self.btn_save = tk.Button(btn_frame, text="💾 LƯU CSV TẤT CẢ", command=self.save_to_csv,
                                  state=tk.DISABLED, font=("Arial", 9), padx=10)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        self.lbl_status = tk.Label(btn_frame, text="Ready", fg="#495057", bg="#f8f9fa")
        self.lbl_status.pack(side=tk.LEFT, padx=20)

        # --- Giao diện kết quả (Sử dụng Canvas cuộn dọc cho nhiều bảng) ---
        self.frame_results_container = tk.Frame(root, bg="#f8f9fa")
        self.frame_results_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.frame_results_container, bg="#f8f9fa", highlightthickness=0)
        self.scrollbar_v = ttk.Scrollbar(self.frame_results_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f8f9fa")

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar_v.pack(side="right", fill="y")

        # Khung chứa nội dung thực tế bên trong canvas
        self.scroll_window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar_v.set)

        # Tự động cập nhật vùng cuộn khi size frame thay đổi
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # QUAN TRỌNG: Ép frame bên trong phải giãn bằng chiều rộng canvas
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.scroll_window_id, width=e.width)
        )

        # Hỗ trợ cuộn chuột
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Bind phím tắt F5
        self.root.bind('<F5>', lambda event: self.run_query_thread())

    def get_sql_drivers(self):
        """Lấy danh sách tất cả các driver SQL Server có sẵn"""
        drivers = pyodbc.drivers()
        sql_drivers = [d for d in drivers if "SQL Server" in d or "ODBC Driver" in d]
        return sql_drivers

    def get_best_driver(self, drivers):
        """Tự động tìm driver SQL Server tốt nhất trong danh sách"""
        # Ưu tiên các bản ODBC Driver mới
        priority = [
            'ODBC Driver 17 for SQL Server',
            'ODBC Driver 18 for SQL Server',
            'ODBC Driver 13 for SQL Server',
            'SQL Server Native Client 11.0',
            'SQL Server'
        ]
        for p in priority:
            if p in drivers:
                return p
        return drivers[0] if drivers else None

    def on_driver_change(self, event):
        """Cập nhật driver khi người dùng chọn trong combobox"""
        self.driver = self.cbo_driver.get()
        self.lbl_status.config(text=f"Đã đổi sang driver: {self.driver}", fg="blue")
        self.save_config()

    def load_config(self):
        """Tải cấu hình từ file JSON"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"servers": [DEFAULT_SERVER], "databases": [DEFAULT_DB]}

    def save_config(self):
        """Lưu cấu hình hiện tại vào file JSON"""
        config = {
            "servers": list(self.cbo_server['values']),
            "databases": list(self.cbo_database['values']),
            "last_server": self.cbo_server.get(),
            "last_database": self.cbo_database.get(),
            "last_driver": self.cbo_driver.get()
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except:
            pass

    def add_to_history(self, server, database):
        """Thêm server và database vào lịch sử nếu chưa có"""
        servers = list(self.cbo_server['values'])
        databases = list(self.cbo_database['values'])

        changed = False
        if server and server not in servers:
            servers.insert(0, server)
            self.cbo_server['values'] = servers
            changed = True
        
        if database and database not in databases:
            databases.insert(0, database)
            self.cbo_database['values'] = databases
            changed = True

        if changed:
            self.save_config()

    def test_connection(self):
        """Kiểm tra kết nối tới server/database"""
        server = self.cbo_server.get()
        database = self.cbo_database.get()
        driver = self.cbo_driver.get()

        if not server or not database:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Server và Database!")
            return

        self.lbl_status.config(text=f"Đang thử kết nối tới {server}...", fg="blue")
        self.btn_test_conn.config(state=tk.DISABLED)

        def check():
            try:
                conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
                conn = pyodbc.connect(conn_str, timeout=5)
                conn.close()
                self.root.after(0, lambda: messagebox.showinfo("Thành công", f"Kết nối tới {server} thành công!"))
                self.root.after(0, lambda: self.lbl_status.config(text="Kết nối thành công", fg="green"))
                self.root.after(0, lambda: self.add_to_history(server, database))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Thất bại", f"Không thể kết nối:\n{str(e)}"))
                self.root.after(0, lambda: self.lbl_status.config(text="Kết nối thất bại", fg="red"))
            finally:
                self.root.after(0, lambda: self.btn_test_conn.config(state=tk.NORMAL))

        threading.Thread(target=check, daemon=True).start()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def stop_query(self):
        """Ngắt kết nối đang chạy"""
        if self.current_conn:
            try:
                self.lbl_status.config(text="Đang dừng câu lệnh...", fg="red")
                self.current_conn.close()
                self.current_conn = None
            except:
                pass

    def run_query_thread(self):
        """Chạy query trong luồng riêng để không treo giao diện"""
        if self.txt_query.tag_ranges(tk.SEL):
            query = self.txt_query.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
        else:
            query = self.txt_query.get("1.0", tk.END).strip()

        if not query:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập câu lệnh SQL!")
            return

        forbidden = ['UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 'INSERT']
        if any(word in query.upper() for word in forbidden):
            messagebox.showerror("Bị chặn", "Tool này chỉ cho phép chạy SELECT để đảm bảo an toàn!")
            return

        self.btn_run.config(state=tk.DISABLED, text="Đang chạy...")
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_copy.config(state=tk.DISABLED)
        self.btn_save.config(state=tk.DISABLED)
        self.lbl_status.config(text="Đang kết nối và thực thi...", fg="blue")
        
        # Xóa lỗi cũ
        self.lbl_error.config(text="")
        self.lbl_error.pack_forget()
        
        # Xóa các bảng cũ
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.last_results = []

        server = self.cbo_server.get()
        database = self.cbo_database.get()
        
        # Thêm vào history và lưu config ngay khi bắt đầu chạy
        self.add_to_history(server, database)

        thread = threading.Thread(target=self.execute_sql, args=(query, server, database))
        thread.start()

    def execute_sql(self, user_query, server, database):
        self.current_conn = None
        if not self.driver:
            self.root.after(0, self.update_ui_state, [], "LỖI: Máy tính chưa cài đặt ODBC Driver cho SQL Server. Vui lòng xem file SYSTEM_REQUIREMENTS.md")
            return

        all_results = []
        start_time = time.time()
        try:
            conn_str = f"DRIVER={{{self.driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
            self.current_conn = pyodbc.connect(conn_str, timeout=10) 
            cursor = self.current_conn.cursor()
            cursor.execute(SAFETY_INJECTION)
            cursor.execute(user_query)

            while True:
                try:
                    if cursor.description:
                        columns = [column[0] for column in cursor.description]
                        rows = cursor.fetchall()
                        elapsed = time.time() - start_time
                        all_results.append((columns, rows, elapsed))
                except Exception as e:
                    # Nếu lỗi ở một result set tiếp theo, dừng loop và báo lỗi nhưng giữ kết quả cũ
                    self.root.after(0, self.update_ui_state, all_results, str(e))
                    return

                if not cursor.nextset():
                    break

            self.root.after(0, self.update_ui_state, all_results, None)

        except Exception as e:
            error_msg = str(e)
            if self.current_conn is None and ('cursor' in error_msg.lower() or 'connection' in error_msg.lower()):
                friendly_msg = "⏹️ ĐÃ DỪNG: Câu lệnh đã được dừng bởi người dùng."
                self.root.after(0, self.update_ui_state, all_results, friendly_msg)
                return

            friendly_msg = f"Lỗi: {error_msg}"
            if '1222' in error_msg or 'timeout' in error_msg.lower():
                friendly_msg = "⏱️ LỖI TIMEOUT: Hệ thống bận bị lock quá 3 giây."
            elif '8649' in error_msg:
                friendly_msg = "🛑 LỖI QUÁ TẢI: Query quá nặng.chi phí Est thực thi quá 3000 Cost"
            elif 'Login failed' in error_msg:
                 friendly_msg = "🔐 LỖI ĐĂNG NHẬP: Kiểm tra Server/DB hoặc Quyền Windows."

            self.root.after(0, self.update_ui_state, all_results, friendly_msg)
        finally:
            if self.current_conn: 
                try: self.current_conn.close()
                except: pass
            self.current_conn = None

    def update_ui_state(self, all_results, error_msg=None):
        """Hàm duy nhất cập nhật UI cho cả thành công và lỗi (Partial Results)"""
        self.btn_run.config(state=tk.NORMAL, text="▶ CHẠY TRUY VẤN (F5)")
        self.btn_stop.config(state=tk.DISABLED)
        
        # Luôn cập nhật kết quả (nếu có)
        if all_results:
            self.last_results = all_results
            self.btn_copy.config(state=tk.NORMAL)
            self.btn_save.config(state=tk.NORMAL)
            
            total_rows = sum(len(r[1]) for r in all_results)
            total_time = all_results[-1][2] if all_results else 0
            
            if error_msg:
                self.lbl_status.config(text=f"Đã thực thi {len(all_results)} lệnh thành công; Gặp lỗi ở lệnh SQL tiếp theo.", fg="orange")
            else:
                self.lbl_status.config(text=f"Hoàn thành! {len(all_results)} bảng ({total_rows} dòng) - {total_time:.3f}s.", fg="green")
            
            # Vẽ bảng bằng Virtual Scroll
            def render_result_batch(idx):
                if idx >= len(all_results): return

                columns, rows, elapsed = all_results[idx]
                res_frame = tk.LabelFrame(self.scrollable_frame, 
                                         text=f" Kết quả {idx + 1} ({len(rows)} dòng) - {elapsed:.3f}s ", 
                                         pady=10, padx=10, font=("Arial", 10, "bold"), 
                                         fg="#0056b3", bg="white", relief="groove")
                res_frame.pack(fill=tk.X, expand=True, pady=(0, 20), padx=10)

                local_btn_frame = tk.Frame(res_frame, bg="white")
                local_btn_frame.pack(fill=tk.X, pady=(0, 10))

                tk.Button(local_btn_frame, text="📋 Copy bảng này", 
                          command=lambda c=columns, r=rows: self.copy_single(c, r),
                          font=("Arial", 8), bg="#e9ecef", relief="flat", padx=10).pack(side=tk.LEFT, padx=2)

                tk.Button(local_btn_frame, text="💾 Lưu CSV bảng này", 
                          command=lambda c=columns, r=rows, i=idx: self.save_single(c, r, i),
                          font=("Arial", 8), bg="#e9ecef", relief="flat", padx=10).pack(side=tk.LEFT, padx=2)

                # Sử dụng Virtual Treeview mới
                vtree = VirtualTreeview(res_frame, columns, rows, height=18)
                vtree.pack(fill=tk.BOTH, expand=True)

                # Render bảng tiếp theo sau một khoảng trễ nhỏ để UI mượt mà
                self.root.after(50, render_result_batch, idx + 1)

            render_result_batch(0)
        else:
            self.btn_copy.config(state=tk.DISABLED)
            self.btn_save.config(state=tk.DISABLED)

        # Hiển thị lỗi nếu có
        if error_msg:
            self.lbl_error.config(text=f"❌ {error_msg}")
            self.lbl_error.pack(fill=tk.X, pady=(5, 5))
            if not all_results:
                self.lbl_status.config(text="Gặp lỗi!", fg="red")
        else:
            self.lbl_error.config(text="")
            self.lbl_error.pack_forget()

    def copy_single(self, columns, rows):
        """Copy một bảng duy nhất"""
        try:
            output = io.StringIO()
            writer = csv.writer(output, delimiter='\t')
            writer.writerow(columns)
            writer.writerows(rows)
            
            self.root.clipboard_clear()
            self.root.clipboard_append(output.getvalue())
            self.root.update()
            messagebox.showinfo("Copy", "Đã copy bảng dữ liệu này!")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def save_single(self, columns, rows, idx):
        """Lưu một bảng duy nhất ra CSV"""
        f_path = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            initialfile=f"Result_{idx+1}.csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not f_path: return
        try:
            with open(f_path, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)
            messagebox.showinfo("Lưu file", f"Đã lưu thành công tại:\n{f_path}")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def copy_to_clipboard(self):
        """Copy TẤT CẢ các bảng vào Clipboard"""
        if not self.last_results: return
        try:
            output = io.StringIO()
            writer = csv.writer(output, delimiter='\t')
            for idx, (cols, rows, elapsed) in enumerate(self.last_results):
                writer.writerow([f"--- BẢNG KẾT QUẢ {idx + 1} ({elapsed:.3f}s) ---"])
                writer.writerow(cols)
                writer.writerows(rows)
                writer.writerow([]) # Dòng trống ngăn cách
            
            self.root.clipboard_clear()
            self.root.clipboard_append(output.getvalue())
            self.root.update()
            messagebox.showinfo("Copy", "Đã copy TẤT CẢ các bảng dữ liệu!\nHãy dán vào Excel.")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def save_to_csv(self):
        """Lưu TẤT CẢ các bảng vào một file CSV"""
        if not self.last_results: return
        f_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not f_path: return
        try:
            with open(f_path, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                for idx, (cols, rows, elapsed) in enumerate(self.last_results):
                    writer.writerow([f"KẾT QUẢ {idx + 1} ({elapsed:.3f}s)"])
                    writer.writerow(cols)
                    writer.writerows(rows)
                    writer.writerow([])
            messagebox.showinfo("Lưu file", f"Đã lưu thành công tại:\n{f_path}")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = SafeQueryApp(root)
    root.mainloop()