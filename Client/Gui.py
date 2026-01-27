import customtkinter as ctk
import ctypes
import logging
import base64
from datetime import datetime
from typing import Optional, Set, List
import threading
import webbrowser
import pyperclip
import os
from .history_manager import HistoryManager
from .network_handler import NetworkHandler
from .audio_handler import AudioHandler
from shared import config

#  Quan trọng: Đặt phần này ở đầu file để đảm bảo DPI awareness hoạt động
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    print(" Đã set DPI awareness")
except Exception as e:
    print(f" Không thể set DPI awareness: {e}")

logging.basicConfig(level=logging.INFO)

class AudioCallApp:
    def __init__(self, root: ctk.CTk, username="User"):
        self.root = root
        self.username = username

        # State management
        self.running = True
        self.active_after_ids: Set[int] = set()

        # Core components
        self.history_manager = HistoryManager()
        self.network_handler = NetworkHandler()
        self.audio_handler = AudioHandler(self.network_handler)
        self.network_handler.set_audio_handler(self.audio_handler)

        # Call state
        self.current_room_id: Optional[str] = None
        self.is_in_call = False
        self.is_muted = False
        self.call_start_time: Optional[datetime] = None
        self.selected_input_device = None
        self.selected_output_device = None
        self.room_users: List[str] = []

        # UI setup
        self._configure_dpi()
        self.root.title(f"VoiceChat - {self.username}")
        self.root.geometry("900x650")  # Giảm kích thước
        self.root.configure(fg_color="#2b2b2b")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._setup_ui()
        self._connect_to_server()
        self._update_device_options()
        self._update_call_controls()

    def _configure_dpi(self):
        try:
            dpi = ctypes.windll.user32.GetDpiForWindow(self.root.winfo_id())
            scaling = dpi / 96.0
            ctk.set_widget_scaling(scaling)
            ctk.set_window_scaling(scaling)
        except Exception:
            pass

    def _setup_ui(self):
        # Main frame đơn giản không scroll
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header đơn giản
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            header_frame, 
            text=f"🎧 VoiceChat - {self.username}",
            font=("Arial", 20, "bold"),
            text_color="#ffffff"
        ).pack(side="left")

        # Nút lịch sử cuộc gọi
        history_button = ctk.CTkButton(
            header_frame,
            text="📋 Lịch sử",
            command=self._show_history,
            width=80,
            height=30,
            fg_color="#9b59b6",
            hover_color="#8e44ad",
            font=("Arial", 10)
        )
        history_button.pack(side="right", padx=5)

        # Main content với tabs - ĐƠN GIẢN HÓA
        self.tabview = ctk.CTkTabview(
            main_frame, 
            fg_color="#2a2a2a",
            segmented_button_selected_color="#3498db",
            segmented_button_selected_hover_color="#2980b9"
        )
        self.tabview.pack(fill="both", expand=True)
        
        # Tab 1: Thiết bị
        self.tabview.add("🎧 Thiết bị")
        self._setup_device_tab()
        
        # Tab 2: Phòng
        self.tabview.add("🚪 Phòng")
        self._setup_room_tab()
        
        # Tab 3: Cuộc gọi
        self.tabview.add("📞 Gọi")
        self._setup_call_tab()

        # Status bar đơn giản
        self.status_label = ctk.CTkLabel(
            self.root, 
            text="🟢 Đã kết nối",
            text_color="white", 
            fg_color="#2c3e50",
            height=30,
            font=("Arial", 10)
        )
        self.status_label.pack(side="bottom", fill="x")

    def _setup_device_tab(self):
        tab = self.tabview.tab("🎧 Thiết bị")
        
        # Scrollable frame cho thiết bị
        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="#2a2a2a")
        scroll_frame.pack(fill="both", expand=True)

        device_frame = ctk.CTkFrame(scroll_frame, fg_color="#2a2a2a")
        device_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            device_frame, 
            text="Thiết bị âm thanh",
            font=("Arial", 16, "bold"),
            text_color="#ffffff"
        ).pack(pady=(0, 15))

        # Input device
        input_frame = ctk.CTkFrame(device_frame, fg_color="#3a3a3a", corner_radius=8)
        input_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkLabel(
            input_frame, 
            text="🎤 Microphone",
            font=("Arial", 14),
            text_color="#ffffff"
        ).pack(pady=8)
        
        self.input_device_var = ctk.StringVar(value="None")
        self.input_device_menu = ctk.CTkOptionMenu(
            input_frame, 
            variable=self.input_device_var,
            values=["None"], 
            command=self._select_input_device,
            width=280,
            height=32,
            fg_color="#4a4a4a",
            button_color="#3498db"
        )
        self.input_device_menu.pack(pady=8)

        # Output device
        output_frame = ctk.CTkFrame(device_frame, fg_color="#3a3a3a", corner_radius=8)
        output_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkLabel(
            output_frame, 
            text="🔈 Loa",
            font=("Arial", 14),
            text_color="#ffffff"
        ).pack(pady=8)
        
        self.output_device_var = ctk.StringVar(value="None")
        self.output_device_menu = ctk.CTkOptionMenu(
            output_frame, 
            variable=self.output_device_var,
            values=["None"], 
            command=self._select_output_device,
            width=280,
            height=32,
            fg_color="#4a4a4a",
            button_color="#3498db"
        )
        self.output_device_menu.pack(pady=8)

    def _setup_room_tab(self):
        tab = self.tabview.tab("🚪 Phòng")
        
        # Scrollable frame cho phòng
        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="#2a2a2a")
        scroll_frame.pack(fill="both", expand=True)

        room_frame = ctk.CTkFrame(scroll_frame, fg_color="#2a2a2a")
        room_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Tạo phòng
        create_frame = ctk.CTkFrame(room_frame, fg_color="#3a3a3a", corner_radius=8)
        create_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkLabel(
            create_frame, 
            text="Tạo phòng mới",
            font=("Arial", 14),
            text_color="#ffffff"
        ).pack(pady=8)

        self.create_room_button = ctk.CTkButton(
            create_frame, 
            text="🎯 Tạo phòng",
            command=self.create_room,
            height=40,
            font=("Arial", 12, "bold"),
            fg_color="#27ae60",
            hover_color="#219a52"
        )
        self.create_room_button.pack(pady=8)

        # Tham gia phòng
        join_frame = ctk.CTkFrame(room_frame, fg_color="#3a3a3a", corner_radius=8)
        join_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkLabel(
            join_frame, 
            text="Tham gia phòng",
            font=("Arial", 14),
            text_color="#ffffff"
        ).pack(pady=8)

        self.room_id_entry = ctk.CTkEntry(
            join_frame, 
            width=250,
            height=35,
            placeholder_text="Dán mã phòng...",
            font=("Arial", 11)
        )
        self.room_id_entry.pack(pady=5)

        self.join_room_button = ctk.CTkButton(
            join_frame, 
            text="🚀 Tham gia",
            command=self.join_room,
            height=35,
            font=("Arial", 11, "bold"),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        self.join_room_button.pack(pady=8)

        # Thông tin phòng hiện tại
        self.room_info_frame = ctk.CTkFrame(room_frame, fg_color="#3a3a3a", corner_radius=8)
        self.room_info_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkLabel(
            self.room_info_frame, 
            text="Phòng hiện tại",
            font=("Arial", 14),
            text_color="#ffffff"
        ).pack(pady=8)

        self.room_id_label = ctk.CTkLabel(
            self.room_info_frame, 
            text="Chưa tham gia",
            font=("Arial", 12),
            text_color="#f39c12"
        )
        self.room_id_label.pack(pady=5)

        # Nút hành động
        action_frame = ctk.CTkFrame(self.room_info_frame, fg_color="transparent")
        action_frame.pack(pady=8)

        self.copy_room_id_button = ctk.CTkButton(
            action_frame, 
            text="📋 Copy",
            command=self._copy_room_id,
            width=80,
            height=30,
            state="disabled",
            fg_color="#9b59b6",
            hover_color="#8e44ad",
            font=("Arial", 10)
        )
        self.copy_room_id_button.pack(side="left", padx=5)

        self.share_whatsapp_button = ctk.CTkButton(
            action_frame, 
            text="📱 WhatsApp",
            command=self._share_whatsapp,
            width=80,
            height=30,
            state="disabled",
            fg_color="#25D366",
            hover_color="#128C7E",
            font=("Arial", 10)
        )
        self.share_whatsapp_button.pack(side="left", padx=5)

        self.leave_room_button = ctk.CTkButton(
            action_frame, 
            text="👋 Rời",
            command=self.leave_room,
            width=80,
            height=30,
            state="disabled",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=("Arial", 10)
        )
        self.leave_room_button.pack(side="left", padx=5)

    def _setup_call_tab(self):
        tab = self.tabview.tab("📞 Gọi")
        
        # Scrollable frame cho cuộc gọi
        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="#2a2a2a")
        scroll_frame.pack(fill="both", expand=True)

        call_frame = ctk.CTkFrame(scroll_frame, fg_color="#2a2a2a")
        call_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Thành viên
        users_frame = ctk.CTkFrame(call_frame, fg_color="#3a3a3a", corner_radius=8)
        users_frame.pack(fill="both", expand=True, pady=8, padx=5)
        
        ctk.CTkLabel(
            users_frame, 
            text="👥 Thành viên",
            font=("Arial", 14),
            text_color="#ffffff"
        ).pack(pady=8)

        # Danh sách thành viên đơn giản
        self.user_listbox = ctk.CTkTextbox(
            users_frame, 
            height=120,
            state="normal",  # Sửa từ "disabled" để có thể cập nhật
            fg_color="#2a2a2a",
            text_color="#ffffff",
            font=("Arial", 11)
        )
        self.user_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Điều khiển cuộc gọi
        controls_frame = ctk.CTkFrame(call_frame, fg_color="#3a3a3a", corner_radius=8)
        controls_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkLabel(
            controls_frame, 
            text="Điều khiển",
            font=("Arial", 14),
            text_color="#ffffff"
        ).pack(pady=8)

        # Nút điều khiển
        button_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        button_frame.pack(pady=8)

        self.mute_button = ctk.CTkButton(
            button_frame, 
            text="🔇 Mute",
            command=self.toggle_mute,
            width=100,
            height=45,
            state="disabled",
            fg_color="#e67e22",
            hover_color="#d35400",
            font=("Arial", 12, "bold")
        )
        self.mute_button.pack(side="left", padx=10)

        self.call_button = ctk.CTkButton(
            button_frame, 
            text="📞 Gọi",
            command=self.toggle_call,
            width=100,
            height=45,
            state="disabled",
            fg_color="#27ae60",
            hover_color="#219a52",
            font=("Arial", 12, "bold")
        )
        self.call_button.pack(side="left", padx=10)

        # Trạng thái audio
        self.audio_status_label = ctk.CTkLabel(
            controls_frame, 
            text="🔴 Chưa kích hoạt",
            font=("Arial", 11),
            text_color="#e74c3c"
        )
        self.audio_status_label.pack(pady=(0, 10))

    def _update_user_list(self, users):
        """Cập nhật danh sách thành viên trong user_listbox"""
        self.room_users = users  # Lưu danh sách users
        self.user_listbox.delete("1.0", ctk.END)  # Xóa toàn bộ nội dung cũ
        
        if not users:
            self.user_listbox.insert(ctk.END, "Chưa có thành viên nào\n")
        else:
            for user in users:
                self.user_listbox.insert(ctk.END, f"👤 {user}\n")

    def _share_whatsapp(self):
        """Chia sẻ mã phòng qua WhatsApp"""
        if self.current_room_id:
            try:
                message = f"Tham gia phòng voice chat của tôi! Mã phòng: {self.current_room_id}"
                whatsapp_url = f"https://wa.me/?text={message}"
                webbrowser.open(whatsapp_url)
                self.update_status("✅ Đã mở WhatsApp để chia sẻ", "green")
            except Exception as e:
                self.update_status("❌ Lỗi khi chia sẻ qua WhatsApp", "red")
                logging.error(f"[GUI] WhatsApp share error: {e}")
        else:
            self.update_status("❌ Không có phòng để chia sẻ", "orange")

    def _show_history(self):
        """Hiển thị lịch sử cuộc gọi"""
        recent_calls = self.history_manager.get_recent_calls()
        
        history_window = ctk.CTkToplevel(self.root)
        history_window.title("Lịch sử cuộc gọi")
        history_window.geometry("600x500")
        history_window.transient(self.root)
        history_window.grab_set()
        
        ctk.CTkLabel(
            history_window, 
            text="📋 Lịch sử cuộc gọi gần đây",
            font=("Arial", 18, "bold")
        ).pack(pady=15)
        
        if not recent_calls:
            ctk.CTkLabel(
                history_window,
                text="Chưa có cuộc gọi nào trong lịch sử",
                text_color="#7f8c8d",
                font=("Arial", 14)
            ).pack(pady=50)
        else:
            scroll_frame = ctk.CTkScrollableFrame(history_window, height=350)
            scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            for call in reversed(recent_calls):
                call_frame = ctk.CTkFrame(scroll_frame, fg_color="#3a3a3a", corner_radius=8)
                call_frame.pack(fill="x", pady=5, padx=5)
                
                call_text = (
                    f"📅 {datetime.fromisoformat(call['timestamp']).strftime('%d/%m/%Y %H:%M')}\n"
                    f"🚪 Phòng: {call['room_id']}\n"
                    f"👥 Thành viên: {', '.join(call['participants'])}\n"
                    f"⏱️ Thời lượng: {call['duration_formatted']}"
                )
                
                ctk.CTkLabel(
                    call_frame,
                    text=call_text,
                    font=("Arial", 11),
                    justify="left"
                ).pack(padx=10, pady=8, anchor="w")
        
        ctk.CTkButton(
            history_window,
            text="Đóng",
            command=history_window.destroy,
            height=40,
            fg_color="#95a5a6",
            hover_color="#7f8c8d"
        ).pack(pady=15)

    def _copy_room_id(self):
        if self.current_room_id:
            pyperclip.copy(self.current_room_id)
            self.update_status("✅ Đã copy mã phòng", "green")
        else:
            self.update_status("❌ Không có phòng để copy", "orange")

    def _update_device_options(self):
        devices = self.audio_handler.get_audio_devices()
        input_options = ["None"] + [f"{d['index']}: {d['name']}" for d in devices if d['input_channels'] > 0]
        output_options = ["None"] + [f"{d['index']}: {d['name']}" for d in devices if d['output_channels'] > 0]
        self.input_device_menu.configure(values=input_options)
        self.output_device_menu.configure(values=output_options)
        if input_options:
            self.input_device_var.set(input_options[0])
        if output_options:
            self.output_device_var.set(output_options[0])

    def _select_input_device(self, value):
        if value == "None":
            self.selected_input_device = None
        else:
            self.selected_input_device = int(value.split(":")[0])

    def _select_output_device(self, value):
        if value == "None":
            self.selected_output_device = None
        else:
            self.selected_output_device = int(value.split(":")[0])

    def _connect_to_server(self):
        success, message = self.network_handler.connect(self.username)
        if success:
            self.network_handler.set_callback(self._handle_network_message)
            self.update_status("✅ Đã kết nối server", "green")
            self._start_keep_alive()
            self._update_call_controls()
            self._start_connection_monitor()
        else:
            self.update_status(f"❌ Lỗi kết nối: {message}", "red")

    def _start_keep_alive(self):
        def send_ping():
            if self.running and self.network_handler.is_connected():
                self.network_handler.send_message({'type': 'PING'})
                if self._is_window_valid():
                    after_id = self.root.after(30000, send_ping)
                    self.active_after_ids.add(after_id)
        if self._is_window_valid():
            after_id = self.root.after(10000, send_ping)
            self.active_after_ids.add(after_id)

    def _start_connection_monitor(self):
        """Theo dõi trạng thái kết nối"""
        def check_connection():
            if self.running:
                if self.network_handler.is_connected():
                    self.status_label.configure(fg_color="#2c3e50")
                else:
                    self.status_label.configure(fg_color="#e74c3c")
                    self.update_status("❌ Mất kết nối server", "red")
                    if self.is_in_call:
                        self._end_call()
                
                if self._is_window_valid():
                    after_id = self.root.after(5000, check_connection)
                    self.active_after_ids.add(after_id)
        
        if self._is_window_valid():
            after_id = self.root.after(5000, check_connection)
            self.active_after_ids.add(after_id)

    def _handle_network_message(self, message):
        msg_type = message.get('type')
        if msg_type == 'ROOM_CREATED':
            self.current_room_id = message.get('room_id')
            users = message.get('users', [])
            self._update_user_list(users)
            self.update_status(f"✅ Đã tạo phòng {self.current_room_id}", "green")
            self._update_room_display()
            self._update_call_controls()
        elif msg_type == 'JOIN_SUCCESS':
            self.current_room_id = message.get('room_id')
            users = message.get('users', [])
            self._update_user_list(users)
            self._update_room_display()
            self.update_status(f"✅ Đã tham gia phòng {self.current_room_id}", "green")
            self._update_call_controls()
        elif msg_type == 'USER_JOINED':
            users = message.get('users', [])
            self._update_user_list(users)
        elif msg_type == 'USER_LEFT':
            users = message.get('users', [])
            self._update_user_list(users)
        elif msg_type == 'AUDIO_DATA':
            try:
                self.audio_handler.handle_audio_data(message)
            except Exception as e:
                logging.error(f"[GUI] Audio handling error: {e}")

    def create_room(self):
        self.network_handler.send_message({
            'type': 'CREATE_ROOM'
        })
        self.update_status("🔄 Đang tạo phòng...", "blue")

    def join_room(self):
        room_id = self.room_id_entry.get().strip()
        if not room_id:
            self.update_status("❌ Vui lòng nhập mã phòng", "orange")
            return
        
        self.network_handler.send_message({
            'type': 'JOIN_ROOM',
            'room_id': room_id
        })
        self.update_status(f"🔄 Đang tham gia phòng {room_id}...", "blue")

    def leave_room(self):
        if self.current_room_id:
            self.network_handler.send_message({'type': 'LEAVE_ROOM'})
            self.current_room_id = None
            self._update_user_list([])
            self.update_status("✅ Đã rời phòng", "blue")
            if self.is_in_call:
                self.toggle_call()
        self._update_room_display()
        self._update_call_controls()

    def toggle_call(self):
        if not self.current_room_id:
            self.update_status("❌ Chưa tham gia phòng nào", "orange")
            return
        
        if not self.network_handler.is_connected():
            self.update_status("❌ Mất kết nối server", "red")
            return
            
        if not self.is_in_call:
            self._start_call()
        else:
            self._end_call()

    def _start_call(self):
        try:
            input_device_index = self.selected_input_device
            output_device_index = self.selected_output_device

            self.audio_handler.start_recording(
                send_callback=self._send_audio_data,
                input_device_index=input_device_index
            )
            self.audio_handler.start_playback(
                get_callback=self._get_audio_data,
                output_device_index=output_device_index
            )

            self.is_in_call = True
            self.call_start_time = datetime.now()
            self._update_call_controls()
            self.update_status("🎙️ Đang trong cuộc gọi", "green")
            self.audio_status_label.configure(text="🟢 Audio đang hoạt động", text_color="#2ecc71")
            
        except Exception as e:
            self.update_status(f"❌ Lỗi khởi động call: {e}", "red")
            logging.error(f"[GUI] Start call error: {e}")
            self._end_call()

    def _end_call(self):
        """Kết thúc cuộc gọi và lưu lịch sử một cách an toàn"""
        try:
            if self.call_start_time:
                duration = (datetime.now() - self.call_start_time).total_seconds()
                if hasattr(self, 'history_manager') and self.current_room_id:
                    self.history_manager.add_call(
                        room_id=self.current_room_id,
                        participants=self.room_users,
                        duration=duration
                    )
            
            # Dừng audio một cách an toàn
            if hasattr(self, 'audio_handler'):
                self.audio_handler.stop_recording()
                self.audio_handler.stop_playback()
                
            self.is_in_call = False
            self._update_call_controls()
            self.update_status("✅ Đã kết thúc cuộc gọi", "blue")
            self.audio_status_label.configure(text="🔴 Audio chưa kích hoạt", text_color="#e74c3c")
        
        except Exception as e:
            logging.error(f"[GUI] Error ending call: {e}")
            # Vẫn tiếp tục dọn dẹp state ngay cả khi có lỗi
            self.is_in_call = False
            self._update_call_controls()

    def toggle_mute(self):
        if not self.is_in_call:
            self.update_status("❌ Chưa trong cuộc gọi", "orange")
            return
        self.is_muted = self.audio_handler.toggle_mute()
        self._update_call_controls()

    def _send_audio_data(self, audio_data):
        try:
            if (self.current_room_id and 
                not self.is_muted and 
                self.network_handler.is_connected()):
                
                # KIỂM TRA KÍCH THƯỚC AUDIO DATA
                sample_size = self.audio_handler.audio.get_sample_size(config.AUDIO_FORMAT)
                expected_size = config.AUDIO_CHUNK * sample_size * config.AUDIO_CHANNELS
                
                if len(audio_data) != expected_size:
                    logging.warning(f"[AudioSend] ❌ Size mismatch: {len(audio_data)} vs {expected_size}")
                    # TỰ ĐỘNG ĐIỀU CHỈNH KÍCH THƯỚC
                    if len(audio_data) < expected_size:
                        audio_data = audio_data + b'\x00' * (expected_size - len(audio_data))
                    else:
                        audio_data = audio_data[:expected_size]
                    logging.info(f"[AudioSend] ✅ Adjusted size to: {len(audio_data)}")
                
                # ENCODE VÀ GỬI
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                
                success = self.network_handler.send_message({
                    'type': 'AUDIO_DATA',
                    'data': audio_b64
                })
                
                if success:
                    logging.debug(f"[AudioSend] ✅ Sent: {len(audio_data)} bytes")
                else:
                    logging.warning("[AudioSend] ❌ Failed to send")
                    
        except Exception as e:
            logging.error(f"[AudioSend] ❌ Error: {e}")

    def _get_audio_data(self):
        try:
            if not self.audio_handler.audio_queue.empty():
                return self.audio_handler.audio_queue.get_nowait()
            else:
                sample_size = self.audio_handler.audio.get_sample_size(config.AUDIO_FORMAT)
                return b'\x00' * (config.AUDIO_CHUNK * sample_size * config.AUDIO_CHANNELS)
        except Exception as e:
            logging.error(f"[GUI] Get audio data error: {e}")
            sample_size = self.audio_handler.audio.get_sample_size(config.AUDIO_FORMAT)
            return b'\x00' * (config.AUDIO_CHUNK * sample_size * config.AUDIO_CHANNELS)

    def _update_room_display(self):
        if self.current_room_id:
            self.room_id_label.configure(text=self.current_room_id)
            self.copy_room_id_button.configure(state="normal")
            self.share_whatsapp_button.configure(state="normal")
            self.leave_room_button.configure(state="normal")
        else:
            self.room_id_label.configure(text="Chưa tham gia")
            self.copy_room_id_button.configure(state="disabled")
            self.share_whatsapp_button.configure(state="disabled")
            self.leave_room_button.configure(state="disabled")

    def _update_call_controls(self):
        if self.is_in_call:
            self.call_button.configure(text="📞 Kết thúc gọi", fg_color="#e74c3c")
            self.mute_button.configure(state="normal")
            if self.is_muted:
                self.mute_button.configure(text="🔊 Unmute", fg_color="#f39c12")
            else:
                self.mute_button.configure(text="🔇 Mute", fg_color="#e67e22")
        else:
            self.call_button.configure(text="📞 Bắt đầu gọi", fg_color="#27ae60")
            self.mute_button.configure(state="disabled")
            
        if self.current_room_id and self.network_handler.is_connected():
            self.call_button.configure(state="normal")
        else:
            self.call_button.configure(state="disabled")
            self.audio_status_label.configure(text="🔴 Audio chưa kích hoạt", text_color="#e74c3c")

    def update_status(self, message: str, color: str = "blue"):
        color_map = {
            "green": "#2ecc71", "red": "#e74c3c",
            "blue": "#3498db", "orange": "#f39c12"
        }
        if self._is_window_valid():
            self.status_label.configure(
                text=message,
                fg_color=color_map.get(color, "#34495e")
            )

    def _is_window_valid(self):
        try:
            return (self.running and self.root.winfo_exists() and
                    hasattr(self.root, 'tk') and self.root.tk is not None)
        except:
            return False

    def on_closing(self):
        self.running = False
        self.leave_room()
        self.network_handler.disconnect()
        self.audio_handler.cleanup()
        for after_id in self.active_after_ids:
            try:
                self.root.after_cancel(after_id)
            except ctk.TclError:
                pass
        try:
            self.root.destroy()
        except:
            pass

if __name__ == "__main__":
    root = ctk.CTk()
    app = AudioCallApp(root)
    root.mainloop()