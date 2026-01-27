# Client/main_Client.py
import customtkinter as ctk
from .Login_gui import LoginGUI
from .Gui import AudioCallApp

def start_audio_app(username: str):
    """Khởi động ứng dụng audio call"""
    root = ctk.CTk()
    app = AudioCallApp(root, username=username)
    root.mainloop()

def main():
    """Hàm main"""
    def on_login_success(username: str):
        print(f" Đăng nhập thành công: {username}")
        start_audio_app(username)

    def on_login_failure(msg: str):
        print(f" Đăng nhập thất bại: {msg}")

    # Khởi động login GUI
    login_gui = LoginGUI(
        on_login_success_callback=on_login_success,
        on_login_failure_callback=on_login_failure,
    )
    login_gui.show()

if __name__ == "__main__":
    main()