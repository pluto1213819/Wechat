# friend_request_manager.py - 好友申请管理窗口
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QMessageBox, QHeaderView, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COLORS = {
    'primary': '#12B7F5',
    'primary_dark': '#0D8EDF',
    'success': '#52C41A',
    'warning': '#FAAD14',
    'danger': '#FF4D4F',
    'bg_main': '#FFFFFF',
    'bg_secondary': '#F5F5F5',
}

class ModernButton(QPushButton):
    def __init__(self, text='', color_type='primary', parent=None):
        super().__init__(text, parent)
        self.color_type = color_type
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()
    
    def _apply_style(self):
        colors = {
            'primary': (COLORS['primary'], COLORS['primary_dark']),
            'success': (COLORS['success'], '#389E0D'),
            'danger': (COLORS['danger'], '#CF1322'),
            'warning': (COLORS['warning'], '#D48806'),
            'default': (COLORS['bg_secondary'], '#E0E0E0')
        }
        bg_color, hover_color = colors.get(self.color_type, colors['default'])
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {'white' if self.color_type != 'default' else '#262626'};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {hover_color}; }}
            QPushButton:disabled {{ background-color: #E0E0E0; color: #BFBFBF; }}
        """)
        self.setMinimumHeight(32)

class SignalHelper(QObject):
    requests_loaded = pyqtSignal(list)

class FriendRequestManager(QDialog):
    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.signal_helper = SignalHelper()
        self.signal_helper.requests_loaded.connect(self._update_table)
        self.init_ui()
        self._pending_requests = []
        self.load_friend_requests()
    
    def init_ui(self):
        self.setWindowTitle("好友申请管理")
        self.setFixedSize(600, 450)
        self.setStyleSheet("QDialog { background-color: #f8f9fa; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel("好友申请管理")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 15px;")
        layout.addWidget(title_label)
        
        button_layout = QHBoxLayout()
        
        refresh_btn = ModernButton("刷新", 'primary')
        refresh_btn.clicked.connect(self.load_friend_requests)
        button_layout.addWidget(refresh_btn)
        
        accept_btn = ModernButton("接受选中", 'success')
        accept_btn.clicked.connect(self.accept_selected_requests)
        button_layout.addWidget(accept_btn)
        
        reject_btn = ModernButton("拒绝选中", 'danger')
        reject_btn.clicked.connect(self.reject_selected_requests)
        button_layout.addWidget(reject_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.request_table = QTableWidget()
        self.request_table.setColumnCount(3)
        self.request_table.setHorizontalHeaderLabels(["发送者", "发送时间", "操作"])
        self.request_table.setAlternatingRowColors(True)
        self.request_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.request_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.request_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.request_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.request_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.request_table.verticalHeader().setDefaultSectionSize(45)
        layout.addWidget(self.request_table, 1)
    
    def load_friend_requests(self):
        try:
            if self.client and hasattr(self.client, 'connected') and self.client.connected:
                if hasattr(self.client, 'get_friend_requests'):
                    self.client.get_friend_requests()
                if hasattr(self.client, 'register_callback'):
                    self.client.register_callback('friend_requests_list', self._handle_friend_requests_list)
            else:
                self._update_table([])
        except Exception as e:
            logger.error(f"加载好友申请列表失败: {e}")
    
    def _handle_friend_requests_list(self, message):
        try:
            requests = message.get('requests', [])
            self.signal_helper.requests_loaded.emit(requests)
        except Exception as e:
            logger.error(f"处理好友申请列表失败: {e}")
    
    def _update_table(self, requests):
        try:
            self._pending_requests = requests
            self.request_table.setRowCount(len(requests))
            
            for row, req in enumerate(requests):
                username = req.get('username', '')
                sender_item = QTableWidgetItem(username)
                sender_item.setTextAlignment(Qt.AlignCenter)
                self.request_table.setItem(row, 0, sender_item)
                
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
                time_item = QTableWidgetItem(created_at)
                time_item.setTextAlignment(Qt.AlignCenter)
                self.request_table.setItem(row, 1, time_item)
                
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(5, 5, 5, 5)
                action_layout.setSpacing(8)
                
                accept_btn = ModernButton("接受", 'success')
                accept_btn.setFixedSize(70, 28)
                accept_btn.clicked.connect(lambda checked, u=username: self.accept_request(u))
                action_layout.addWidget(accept_btn)
                
                reject_btn = ModernButton("拒绝", 'danger')
                reject_btn.setFixedSize(70, 28)
                reject_btn.clicked.connect(lambda checked, u=username: self.reject_request(u))
                action_layout.addWidget(reject_btn)
                
                action_layout.addStretch()
                self.request_table.setCellWidget(row, 2, action_widget)
        except Exception as e:
            logger.error(f"更新表格失败: {e}")
    
    def accept_request(self, username):
        try:
            if self.client and hasattr(self.client, 'connected') and self.client.connected:
                if hasattr(self.client, 'accept_friend_request'):
                    self.client.accept_friend_request(username)
                QMessageBox.information(self, "成功", f"已接受 {username} 的好友申请")
                self.load_friend_requests()
            else:
                QMessageBox.warning(self, "失败", "客户端未连接到服务器")
        except Exception as e:
            logger.error(f"接受好友申请失败: {e}")
    
    def reject_request(self, username):
        try:
            if self.client and hasattr(self.client, 'connected') and self.client.connected:
                if hasattr(self.client, 'reject_friend_request'):
                    self.client.reject_friend_request(username)
                QMessageBox.information(self, "成功", f"已拒绝 {username} 的好友申请")
                self.load_friend_requests()
            else:
                QMessageBox.warning(self, "失败", "客户端未连接到服务器")
        except Exception as e:
            logger.error(f"拒绝好友申请失败: {e}")
    
    def accept_selected_requests(self):
        selected_rows = self.request_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择一个或多个好友申请！")
            return
        
        for row in selected_rows:
            username = self.request_table.item(row.row(), 0).text()
            if self.client and hasattr(self.client, 'accept_friend_request'):
                self.client.accept_friend_request(username)
        
        QMessageBox.information(self, "操作完成", f"成功接受 {len(selected_rows)} 条好友申请")
        self.load_friend_requests()
    
    def reject_selected_requests(self):
        selected_rows = self.request_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择一个或多个好友申请！")
            return
        
        for row in selected_rows:
            username = self.request_table.item(row.row(), 0).text()
            if self.client and hasattr(self.client, 'reject_friend_request'):
                self.client.reject_friend_request(username)
        
        QMessageBox.information(self, "操作完成", f"成功拒绝 {len(selected_rows)} 条好友申请")
        self.load_friend_requests()
