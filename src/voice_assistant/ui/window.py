"""Compact, polished PySide6 assistant window."""

from __future__ import annotations

import datetime
import html

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

STYLE = """
QWidget {
    background: #11111b;
    color: #cdd6f4;
    font-family: "Inter", "Noto Sans", sans-serif;
    font-size: 13px;
}
#Sidebar { background: #181825; border-right: 1px solid #313244; }
#Header { font-size: 15px; font-weight: 600; color: #f5e0dc; }
#Subtle { color: #a6adc8; font-size: 11px; }
#Status { color: #a6e3a1; font-size: 11px; }
QListWidget {
    background: transparent;
    border: none;
    outline: none;
    padding: 4px;
}
QListWidget::item {
    background: #1e1e2e;
    border-radius: 8px;
    padding: 8px;
    margin: 3px 0;
}
QListWidget::item:selected { background: #313244; }
QTextBrowser {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 10px;
}
QLineEdit {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 10px;
    padding: 9px 12px;
    selection-background-color: #89b4fa;
}
QLineEdit:focus { border: 1px solid #89b4fa; }
QPushButton {
    background: #313244;
    border: none;
    border-radius: 9px;
    padding: 8px 12px;
}
QPushButton:hover { background: #45475a; }
QPushButton#Primary { background: #89b4fa; color: #11111b; font-weight: 600; }
QPushButton#Primary:hover { background: #b4befe; }
QPushButton#Danger { background: #45475a; color: #f38ba8; }
"""


class Worker(QThread):
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn = fn
        self.args = args

    def run(self):
        try:
            self.done.emit(self.fn(*self.args) or "")
        except Exception as e:
            self.failed.emit(str(e))


class AssistantWindow(QWidget):
    state_signal = Signal(str, str)

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.worker: Worker | None = None
        self.state_signal.connect(self.update_state)
        self._build()
        self._refresh_sessions()
        self._load_current_session()

    def _build(self):
        self.setWindowTitle(f"{self.assistant.settings.assistant_name} — Voice Assistant")
        self.setMinimumSize(720, 500)
        self.resize(820, 560)
        self.setStyleSheet(STYLE)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 14, 12, 12)
        sl.setSpacing(8)
        title = QLabel("Conversations")
        title.setObjectName("Header")
        sl.addWidget(title)
        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self._session_clicked)
        sl.addWidget(self.session_list, 1)
        new_btn = QPushButton("+  New session")
        new_btn.clicked.connect(self._new_session)
        sl.addWidget(new_btn)
        del_btn = QPushButton("Delete selected")
        del_btn.setObjectName("Danger")
        del_btn.clicked.connect(self._delete_session)
        sl.addWidget(del_btn)
        forget_btn = QPushButton("Forget everything")
        forget_btn.setObjectName("Danger")
        forget_btn.clicked.connect(self._forget_all)
        sl.addWidget(forget_btn)
        self.model_label = QLabel("Model: placeholder\nWake: placeholder")
        self.model_label.setObjectName("Subtle")
        self.model_label.setWordWrap(True)
        sl.addWidget(self.model_label)
        root.addWidget(sidebar)

        # Main
        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(16, 14, 16, 14)
        ml.setSpacing(10)
        header = QHBoxLayout()
        name = QLabel(self.assistant.settings.assistant_name)
        name.setObjectName("Header")
        header.addWidget(name)
        header.addStretch()
        self.status = QLabel("Idle")
        self.status.setObjectName("Status")
        header.addWidget(self.status)
        ml.addLayout(header)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        ml.addWidget(self.chat, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message…  (English / हिंदी / Hinglish)")
        self.input.returnPressed.connect(self._send)
        row.addWidget(self.input, 1)
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("Primary")
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)
        self.ptt_btn = QPushButton("🎙")
        self.ptt_btn.setToolTip("Push to talk")
        self.ptt_btn.clicked.connect(self._ptt)
        row.addWidget(self.ptt_btn)
        ml.addLayout(row)
        root.addWidget(main, 1)

        self._update_model_labels()

    def _update_model_labels(self):
        s = self.assistant.settings
        self.model_label.setText(f"Model: {s.llm_model}\nWake model: {s.wake_model}\nTTS: {s.tts_voice}")

    def _refresh_sessions(self):
        self.session_list.clear()
        sessions = self.assistant.list_sessions()
        for s in sessions:
            ts = datetime.datetime.fromtimestamp(s["started_at"]).strftime("%d %b · %H:%M")
            preview = (s.get("preview") or "Empty session").replace("\n", " ")[:38]
            item = QListWidgetItem(f"{ts}\n{preview}")
            item.setData(Qt.UserRole, s["id"])
            self.session_list.addItem(item)
            if s["id"] == self.assistant.session_id:
                self.session_list.setCurrentItem(item)

    def _load_current_session(self):
        self.chat.clear()
        for m in self.assistant.memory.session_messages(self.assistant.session_id):
            self._append(m["role"], m["content"], m.get("created_at"))

    def _session_clicked(self, item):
        sid = item.data(Qt.UserRole)
        self.assistant.load_session(int(sid))
        self._load_current_session()

    def _new_session(self):
        self.assistant.new_session()
        self._refresh_sessions()
        self._load_current_session()

    def _delete_session(self):
        item = self.session_list.currentItem()
        if not item:
            return
        sid = int(item.data(Qt.UserRole))
        if QMessageBox.question(self, "Delete session", "Delete this conversation?") != QMessageBox.Yes:
            return
        self.assistant.delete_session(sid)
        self._refresh_sessions()
        self._load_current_session()

    def _forget_all(self):
        if QMessageBox.question(self, "Forget everything", "Delete all sessions and personal memory?") != QMessageBox.Yes:
            return
        self.assistant.forget_all()
        self._refresh_sessions()
        self._load_current_session()

    def _append(self, role, text, ts=None):
        when = datetime.datetime.fromtimestamp(ts).strftime("%H:%M") if ts else datetime.datetime.now().strftime("%H:%M")
        speaker = "You" if role == "user" else self.assistant.settings.assistant_name
        color = "#89b4fa" if role == "user" else "#a6e3a1"
        align = "right" if role == "user" else "left"
        bubble = "#313244" if role == "user" else "#1e1e2e"
        safe = html.escape(text).replace("\n", "<br>")
        self.chat.append(
            f'<div style="text-align:{align}; margin:6px 0;">'
            f'<span style="color:{color}; font-size:11px;">{speaker} · {when}</span><br>'
            f'<span style="display:inline-block; background:{bubble}; padding:8px 10px; '
            f'border-radius:10px; max-width:80%;">{safe}</span></div>'
        )

    def _send(self):
        text = self.input.text().strip()
        if not text or self.worker is not None:
            return
        self.input.clear()
        self._append("user", text)
        self._start_worker(self.assistant.process_text, text)

    def _ptt(self):
        if self.worker is not None:
            return
        self._start_worker(self.assistant.push_to_talk)

    def _start_worker(self, fn, *args):
        self.status.setText("Thinking…")
        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.worker = Worker(fn, *args)
        self.worker.done.connect(self._on_reply)
        self.worker.failed.connect(self._on_error)
        self.worker.start()

    def _on_reply(self, text):
        if text:
            self._append("assistant", text)
        self._finish_worker()

    def _on_error(self, err):
        self._append("assistant", f"Error: {err}")
        self._finish_worker()

    def _finish_worker(self):
        self.worker = None
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status.setText("Idle")
        self._refresh_sessions()

    def update_state(self, state, text):
        self.status.setText(state.capitalize())

    def closeEvent(self, event):
        try:
            self.assistant.stop()
        finally:
            super().closeEvent(event)