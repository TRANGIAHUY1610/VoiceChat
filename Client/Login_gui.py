# Client/Login_gui.py
import customtkinter as ctk
import json
import os
import hashlib

USERS_FILE = "users.json"

class LoginGUI:
    def __init__(self, on_login_success_callback=None, on_login_failure_callback=None):
        self.on_login_success = on_login_success_callback
        self.on_login_failure = on_login_failure_callback
        self.root = None
        
    def _hash_password(self, password):
        """Hash mật khẩu đơn giản"""
        return hashlib.sha256(password.encode()).hexdigest()
        
    def load_users(self):
        """Tải dữ liệu người dùng từ file"""
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_users(self, users):
        """Lưu dữ liệu người dùng vào file"""
        try:
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    def register_user(self, username, password):
        """Đăng ký người dùng mới"""
        users = self.load_users()
        if username in users:
            return False, "Tên đăng nhập đã tồn tại"
        
        if len(username) < 3:
            return False, "Tên đăng nhập phải có ít nhất 3 ký tự"
            
        if len(password) < 4:
            return False, "Mật khẩu phải có ít nhất 4 ký tự"
            
        users[username] = self._hash_password(password)
        if self.save_users(users):
            return True, "Đăng ký thành công"
        else:
            return False, "Lỗi lưu dữ liệu"

    def authenticate_user(self, username, password):
        """Xác thực người dùng"""
        users = self.load_users()
        if username not in users:
            return False, "Tên đăng nhập không tồn tại"
            
        if users[username] != self._hash_password(password):
            return False, "Mật khẩu không đúng"
            
        return True, "Đăng nhập thành công"

    def show(self):
        """Hiển thị cửa sổ đăng nhập"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Đăng Nhập - Audio Call App")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        # Main frame
        main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="Audio Call App", 
                                  font=("Arial", 24, "bold"))
        title_label.pack(pady=30)
        
        subtitle_label = ctk.CTkLabel(main_frame, text="Đăng nhập để tiếp tục",
                                     font=("Arial", 14))
        subtitle_label.pack(pady=(0, 30))
        
        # Login form
        form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="x", padx=30)
        
        # Username
        ctk.CTkLabel(form_frame, text="Tên đăng nhập:", 
                    font=("Arial", 12)).pack(anchor="w", pady=(0, 5))
        self.username_entry = ctk.CTkEntry(form_frame, placeholder_text="Nhập username",
                                          height=40, font=("Arial", 12))
        self.username_entry.pack(fill="x", pady=(0, 15))
        
        # Password
        ctk.CTkLabel(form_frame, text="Mật khẩu:", 
                    font=("Arial", 12)).pack(anchor="w", pady=(0, 5))
        self.password_entry = ctk.CTkEntry(form_frame, placeholder_text="Nhập mật khẩu",
                                          height=40, show="*", font=("Arial", 12))
        self.password_entry.pack(fill="x", pady=(0, 10))
        
        # Show password checkbox
        self.show_password_var = ctk.BooleanVar(value=False)
        show_password_cb = ctk.CTkCheckBox(form_frame, text="Hiện mật khẩu",
                                          variable=self.show_password_var,
                                          command=self._toggle_password_visibility)
        show_password_cb.pack(anchor="w", pady=(0, 20))
        
        # Login button
        login_btn = ctk.CTkButton(form_frame, text="Đăng nhập", 
                                 command=self._on_login_clicked,
                                 height=45, font=("Arial", 14, "bold"))
        login_btn.pack(fill="x", pady=(0, 15))
        
        # Register link
        register_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        register_frame.pack(fill="x")
        
        ctk.CTkLabel(register_frame, text="Chưa có tài khoản? ",
                    font=("Arial", 12)).pack(side="left")
        
        register_link = ctk.CTkLabel(register_frame, text="Đăng ký ngay",
                                    font=("Arial", 12, "bold"), 
                                    text_color="#3498db", cursor="hand2")
        register_link.pack(side="left")
        register_link.bind("<Button-1>", lambda e: self._show_register_window())
        
        # Status message
        self.status_label = ctk.CTkLabel(form_frame, text="", 
                                        font=("Arial", 12), text_color="red")
        self.status_label.pack(pady=10)
        
        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Bind Enter key to login
        self.root.bind('<Return>', lambda e: self._on_login_clicked())
        
        self.root.mainloop()

    def _toggle_password_visibility(self):
        """Hiện/ẩn mật khẩu"""
        if self.show_password_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    def _on_login_clicked(self):
        """Xử lý sự kiện click đăng nhập"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            self.status_label.configure(text="Vui lòng nhập đầy đủ thông tin!")
            return
            
        success, message = self.authenticate_user(username, password)
        if success:
            self.status_label.configure(text=message, text_color="green")
            self.root.after(1000, lambda: self._login_success(username))
        else:
            self.status_label.configure(text=message, text_color="red")

    def _login_success(self, username):
        """Xử lý đăng nhập thành công"""
        self.root.destroy()
        if self.on_login_success:
            self.on_login_success(username)

    def _show_register_window(self):
        """Hiển thị cửa sổ đăng ký"""
        register_window = ctk.CTkToplevel(self.root)
        register_window.title("Đăng ký tài khoản")
        register_window.geometry("400x500")
        register_window.resizable(False, False)
        register_window.transient(self.root)
        register_window.grab_set()
        
        # Main frame
        main_frame = ctk.CTkFrame(register_window, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="Đăng ký tài khoản", 
                                  font=("Arial", 20, "bold"))
        title_label.pack(pady=20)
        
        # Form frame
        form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="x", padx=30)
        
        # Username
        ctk.CTkLabel(form_frame, text="Tên đăng nhập:", 
                    font=("Arial", 12)).pack(anchor="w", pady=(0, 5))
        username_entry = ctk.CTkEntry(form_frame, placeholder_text="Nhập username",
                                     height=40, font=("Arial", 12))
        username_entry.pack(fill="x", pady=(0, 15))
        
        # Password
        ctk.CTkLabel(form_frame, text="Mật khẩu:", 
                    font=("Arial", 12)).pack(anchor="w", pady=(0, 5))
        password_entry = ctk.CTkEntry(form_frame, placeholder_text="Nhập mật khẩu",
                                     height=40, show="*", font=("Arial", 12))
        password_entry.pack(fill="x", pady=(0, 10))
        
        # Confirm password
        ctk.CTkLabel(form_frame, text="Xác nhận mật khẩu:", 
                    font=("Arial", 12)).pack(anchor="w", pady=(0, 5))
        confirm_password_entry = ctk.CTkEntry(form_frame, placeholder_text="Nhập lại mật khẩu",
                                             height=40, show="*", font=("Arial", 12))
        confirm_password_entry.pack(fill="x", pady=(0, 15))
        
        # Show password checkbox
        show_password_var = ctk.BooleanVar(value=False)
        def toggle_passwords():
            if show_password_var.get():
                password_entry.configure(show="")
                confirm_password_entry.configure(show="")
            else:
                password_entry.configure(show="*")
                confirm_password_entry.configure(show="*")
                
        show_password_cb = ctk.CTkCheckBox(form_frame, text="Hiện mật khẩu",
                                          variable=show_password_var,
                                          command=toggle_passwords)
        show_password_cb.pack(anchor="w", pady=(0, 20))
        
        # Register button
        def on_register_click():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            confirm_password = confirm_password_entry.get().strip()
            
            if not username or not password or not confirm_password:
                status_label.configure(text="Vui lòng nhập đầy đủ thông tin!", text_color="red")
                return
                
            if password != confirm_password:
                status_label.configure(text="Mật khẩu không khớp!", text_color="red")
                return
                
            success, message = self.register_user(username, password)
            if success:
                status_label.configure(text=message, text_color="green")
                register_window.after(1500, register_window.destroy)
            else:
                status_label.configure(text=message, text_color="red")
        
        register_btn = ctk.CTkButton(form_frame, text="Đăng ký", 
                                    command=on_register_click,
                                    height=45, font=("Arial", 14, "bold"))
        register_btn.pack(fill="x", pady=(0, 15))
        
        # Status label
        status_label = ctk.CTkLabel(form_frame, text="", 
                                   font=("Arial", 12))
        status_label.pack()
        
        # Center window
        register_window.update_idletasks()
        width = register_window.winfo_width()
        height = register_window.winfo_height()
        x = (register_window.winfo_screenwidth() // 2) - (width // 2)
        y = (register_window.winfo_screenheight() // 2) - (height // 2)
        register_window.geometry(f"{width}x{height}+{x}+{y}")

    def close(self):
        """Đóng cửa sổ"""
        if self.root:
            self.root.destroy()