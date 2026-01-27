import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import os

class HistoryManager:
    def __init__(self, filename: str = "history.json"):
        self.filename = filename
        self.history: List[Dict[str, Any]] = []
        self._load_history()

    def _load_history(self):
        """Tải lịch sử từ file"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
                logging.info(f"[HistoryManager] Loaded {len(self.history)} history entries")
            else:
                self.history = []
                logging.info("[HistoryManager] No history file found, creating new one")
        except Exception as e:
            logging.error(f"[HistoryManager] Error loading history: {e}")
            self.history = []

    def _save_history(self):
        """Lưu lịch sử vào file"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            logging.info(f"[HistoryManager] Saved {len(self.history)} entries to history")
        except Exception as e:
            logging.error(f"[HistoryManager] Error saving history: {e}")

    def add_call(self, room_id: str, participants: List[str], duration: float):
        """Thêm cuộc gọi vào lịch sử"""
        call_entry = {
            'timestamp': datetime.now().isoformat(),
            'room_id': room_id,
            'participants': participants,
            'duration_seconds': duration,
            'duration_formatted': self._format_duration(duration)
        }
        
        self.history.append(call_entry)
        self._save_history()  #  QUAN TRỌNG: Phải gọi save sau khi thêm
        logging.info(f"[HistoryManager] Added call to history: {room_id}, {duration}s")

    def _format_duration(self, seconds: float) -> str:
        """Định dạng thời lượng cuộc gọi"""
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Lấy các cuộc gọi gần đây"""
        return self.history[-limit:]

    def clear_history(self):
        """Xóa toàn bộ lịch sử"""
        self.history = []
        self._save_history()
        logging.info("[HistoryManager] History cleared")

# Test thử History Manager
if __name__ == "__main__":
    # Test functionality
    hm = HistoryManager("test_history.json")
    hm.add_call("room_123", ["user1", "user2"], 125.5)
    hm.add_call("room_456", ["user1", "user3"], 45.0)
    print("Recent calls:", hm.get_recent_calls())