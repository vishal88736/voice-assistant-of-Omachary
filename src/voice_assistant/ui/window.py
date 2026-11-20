"""PySide6 floating assistant window (minimal)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class AssistantWindow(QWidget):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.setWindowTitle("Voice Assistant")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.resize(420, 520)
        layout = QVBoxLayout(self)
        self.status = QLabel("Idle")
        layout.addWidget(self.status)
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        layout.addWidget(self.chat)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message...")
        self.input.returnPressed.connect(self._send)
        layout.addWidget(self.input)
        self.ptt_btn = QPushButton("Push to talk")
        self.ptt_btn.clicked.connect(self._ptt)
        layout.addWidget(self.ptt_btn)

    def _send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._append("You", text)
        reply = self.assistant.process_text(text)
        self._append(self.assistant.settings.assistant_name, reply)

    def _ptt(self):
        reply = self.assistant.push_to_talk()
        if reply:
            self._append(self.assistant.settings.assistant_name, reply)

    def _append(self, speaker, text):
        self.chat.append(f"<b>{speaker}:</b> {text}")

    def update_state(self, state, text):
        self.status.setText(state.capitalize())