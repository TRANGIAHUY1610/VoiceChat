# Ứng Dụng Voice Chat (Python Socket)

> Đồ án môn Lập trình mạng - Trường Đại học Giao Thông Vận Tải TP. [cite_start]Hồ Chí Minh (UTH)[cite: 2, 4].

## 📖 Giới thiệu
[cite_start]Dự án này là một ứng dụng gọi thoại (Audio Call) trực tuyến hoạt động theo mô hình **Client-Server** kết hợp cơ chế **Relay**, được phát triển bằng ngôn ngữ **Python**[cite: 66].

[cite_start]Ứng dụng cho phép nhiều người dùng kết nối, tạo phòng và tham gia trò chuyện thoại thời gian thực với độ trễ thấp trong mạng LAN[cite: 68, 72]. [cite_start]Hệ thống không chỉ truyền tải âm thanh mà còn tích hợp các kỹ thuật xử lý tín hiệu cơ bản như triệt tiêu tiếng vọng (echo cancellation) và giảm nhiễu[cite: 15].

## 🚀 Tính năng chính
* [cite_start]**Mô hình Client-Server (Relay):** Server đóng vai trò vừa là Signaling (điều phối kết nối) vừa là Media Relay (chuyển tiếp dữ liệu âm thanh) giúp giảm độ phức tạp khi xuyên NAT[cite: 98, 103, 111].
* [cite_start]**Giao diện hiện đại (GUI):** Sử dụng thư viện **CustomTkinter** để thiết kế giao diện trực quan, hỗ trợ Dark mode, dễ sử dụng[cite: 95].
* [cite_start]**Quản lý phòng:** * Tạo phòng mới (cấp mã phòng ngẫu nhiên)[cite: 16].
    * [cite_start]Tham gia phòng thông qua mã phòng (Room ID)[cite: 16].
    * [cite_start]Hiển thị danh sách thành viên trong phòng[cite: 101].
* **Xử lý âm thanh (Real-time Audio):**
    * [cite_start]Thu/phát âm thanh thời gian thực sử dụng thư viện **PyAudio**[cite: 67].
    * [cite_start]Tích hợp Echo Cancellation (khử tiếng vọng) và Silence Detection (ngắt khi im lặng)[cite: 15, 78].
* **Tiện ích khác:**
    * [cite_start]Đăng ký/Đăng nhập tài khoản[cite: 166].
    * [cite_start]Lưu trữ lịch sử cuộc gọi[cite: 16].
    * [cite_start]Tùy chọn thiết bị đầu vào/đầu ra (Microphone/Speaker)[cite: 169].

## 🛠️ Công nghệ sử dụng
* **Ngôn ngữ:** Python 3.x
* [cite_start]**Giao thức mạng:** TCP Socket (để đảm bảo tin cậy cho Signaling)[cite: 87].
* [cite_start]**Thư viện âm thanh:** PyAudio (PortAudio bindings)[cite: 89].
* [cite_start]**Giao diện (GUI):** CustomTkinter[cite: 95].
* [cite_start]**Kiến trúc hệ thống:** * *Signaling Server:* Xử lý các lệnh `REGISTER`, `CREATE_ROOM`, `JOIN_ROOM`[cite: 99, 100].
    * [cite_start]*Media Relay Server:* Chuyển tiếp gói tin `AUDIO_DATA` đến các client khác trong phòng[cite: 103, 104].

## ⚙️ Cài đặt & Hướng dẫn sử dụng

### 1. Yêu cầu hệ thống (Prerequisites)
* Python 3.x đã được cài đặt.
* Cài đặt các thư viện cần thiết:
```bash
pip install pyaudio customtkinter

(Lưu ý: PyAudio có thể yêu cầu cài thêm PortAudio trên Linux hoặc Mac)2. Chạy ServerMáy chủ chịu trách nhiệm điều phối và chuyển tiếp âm thanh.Bashpython signaling_server.py
Server sẽ lắng nghe kết nối từ các Client và quản lý danh sách phòng.3. Chạy ClientMở ứng dụng giao diện người dùng trên các máy trạm.Bashpython main_client.py 
# (Hoặc tên file chạy chính của client)
4. Quy trình sử dụngĐăng nhập/Đăng ký: Nhập Username/Password để truy cập hệ thống.Cấu hình thiết bị: Chọn Microphone và Loa trong tab "Thiết bị".Tạo/Tham gia phòng:Nhấn Tạo phòng để lấy mã phòng (Room ID).Hoặc nhập mã phòng từ người khác và nhấn Tham gia.Bắt đầu gọi:Nhấn nút Bắt đầu gọi để kích hoạt Micro và Loa.Sử dụng nút Mute để tắt tiếng tạm thời.Kết thúc: Nhấn Rời phòng để ngắt kết nối và lưu lịch sử.📷 Một số hình ảnh demo(Thêm các hình ảnh chụp màn hình từ báo cáo vào thư mục images/ của repo và link vào đây)Đăng nhậpTạo phòngGiao diện đăng nhập Giao diện tạo/tham gia phòng Gọi thoạiThiết lậpGiao diện trong cuộc gọi Cài đặt thiết bị 🧩 Luồng hoạt động (Flowchart)Khởi động: Client kết nối Socket tới Server.Signaling: Client gửi yêu cầu (REGISTER, JOIN_ROOM). Server xác thực và cập nhật trạng thái .Streaming: * Client thu âm -> Chia nhỏ (Chunk) -> Encode Base64 -> Gửi Server.Server nhận AUDIO_DATA -> Broadcast cho các Client khác trong phòng.Client nhận -> Decode Base64 -> Phát ra loa.🚧 Hạn chế & Hướng phát triểnHạn chế hiện tại:Chưa có mã hóa đầu cuối (E2EE), dữ liệu chỉ được encode Base64.Chưa tối ưu bitrate theo băng thông mạng (chưa dùng codec nén mạnh như Opus).Chỉ hỗ trợ âm thanh (chưa có Video).Dự định tương lai (To-do):[ ] Tích hợp mã hóa E2EE bảo mật cuộc gọi.[ ] Sử dụng Codec Opus để nén âm thanh tốt hơn.[ ] Triển khai STUN/TURN để hỗ trợ kết nối qua Internet (vượt NAT).[ ] Thêm tính năng Video Call và Chat Text.👥 Tác giảNhóm sinh viên thực hiện:Trần Gia Huy - 079205013040 Lê Quốc Trung - 075205015953 Giảng viên hướng dẫn: ThS. Lê Văn Quốc Anh Báo cáo hoàn thành tháng 1 năm 2026 tại TP. Hồ Chí Minh.
### Hướng dẫn bổ sung để Repo chuyên nghiệp hơn:
1.  **Ảnh Demo:** Bạn hãy cắt các hình ảnh (Hình 5, 6, 7, 8) từ file Word, lưu vào thư mục tên là `images` trong project folder, sau đó sửa lại đường dẫn `link_to_image_x` trong file Markdown ở trên thành đường dẫn thật (ví dụ: `images/login.png`).
2.  **Requirements.txt:** Tạo thêm một file `requirements.txt` với nội dung:
    ```text
    customtkinter
    pyaudio
    numpy
    # thêm các thư viện khác nếu có trong code thực tế
    ```
3.  **Cấu trúc thư mục:** Nên sắp xếp code theo cấu trúc:
    ```
    ├── client/
    │   ├── gui.py
    │   ├── audio_handler.py
    │   ├── network_handler.py
    │   └── main_client.py
    ├── server/
    │   └── signaling_server.py
    ├── images/
    ├── requirements.txt
    └── README.md
    ```
