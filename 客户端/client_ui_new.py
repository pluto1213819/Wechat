# client_ui.py - 仿QQ即时通讯系统客户端UI（完整版）
# 包含所有功能：注册、登录、好友、群聊、私聊、文件传输等

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QLineEdit,
    QListWidget, QComboBox, QSplitter, QGroupBox,
    QStatusBar, QMessageBox, QAction, QToolBar,
    QMenu, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QGridLayout, QFrame, QTabWidget,
    QListWidgetItem, QStackedWidget, QScrollArea,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFormLayout
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, pyqtSlot
from PyQt5.QtGui import QFont, QTextCursor, QColor, QIcon, QPixmap, QPainter, QBrush, QPainterPath
import sys
import json
import os
from datetime import datetime
import logging
import socket
import threading
import struct
import time
import queue
import base64
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from friend_request_manager import FriendRequestManager
    FRIEND_REQUEST_UI_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入好友申请管理模块: {e}")
    FRIEND_REQUEST_UI_AVAILABLE = False
    FriendRequestManager = None

# QQ风格配色方案
COLORS = {
    'primary': '#12B7F5',      # QQ蓝
    'primary_dark': '#0D8EDF',
    'success': '#52C41A',      # 成功绿
    'warning': '#FAAD14',      # 警告黄
    'danger': '#FF4D4F',       # 错误红
    'bg_main': '#FFFFFF',      # 主背景白
    'bg_secondary': '#F5F5F5', # 次级背景灰
    'bg_hover': '#E6F7FF',     # 悬停背景
    'text_primary': '#262626', # 主文本黑
    'text_secondary': '#8C8C8C', # 次要文本灰
    'border': '#D9D9D9',      # 边框灰
    'online': '#52C41A',       # 在线绿
    'offline': '#8C8C8C',      # 离线灰
    'header_blue': '#2C3E50',  # 顶部深蓝色
}

class CaptchaGenerator:
    """验证码生成器 - 生成数学问题验证码"""
    
    @staticmethod
    def generate():
        """生成一个数学问题验证码"""
        # 随机选择运算类型
        op_type = random.choice(['add', 'sub', 'mul'])
        
        if op_type == 'add':
            # 加法
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            question = f"{a} + {b} = ?"
            answer = a + b
        elif op_type == 'sub':
            # 减法（确保结果为正）
            a = random.randint(10, 30)
            b = random.randint(1, a)
            question = f"{a} - {b} = ?"
            answer = a - b
        else:
            # 乘法（简单的个位数乘法）
            a = random.randint(2, 9)
            b = random.randint(2, 9)
            question = f"{a} × {b} = ?"
            answer = a * b
        
        return question, str(answer)
    
    @staticmethod
    def verify(user_answer, correct_answer):
        """验证用户答案"""
        try:
            return str(user_answer.strip()) == str(correct_answer)
        except:
            return False

class ModernButton(QPushButton):
    """现代化按钮"""
    def __init__(self, text='', color_type='primary', parent=None):
        super().__init__(text, parent)
        self.color_type = color_type
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()
    
    def _apply_style(self):
        colors = {
            'primary': ('#1890FF', '#40A9FF'),      # 蓝色
            'success': ('#52C41A', '#73D13D'),      # 绿色
            'danger': ('#FF4D4F', '#FF7875'),       # 红色
            'warning': ('#FA8C16', '#FFA940'),      # 橙色
            'default': (COLORS['bg_secondary'], '#E0E0E0')
        }
        
        bg_color, hover_color = colors.get(self.color_type, colors['default'])
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
                font-family: 'Microsoft YaHei UI', 'Segoe UI';
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {bg_color};
            }}
            QPushButton:disabled {{
                background-color: #E0E0E0;
                color: #BFBFBF;
            }}
        """)
        self.setMinimumHeight(40)


class LoginDialog(QDialog):
    """登录对话框 - 按照图1样式设计"""
    login_success = pyqtSignal(str, str, str, object)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Nova chatting')
        self.setFixedSize(440, 620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.client = None
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部标题栏
        header_widget = QWidget()
        header_widget.setFixedHeight(140)
        header_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1a237e, stop:1 #0d47a1);
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(8)
        
        # Logo图标
        logo_label = QLabel('💬')
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(logo_label)
        
        title_label = QLabel('Nova chatting')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: white; font-size: 26px; font-weight: bold; font-family: 'Microsoft YaHei UI';")
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel('Secure Instant Messaging')
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; font-family: 'Segoe UI';")
        header_layout.addWidget(subtitle_label)
        
        main_layout.addWidget(header_widget)
        
        # 表单区域
        form_widget = QWidget()
        form_widget.setStyleSheet("background-color: #FAFAFA;")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(35, 25, 35, 15)
        form_layout.setSpacing(12)
        
        # 服务器设置区域（可折叠样式）
        server_group = QWidget()
        server_group.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        server_group_layout = QVBoxLayout(server_group)
        server_group_layout.setContentsMargins(15, 12, 15, 12)
        server_group_layout.setSpacing(10)
        
        server_title = QLabel('服务器设置')
        server_title.setStyleSheet("font-size: 13px; color: #666; font-weight: bold; border: none; background: transparent;")
        server_group_layout.addWidget(server_title)
        
        server_row = QHBoxLayout()
        server_row.setSpacing(10)
        
        server_label = QLabel('地址:')
        server_label.setStyleSheet("font-size: 13px; color: #333; border: none; background: transparent;")
        server_label.setFixedWidth(40)
        self.server_input = QLineEdit('127.0.0.1')
        self.server_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #1a237e;
                background-color: white;
            }
        """)
        server_row.addWidget(server_label)
        server_row.addWidget(self.server_input)
        
        port_label = QLabel('端口:')
        port_label.setStyleSheet("font-size: 13px; color: #333; border: none; background: transparent;")
        port_label.setFixedWidth(40)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(8000)
        self.port_input.setFixedWidth(100)
        self.port_input.setStyleSheet("""
            QSpinBox {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
            }
            QSpinBox:focus {
                border: 2px solid #1a237e;
                background-color: white;
            }
        """)
        server_row.addWidget(port_label)
        server_row.addWidget(self.port_input)
        
        server_group_layout.addLayout(server_row)
        form_layout.addWidget(server_group)
        
        # 用户名输入
        username_widget = QWidget()
        username_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        username_layout = QHBoxLayout(username_widget)
        username_layout.setContentsMargins(15, 12, 15, 12)
        
        user_icon = QLabel('👤')
        user_icon.setStyleSheet("font-size: 18px; border: none; background: transparent;")
        username_layout.addWidget(user_icon)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('请输入用户名或ID')
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                padding: 5px;
                font-size: 14px;
            }
        """)
        username_layout.addWidget(self.username_input)
        
        form_layout.addWidget(username_widget)
        
        # 密码输入
        password_widget = QWidget()
        password_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        password_layout = QHBoxLayout(password_widget)
        password_layout.setContentsMargins(15, 12, 15, 12)
        
        pwd_icon = QLabel('🔒')
        pwd_icon.setStyleSheet("font-size: 18px; border: none; background: transparent;")
        password_layout.addWidget(pwd_icon)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('请输入密码')
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                padding: 5px;
                font-size: 14px;
            }
        """)
        password_layout.addWidget(self.password_input)
        
        form_layout.addWidget(password_widget)
        
        # 复选框区域
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(20)
        
        self.remember_checkbox = QCheckBox('记住密码')
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                color: #666;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #D9D9D9;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #1a237e;
                border-color: #1a237e;
            }
        """)
        
        self.auto_login_checkbox = QCheckBox('自动登录')
        self.auto_login_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                color: #666;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #D9D9D9;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #1a237e;
                border-color: #1a237e;
            }
        """)
        
        checkbox_layout.addWidget(self.remember_checkbox)
        checkbox_layout.addWidget(self.auto_login_checkbox)
        checkbox_layout.addStretch()
        form_layout.addLayout(checkbox_layout)
        
        # 登录按钮
        self.login_btn = QPushButton('登 录')
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a237e, stop:1 #0d47a1);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #283593, stop:1 #1565C0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a237e, stop:1 #0d47a1);
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.login_btn.clicked.connect(self.do_login)
        form_layout.addWidget(self.login_btn)
        
        # 底部按钮区域
        bottom_btn_layout = QHBoxLayout()
        bottom_btn_layout.setSpacing(15)
        
        self.register_btn = QPushButton('注册账号')
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #52C41A;
                border: 1px solid #52C41A;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F6FFED;
            }
        """)
        self.register_btn.clicked.connect(self.show_register_dialog)
        bottom_btn_layout.addWidget(self.register_btn)
        
        self.forgot_btn = QPushButton('找回密码')
        self.forgot_btn.setCursor(Qt.PointingHandCursor)
        self.forgot_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FA8C16;
                border: 1px solid #FA8C16;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #FFF7E6;
            }
        """)
        self.forgot_btn.clicked.connect(self.show_forgot_password_dialog)
        bottom_btn_layout.addWidget(self.forgot_btn)
        
        form_layout.addLayout(bottom_btn_layout)
        form_layout.addStretch()
        
        main_layout.addWidget(form_widget)
        
        # 状态标签
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #999; font-size: 11px; padding: 8px; background-color: #FAFAFA;")
        main_layout.addWidget(self.status_label)
    
    def do_login(self):
        """执行登录"""
        server_addr = self.server_input.text().strip()
        port = self.port_input.value()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not all([server_addr, username, password]):
            self.status_label.setText('[WARNING] 请填写完整信息')
            return
        
        self.status_label.setText('正在连接...')
        self.login_btn.setEnabled(False)
        self.login_btn.setText('连接中...')
        
        try:
            from client_network import NetworkClient
            self.client = NetworkClient(server_addr, port)
            
            if not self.client.connect():
                self.status_label.setText('[ERROR] 无法连接到服务器')
                self.login_btn.setEnabled(True)
                self.login_btn.setText('登 录')
                QMessageBox.warning(self, '连接失败', '无法连接到服务器，请检查服务器地址和端口')
                return
            
            # 执行登录
            if self.client.login(username, password):
                # 登录成功
                self.status_label.setText('登录成功！')
                self.login_success.emit(username, f'{server_addr}:{port}', '', self.client)
            else:
                # 登录失败，显示错误信息
                error_msg = getattr(self.client, 'last_error', '登录失败')
                self.status_label.setText(f'[ERROR] {error_msg}')
                self.login_btn.setEnabled(True)
                self.login_btn.setText('登 录')
                QMessageBox.warning(self, '登录失败', error_msg)
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            self.status_label.setText(f'[ERROR] 登录异常: {str(e)}')
            self.login_btn.setEnabled(True)
            self.login_btn.setText('登 录')
            QMessageBox.critical(self, '登录异常', f'登录过程中发生错误: {str(e)}')
    
    def show_register_dialog(self):
        """显示注册对话框"""
        server_addr = self.server_input.text().strip()
        port = self.port_input.value()
        
        if not server_addr:
            QMessageBox.warning(self, '警告', '请先填写服务器地址！')
            return
        
        dialog = RegisterDialog(server_addr, port, self)
        dialog.exec_()
    
    def show_forgot_password_dialog(self):
        """显示找回密码对话框"""
        dialog = ForgotPasswordDialog(self)
        dialog.exec_()


class RegisterDialog(QDialog):
    """注册对话框"""
    def __init__(self, server_addr, port, parent=None):
        super().__init__(parent)
        self.server_addr = server_addr
        self.port = port
        self.client = None
        self.avatar_path = ''  # 保存头像路径
        self.captcha_question = ''
        self.captcha_answer = ''
        self.setWindowTitle('用户注册')
        self.setFixedSize(450, 680)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QLabel {
                font-size: 14px;
                color: #333;
                font-weight: bold;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #1890FF;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel('用户注册')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1890FF; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # 服务器信息
        server_info = QLabel(f'服务器: {self.server_addr}:{self.port}')
        server_info.setAlignment(Qt.AlignCenter)
        server_info.setStyleSheet("font-size: 12px; color: #666; font-weight: normal; margin-bottom: 10px;")
        layout.addWidget(server_info)
        
        # 头像选择区域
        avatar_group = QGroupBox("头像设置")
        avatar_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        avatar_main_layout = QVBoxLayout(avatar_group)
        
        # 当前头像显示
        current_avatar_layout = QHBoxLayout()
        current_avatar_label = QLabel('当前头像:')
        current_avatar_label.setStyleSheet("font-weight: normal; color: #666;")
        current_avatar_layout.addWidget(current_avatar_label)
        
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(60, 60)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet("border: 2px solid #D9D9D9; border-radius: 30px;")
        self._update_avatar_display()
        current_avatar_layout.addWidget(self.avatar_label)
        current_avatar_layout.addStretch()
        avatar_main_layout.addLayout(current_avatar_layout)
        
        # 默认头像选择
        default_avatar_layout = QHBoxLayout()
        default_avatar_label = QLabel('默认头像:')
        default_avatar_label.setStyleSheet("font-weight: normal; color: #666;")
        default_avatar_layout.addWidget(default_avatar_label)
        
        male_avatar_btn = QPushButton()
        male_avatar_btn.setFixedSize(45, 45)
        male_avatar_btn.setToolTip('男性头像')
        male_avatar_btn.clicked.connect(lambda: self._select_default_avatar('m.webp'))
        self._set_default_avatar_button(male_avatar_btn, 'm.webp')
        default_avatar_layout.addWidget(male_avatar_btn)
        
        female_avatar_btn = QPushButton()
        female_avatar_btn.setFixedSize(45, 45)
        female_avatar_btn.setToolTip('女性头像')
        female_avatar_btn.clicked.connect(lambda: self._select_default_avatar('w.webp'))
        self._set_default_avatar_button(female_avatar_btn, 'w.webp')
        default_avatar_layout.addWidget(female_avatar_btn)
        
        # 上传按钮
        upload_btn = ModernButton('上传自定义头像', 'primary')
        upload_btn.clicked.connect(self._upload_custom_avatar)
        default_avatar_layout.addWidget(upload_btn)
        
        default_avatar_layout.addStretch()
        avatar_main_layout.addLayout(default_avatar_layout)
        
        layout.addWidget(avatar_group)
        
        # 表单
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('请输入用户名（英文和数字）')
        form_layout.addRow('用户名 *:', self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('请输入密码（至少6位）')
        form_layout.addRow('密码 *:', self.password_input)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText('请确认密码')
        form_layout.addRow('确认密码 *:', self.confirm_input)
        
        # 验证码
        captcha_layout = QHBoxLayout()
        self.captcha_input = QLineEdit()
        self.captcha_input.setPlaceholderText('请输入验证码')
        captcha_layout.addWidget(self.captcha_input)
        
        # 验证码显示和刷新按钮
        self.captcha_label = QLabel()
        self.captcha_label.setStyleSheet("""
            QLabel {
                background-color: #F0F0F0;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                color: #1890FF;
            }
        """)
        captcha_layout.addWidget(self.captcha_label)
        
        refresh_btn = QPushButton('🔄')
        refresh_btn.setFixedSize(35, 35)
        refresh_btn.setToolTip('刷新验证码')
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_captcha)
        captcha_layout.addWidget(refresh_btn)
        
        form_layout.addRow('验证码 *:', captcha_layout)
        
        # 初始化验证码
        self._refresh_captcha()
        
        layout.addLayout(form_layout)
        
        # 状态标签
        self.status_label = QLabel('')
        self.status_label.setStyleSheet("color: #666; font-size: 12px; font-weight: normal;")
        layout.addWidget(self.status_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.register_btn = ModernButton('注 册', 'success')
        self.register_btn.clicked.connect(self.do_register)
        cancel_btn = ModernButton('取 消', 'default')
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.register_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        layout.addStretch()
    
    def _update_avatar_display(self):
        """更新头像显示"""
        try:
            if self.avatar_path and os.path.exists(self.avatar_path):
                pixmap = QPixmap(self.avatar_path)
                if not pixmap.isNull():
                    # 创建圆形头像
                    size = 60
                    rounded_pixmap = QPixmap(size, size)
                    rounded_pixmap.fill(Qt.transparent)
                    
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    
                    # 创建圆形路径
                    path = QPainterPath()
                    path.addEllipse(0, 0, size, size)
                    painter.setClipPath(path)
                    
                    # 缩放并绘制头像
                    scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    
                    self.avatar_label.setPixmap(rounded_pixmap)
                    return
        except Exception as e:
            logger.error(f"更新头像显示失败: {e}")
        
        # 默认显示👤图标
        self.avatar_label.setText("👤")
        self.avatar_label.setStyleSheet("font-size: 36px; border: 2px solid #D9D9D9; border-radius: 30px;")
    
    def _set_default_avatar_button(self, button, avatar_file):
        """设置默认头像按钮"""
        try:
            if os.path.exists(avatar_file):
                pixmap = QPixmap(avatar_file)
                if not pixmap.isNull():
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(40, 40))
                    button.setStyleSheet("border: 1px solid #D9D9D9; border-radius: 22px;")
                    return
        except Exception as e:
            logger.error(f"设置默认头像按钮失败: {e}")
        
        button.setText('👤' if avatar_file == 'm.webp' else '👩')
        button.setStyleSheet("font-size: 18px; border: 1px solid #D9D9D9; border-radius: 22px;")
    
    def _select_default_avatar(self, avatar_file):
        """选择默认头像"""
        if os.path.exists(avatar_file):
            self.avatar_path = avatar_file
            self._update_avatar_display()
        else:
            QMessageBox.information(self, '提示', f'默认头像文件 {avatar_file} 不存在')
    
    def _upload_custom_avatar(self):
        """上传自定义头像"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '选择头像', 
            '', 
            '图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)'
        )
        
        if file_path:
            self.avatar_path = file_path
            self._update_avatar_display()
    
    def _refresh_captcha(self):
        """刷新验证码"""
        self.captcha_question, self.captcha_answer = CaptchaGenerator.generate()
        self.captcha_label.setText(self.captcha_question)
        self.captcha_input.clear()
    
    def do_register(self):
        """执行注册"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        captcha = self.captcha_input.text().strip()
        
        if not all([username, password, confirm, captcha]):
            QMessageBox.warning(self, '警告', '请填写所有必填项！')
            return
        
        if not username.isalnum():
            QMessageBox.warning(self, '警告', '用户名只能包含英文和数字！')
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, '警告', '密码长度至少6位！')
            return
        
        if password != confirm:
            QMessageBox.warning(self, '警告', '两次输入的密码不一致！')
            return
        
        # 验证码验证
        if not CaptchaGenerator.verify(captcha, self.captcha_answer):
            QMessageBox.warning(self, '警告', '验证码错误，请重新输入！')
            self._refresh_captcha()
            return
        
        self.status_label.setText('正在连接服务器...')
        self.register_btn.setEnabled(False)
        
        try:
            from client_network import NetworkClient
            self.client = NetworkClient(self.server_addr, self.port)
            
            if not self.client.connect():
                self.status_label.setText('')
                self.register_btn.setEnabled(True)
                QMessageBox.warning(self, '连接失败', f'无法连接到服务器 {self.server_addr}:{self.port}')
                return
            
            self.status_label.setText('正在注册...')
            result = self.client.register(username, password, avatar=self.avatar_path)
            
            if result.get('success'):
                self.status_label.setText('')
                QMessageBox.information(self, '注册成功', f'用户 {username} 注册成功！\n请使用用户名和密码登录。')
                self.client.close()
                self.accept()
            else:
                error_msg = result.get('message', '注册失败')
                self.status_label.setText('')
                self.register_btn.setEnabled(True)
                QMessageBox.warning(self, '注册失败', error_msg)
                self.client.close()
                
        except Exception as e:
            self.status_label.setText('')
            self.register_btn.setEnabled(True)
            QMessageBox.critical(self, '错误', f'注册过程中发生错误: {str(e)}')


class ForgotPasswordDialog(QDialog):
    """找回密码对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.captcha_question = ''
        self.captcha_answer = ''
        self.setWindowTitle('找回密码')
        self.setFixedSize(450, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QLabel {
                font-size: 14px;
                color: #333;
                font-weight: bold;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #1890FF;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel('找回密码')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #FA8C16; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 说明
        info = QLabel('请输入您的用户名，我们将帮您找回密码')
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("font-size: 13px; color: #666; font-weight: normal;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # 用户名输入
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('请输入用户名')
        layout.addWidget(QLabel('用户名:'))
        layout.addWidget(self.username_input)
        
        # 验证码
        layout.addWidget(QLabel('验证码:'))
        captcha_layout = QHBoxLayout()
        self.captcha_input = QLineEdit()
        self.captcha_input.setPlaceholderText('请输入验证码')
        captcha_layout.addWidget(self.captcha_input)
        
        # 验证码显示和刷新按钮
        self.captcha_label = QLabel()
        self.captcha_label.setStyleSheet("""
            QLabel {
                background-color: #F0F0F0;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                color: #1890FF;
            }
        """)
        captcha_layout.addWidget(self.captcha_label)
        
        refresh_btn = QPushButton('🔄')
        refresh_btn.setFixedSize(35, 35)
        refresh_btn.setToolTip('刷新验证码')
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_captcha)
        captcha_layout.addWidget(refresh_btn)
        
        layout.addLayout(captcha_layout)
        
        # 初始化验证码
        self._refresh_captcha()
        
        # 按钮
        btn_layout = QHBoxLayout()
        submit_btn = ModernButton('提 交', 'warning')
        submit_btn.clicked.connect(self.do_submit)
        cancel_btn = ModernButton('取 消', 'default')
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(submit_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        layout.addStretch()
    
    def _refresh_captcha(self):
        """刷新验证码"""
        self.captcha_question, self.captcha_answer = CaptchaGenerator.generate()
        self.captcha_label.setText(self.captcha_question)
        self.captcha_input.clear()
    
    def do_submit(self):
        """提交找回密码请求"""
        username = self.username_input.text().strip()
        captcha = self.captcha_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, '警告', '请输入用户名！')
            return
        
        if not captcha:
            QMessageBox.warning(self, '警告', '请输入验证码！')
            return
        
        # 验证码验证
        if not CaptchaGenerator.verify(captcha, self.captcha_answer):
            QMessageBox.warning(self, '警告', '验证码错误，请重新输入！')
            self._refresh_captcha()
            return
        
        QMessageBox.information(self, '提示', '找回密码功能需要连接到服务端实现')
        self.accept()


# 保持原有的 ChatMainWindow 和其他类的代码...
# 为了节省空间，这里只显示修改的部分

class ChatMainWindow(QMainWindow):
    """聊天主窗口"""
    def __init__(self, username, server_addr, client):
        super().__init__()
        self.username = username
        self.server_addr = server_addr
        self.client = client
        self.current_chat_friend = None
        self.user_avatar = getattr(client, 'avatar', None)  # 保存用户头像
        self.pending_files = {}  # 保存待下载的文件 {file_id: {'from': username, 'name': filename, 'data': data}}
        self.file_counter = 0  # 文件计数器
        self.setWindowTitle(f'Nova chatting - {username}')
        self.setGeometry(100, 100, 1000, 700)
        self._setup_ui()
        self._load_friends()
        self._start_message_listener()
    
    def _start_message_listener(self):
        """启动消息监听器"""
        self.message_timer = QTimer(self)
        self.message_timer.timeout.connect(self._check_new_messages)
        self.message_timer.start(500)
        
        # 定时刷新好友列表（每30秒）
        self.friends_refresh_timer = QTimer(self)
        self.friends_refresh_timer.timeout.connect(self._load_friends)
        self.friends_refresh_timer.start(30000)
        
        # 心跳定时器（每10秒发送一次心跳包）
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self._send_heartbeat)
        self.heartbeat_timer.start(10000)  # 10秒
    
    def _send_heartbeat(self):
        """发送心跳包"""
        if self.client and self.client.authenticated:
            self.client.send_heartbeat()
    
    def _check_new_messages(self):
        """检查新消息"""
        if not self.client:
            return
        
        messages_to_remove = []
        for i, msg in enumerate(self.client.message_queue):
            msg_type = msg.get('type')
            
            if msg_type == 'chat':
                messages_to_remove.append(i)
                from_user = msg.get('from', '')
                content = msg.get('content', '')
                
                if self.current_chat_friend == from_user:
                    self.chat_history.append(f'<div style="margin: 8px 0; padding: 10px 15px; background-color: white; border-radius: 8px; display: inline-block;"><b style="color: #1890FF;">{from_user}:</b> {content}</div>')
                else:
                    self.chat_history.append(f'<div style="margin: 8px 0; padding: 10px 15px; background-color: #FFF7E6; border-radius: 8px;"><b style="color: #FA8C16;">[来自 {from_user}]</b> {content}</div>')
            
            elif msg_type == 'offline_messages':
                messages_to_remove.append(i)
                offline_messages = msg.get('messages', [])
                if offline_messages:
                    # 显示离线消息
                    for om in offline_messages:
                        sender = om.get('sender_username', '未知用户')
                        content = om.get('content', '')
                        self.chat_history.append(f'<div style="margin: 8px 0; padding: 10px 15px; background-color: #E6F7FF; border-radius: 8px;"><b style="color: #1890FF;">[离线消息] {sender}:</b> {content}</div>')
            
            elif msg_type == 'friend_request_accepted':
                messages_to_remove.append(i)
                self._load_friends()
            
            elif msg_type == 'kicked':
                messages_to_remove.append(i)
                QMessageBox.warning(self, '账号被踢出', msg.get('message', '您的账号在其他地方登录'))
                self.close()
            
            elif msg_type == 'file_transfer_request':
                messages_to_remove.append(i)
                from_username = msg.get('from_username')
                file_name = msg.get('file_name')
                file_size = msg.get('file_size', 0)
                
                # 显示文件传输请求
                reply = QMessageBox.question(
                    self, 
                    '文件传输请求', 
                    f'用户 {from_username} 想要发送文件:\n{file_name} ({file_size} bytes)\n\n是否接受？',
                    QMessageBox.Yes | QMessageBox.No
                )
                
                # 发送响应
                accepted = reply == QMessageBox.Yes
                self.client.send_file_response(from_username, accepted)
                
                if accepted:
                    self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #E6F7FF; border-radius: 6px; display: inline-block;"><b style="color: #1890FF;">[文件接收]</b> 接受文件: {file_name} ({file_size} bytes)</div>')
                else:
                    self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #FFF1F0; border-radius: 6px; display: inline-block;"><b style="color: #FF4D4F;">[文件接收]</b> 拒绝文件: {file_name}</div>')
            
            elif msg_type == 'file_data':
                messages_to_remove.append(i)
                from_username = msg.get('from_username')
                file_name = msg.get('file_name')
                file_data_base64 = msg.get('data')
                
                # 解码base64数据
                try:
                    file_data = base64.b64decode(file_data_base64)
                except Exception as e:
                    self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #FFF1F0; border-radius: 6px; display: inline-block;"><b style="color: #FF4D4F;">[文件接收]</b> 解码文件数据失败: {str(e)}</div>')
                    continue
                
                # 保存文件数据到待下载列表
                self.file_counter += 1
                file_id = self.file_counter
                self.pending_files[file_id] = {
                    'from': from_username,
                    'name': file_name,
                    'data': file_data
                }
                
                # 显示文件接收信息
                self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #E6F7FF; border-radius: 6px; display: inline-block;"><b style="color: #1890FF;">[文件接收]</b> 收到文件: {file_name} ({len(file_data)} bytes) - 请在下方下载区域下载</div>')
                
                # 添加到文件下载区域
                self._add_file_to_download_list(file_id, from_username, file_name, len(file_data))
        
        for i in reversed(messages_to_remove):
            del self.client.message_queue[i]
    
    def _load_friends(self):
        """加载好友列表"""
        if self.client and self.client.authenticated:
            self.client.get_friends()
            import time
            for _ in range(10):
                for i, msg in enumerate(self.client.message_queue):
                    if msg.get('type') == 'friends_list':
                        del self.client.message_queue[i]
                        friends = msg.get('friends', [])
                        self.friends_list.clear()
                        for friend in friends:
                            status = friend.get('status', 'offline')
                            username = friend.get('username', '')
                            is_online = status == 'online'
                            status_indicator = '🟢' if is_online else '⚫'
                            item_text = f"  {status_indicator} {username}"
                            item = QListWidgetItem(item_text)
                            if is_online:
                                item.setForeground(QColor('#52C41A'))
                            else:
                                item.setForeground(QColor('#8C8C8C'))
                            self.friends_list.addItem(item)
                        break
                else:
                    time.sleep(0.2)
                    continue
                break
    
    def _load_user_avatar(self):
        """加载用户头像"""
        try:
            # 如果用户有自定义头像
            if self.user_avatar and os.path.exists(self.user_avatar):
                pixmap = QPixmap(self.user_avatar)
                if not pixmap.isNull():
                    # 创建圆形头像
                    size = 80
                    rounded_pixmap = QPixmap(size, size)
                    rounded_pixmap.fill(Qt.transparent)
                    
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    
                    # 创建圆形路径
                    path = QPainterPath()
                    path.addEllipse(0, 0, size, size)
                    painter.setClipPath(path)
                    
                    # 缩放并绘制头像
                    scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    
                    return rounded_pixmap
            
            # 使用默认头像
            import random
            default_avatars = ['w.webp', 'm.webp']
            
            # 根据用户名选择默认头像（简单规则：用户名以特定字母开头）
            if self.username:
                first_char = self.username[0].lower()
                if first_char in 'abcdef':
                    default_avatar = 'w.webp'
                else:
                    default_avatar = 'm.webp'
            else:
                default_avatar = random.choice(default_avatars)
            
            # 检查默认头像是否存在
            if os.path.exists(default_avatar):
                pixmap = QPixmap(default_avatar)
                if not pixmap.isNull():
                    # 创建圆形头像
                    size = 80
                    rounded_pixmap = QPixmap(size, size)
                    rounded_pixmap.fill(Qt.transparent)
                    
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    
                    # 创建圆形路径
                    path = QPainterPath()
                    path.addEllipse(0, 0, size, size)
                    painter.setClipPath(path)
                    
                    # 缩放并绘制头像
                    scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    
                    return rounded_pixmap
            
            return None
            
        except Exception as e:
            logger.error(f"加载用户头像失败: {e}")
            return None
    
    def _setup_ui(self):
        """设置UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 左侧边栏
        left_panel = QWidget()
        left_panel.setFixedWidth(260)
        left_panel.setStyleSheet("background-color: #2E2E2E;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 用户信息头部
        user_header = QWidget()
        user_header.setStyleSheet("background-color: #1E1E1E; padding: 20px;")
        user_header_layout = QVBoxLayout(user_header)
        user_header_layout.setAlignment(Qt.AlignCenter)
        
        # 显示用户头像
        user_avatar_label = QLabel()
        user_avatar_label.setFixedSize(80, 80)
        user_avatar_label.setAlignment(Qt.AlignCenter)
        
        # 加载头像
        avatar_pixmap = self._load_user_avatar()
        if avatar_pixmap:
            user_avatar_label.setPixmap(avatar_pixmap)
        else:
            user_avatar_label.setText("👤")
            user_avatar_label.setStyleSheet("font-size: 48px;")
        
        user_header_layout.addWidget(user_avatar_label, 0, Qt.AlignCenter)
        
        user_name = QLabel(self.username)
        user_name.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        user_name.setAlignment(Qt.AlignCenter)
        user_header_layout.addWidget(user_name, 0, Qt.AlignCenter)
        
        left_layout.addWidget(user_header)
        
        # 好友列表标题栏
        friends_header = QWidget()
        friends_header.setStyleSheet("background-color: #2E2E2E; padding: 8px;")
        friends_header_layout = QHBoxLayout(friends_header)
        friends_header_layout.setContentsMargins(10, 5, 10, 5)
        
        friends_title = QLabel('好友列表')
        friends_title.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        friends_header_layout.addWidget(friends_title)
        
        refresh_btn = QPushButton('刷新')
        refresh_btn.setFixedSize(50, 26)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E3E3E;
                color: #AAAAAA;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4E4E4E;
                color: white;
            }
        """)
        refresh_btn.clicked.connect(self._load_friends)
        refresh_btn.setToolTip('刷新好友列表')
        friends_header_layout.addWidget(refresh_btn)
        
        left_layout.addWidget(friends_header)
        
        # 好友列表
        self.friends_list = QListWidget()
        self.friends_list.setStyleSheet("""
            QListWidget {
                background-color: #2E2E2E;
                border: none;
                color: white;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-bottom: 1px solid #3E3E3E;
            }
            QListWidget::item:selected {
                background-color: #3E3E3E;
            }
            QListWidget::item:hover {
                background-color: #383838;
            }
        """)
        self.friends_list.itemDoubleClicked.connect(self._on_friend_selected)
        left_layout.addWidget(self.friends_list)
        
        # 功能按钮区
        btn_widget = QWidget()
        btn_widget.setStyleSheet("background-color: #1E1E1E; padding: 10px;")
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setSpacing(10)
        
        add_friend_btn = QPushButton('➕ 添加')
        add_friend_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E3E3E;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #4E4E4E; }
        """)
        add_friend_btn.clicked.connect(self.show_add_friend_dialog)
        btn_layout.addWidget(add_friend_btn)
        
        friend_req_btn = QPushButton('📨 申请')
        friend_req_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E3E3E;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #4E4E4E; }
        """)
        friend_req_btn.clicked.connect(self.show_friend_requests)
        btn_layout.addWidget(friend_req_btn)
        
        # 修改资料按钮
        profile_btn = QPushButton('👤 资料')
        profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E3E3E;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #4E4E4E; }
        """)
        profile_btn.clicked.connect(self.show_profile_dialog)
        btn_layout.addWidget(profile_btn)
        
        left_layout.addWidget(btn_widget)
        layout.addWidget(left_panel)
        
        # 右侧聊天区域
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #F5F5F5;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 聊天标题栏
        self.chat_title = QLabel('请选择好友开始聊天')
        self.chat_title.setAlignment(Qt.AlignCenter)
        self.chat_title.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            padding: 18px;
            background-color: white;
            border-bottom: 1px solid #E0E0E0;
            color: #333;
        """)
        right_layout.addWidget(self.chat_title)
        
        # 聊天记录区域
        chat_widget = QWidget()
        chat_widget.setStyleSheet("background-color: #EFEFEF;")
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: #EFEFEF;
                border: none;
                padding: 15px;
                font-size: 14px;
            }
        """)
        chat_layout.addWidget(self.chat_history)
        
        # 文件下载区域
        self.file_download_widget = QWidget()
        self.file_download_widget.setStyleSheet("background-color: white; border-top: 1px solid #E0E0E0;")
        file_download_layout = QVBoxLayout(self.file_download_widget)
        file_download_layout.setContentsMargins(10, 5, 10, 5)
        file_download_layout.setSpacing(5)
        
        self.file_download_title = QLabel('待下载文件')
        self.file_download_title.setStyleSheet("font-weight: bold; color: #1890FF; font-size: 12px;")
        file_download_layout.addWidget(self.file_download_title)
        
        self.file_download_list = QWidget()
        self.file_download_list_layout = QVBoxLayout(self.file_download_list)
        self.file_download_list_layout.setContentsMargins(0, 0, 0, 0)
        self.file_download_list_layout.setSpacing(3)
        file_download_layout.addWidget(self.file_download_list)
        
        self.file_download_widget.setVisible(False)  # 默认隐藏
        chat_layout.addWidget(self.file_download_widget)
        
        right_layout.addWidget(chat_widget)
        
        # 输入区域
        input_widget = QWidget()
        input_widget.setFixedHeight(140)
        input_widget.setStyleSheet("background-color: white; border-top: 1px solid #E0E0E0;")
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(15, 10, 15, 10)
        input_layout.setSpacing(8)
        
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText('请输入消息...')
        self.message_input.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: 1px solid #1890FF;
            }
        """)
        self.message_input.setMaximumHeight(70)
        input_layout.addWidget(self.message_input)
        
        send_btn_layout = QHBoxLayout()
        
        # 发送文件按钮
        send_file_btn = ModernButton('📎 发送文件', 'default')
        send_file_btn.clicked.connect(self.send_file)
        send_btn_layout.addWidget(send_file_btn)
        
        send_btn_layout.addStretch()
        
        send_btn = ModernButton('发 送', 'primary')
        send_btn.clicked.connect(self.send_message)
        send_btn_layout.addWidget(send_btn)
        
        input_layout.addLayout(send_btn_layout)
        right_layout.addWidget(input_widget)
        
        layout.addWidget(right_panel)
    
    def _on_friend_selected(self, item):
        """选择好友开始聊天"""
        friend_text = item.text().strip()
        # 格式: "🟢 username" 或 "⚫ username"
        parts = friend_text.split()
        if len(parts) >= 2:
            self.current_chat_friend = parts[-1]
        else:
            self.current_chat_friend = friend_text
        self.chat_title.setText(f'与 {self.current_chat_friend} 聊天')
        self.chat_history.clear()
        self.chat_history.append(f'<div style="color: #999; text-align: center;">开始与 {self.current_chat_friend} 的对话</div>')
    
    def closeEvent(self, event):
        """窗口关闭事件 - 发送注销命令"""
        if self.client and self.client.authenticated:
            self.client.logout()
            logger.info(f"👋 用户 {self.username} 已注销退出")
        event.accept()
    
    def send_file(self):
        """发送文件"""
        if not self.current_chat_friend:
            QMessageBox.warning(self, '提示', '请先选择好友开始聊天')
            return
        
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, '选择文件', '', '所有文件 (*.*)')
        
        if file_path:
            import os
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # 显示发送状态
            self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #E6F7FF; border-radius: 6px; display: inline-block;"><b style="color: #1890FF;">[文件发送]</b> 正在发送: {file_name} ({file_size} bytes)</div>')
            
            # 读取文件数据
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
            except Exception as e:
                self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #FFF1F0; border-radius: 6px; display: inline-block;"><b style="color: #FF4D4F;">[文件发送]</b> 文件读取失败: {str(e)}</div>')
                return
            
            # 发送文件传输请求
            self.client.send_file_request(self.current_chat_friend, file_name, file_size)
            
            # 等待接收响应
            import time
            response_received = False
            for _ in range(20):  # 增加等待时间
                for i, msg in enumerate(self.client.message_queue):
                    if msg.get('type') == 'file_transfer_response':
                        del self.client.message_queue[i]
                        response_received = True
                        accepted = msg.get('accepted', False)
                        
                        if accepted:
                            # 发送文件数据
                            try:
                                self.client.send_file_data(self.current_chat_friend, file_name, file_data)
                                self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #F6FFED; border-radius: 6px; display: inline-block;"><b style="color: #52C41A;">[文件发送]</b> 文件发送成功: {file_name}</div>')
                            except Exception as e:
                                self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #FFF1F0; border-radius: 6px; display: inline-block;"><b style="color: #FF4D4F;">[文件发送]</b> 文件发送失败: {str(e)}</div>')
                        else:
                            self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #FFF1F0; border-radius: 6px; display: inline-block;"><b style="color: #FF4D4F;">[文件发送]</b> 对方拒绝接收文件</div>')
                        break
                
                if response_received:
                    break
                    
                time.sleep(0.3)
            
            if not response_received:
                self.chat_history.append(f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #FFF7E6; border-radius: 6px; display: inline-block;"><b style="color: #FA8C16;">[文件发送]</b> 等待响应超时</div>')
    
    def _add_file_to_download_list(self, file_id, from_username, file_name, file_size):
        """添加文件到下载列表"""
        # 显示文件下载区域
        self.file_download_widget.setVisible(True)
        
        # 创建文件项
        file_item = QWidget()
        file_item.setStyleSheet("background-color: #F5F5F5; border-radius: 4px; padding: 5px;")
        file_item_layout = QHBoxLayout(file_item)
        file_item_layout.setContentsMargins(8, 5, 8, 5)
        file_item_layout.setSpacing(10)
        
        # 文件图标和信息
        file_info = QLabel(f'📄 {file_name} ({from_username}) - {file_size} bytes')
        file_info.setStyleSheet("color: #333; font-size: 12px;")
        file_item_layout.addWidget(file_info)
        
        file_item_layout.addStretch()
        
        # 下载按钮
        download_btn = QPushButton('下载')
        download_btn.setFixedSize(60, 26)
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #1890FF;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #40A9FF;
            }
        """)
        download_btn.clicked.connect(lambda: self._download_file(file_id, file_item))
        file_item_layout.addWidget(download_btn)
        
        # 取消按钮
        cancel_btn = QPushButton('取消')
        cancel_btn.setFixedSize(60, 26)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF4D4F;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #FF7875;
            }
        """)
        cancel_btn.clicked.connect(lambda: self._cancel_file_download(file_id, file_item))
        file_item_layout.addWidget(cancel_btn)
        
        # 添加到列表
        self.file_download_list_layout.addWidget(file_item)
    
    def _cancel_file_download(self, file_id, file_item):
        """取消文件下载"""
        if file_id in self.pending_files:
            file_name = self.pending_files[file_id]['name']
            del self.pending_files[file_id]
            
            # 在聊天记录中显示取消信息
            self.chat_history.append(
                f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #FFF7E6; border-radius: 6px; display: inline-block;">'
                f'<b style="color: #FA8C16;">[文件接收]</b> 已取消下载: {file_name}'
                f'</div>'
            )
        
        # 移除文件项
        file_item.deleteLater()
        
        # 如果没有待下载文件，隐藏下载区域
        if not self.pending_files:
            self.file_download_widget.setVisible(False)
    
    def _download_file(self, file_id, file_item):
        """下载文件"""
        if file_id not in self.pending_files:
            return
        
        file_info = self.pending_files[file_id]
        file_name = file_info['name']
        file_data = file_info['data']
        
        # 弹出保存对话框
        from PyQt5.QtWidgets import QFileDialog
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            '保存文件', 
            file_name, 
            '所有文件 (*.*)'
        )
        
        if save_path:
            try:
                with open(save_path, 'wb') as f:
                    f.write(file_data)
                
                # 在聊天记录中显示保存成功
                self.chat_history.append(
                    f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #F6FFED; border-radius: 6px; display: inline-block;">'
                    f'<b style="color: #52C41A;">[文件接收]</b> 文件已保存: {file_name}'
                    f'</div>'
                )
                
                # 从待下载列表中移除
                del self.pending_files[file_id]
                file_item.deleteLater()
                
                # 如果没有待下载文件，隐藏下载区域
                if not self.pending_files:
                    self.file_download_widget.setVisible(False)
                
            except Exception as e:
                QMessageBox.critical(self, '错误', f'保存文件失败:\n{str(e)}')
        else:
            # 用户取消保存
            self.chat_history.append(
                f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #FFF7E6; border-radius: 6px; display: inline-block;">'
                f'<b style="color: #FA8C16;">[文件接收]</b> 已取消保存: {file_name}'
                f'</div>'
            )
    
    def show_profile_dialog(self):
        """显示个人资料对话框"""
        dialog = ProfileDialog(self.username, self.client, self)
        dialog.exec_()
    
    def show_add_friend_dialog(self):
        """显示添加好友对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle('添加好友')
        dialog.setFixedSize(450, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QLabel {
                font-size: 13px;
                color: #333;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #1890FF;
            }
            QRadioButton {
                font-size: 13px;
                color: #333;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F0F0F0;
            }
            QListWidget::item:selected {
                background-color: #E6F7FF;
                color: #1890FF;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 搜索类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel('搜索方式:')
        type_label.setStyleSheet("font-weight: bold;")
        type_layout.addWidget(type_label)
        
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup, QListWidget, QListWidgetItem
        
        search_type_group = QButtonGroup(dialog)
        username_radio = QRadioButton('用户名模糊搜索')
        id_radio = QRadioButton('ID精准查找')
        username_radio.setChecked(True)
        search_type_group.addButton(username_radio, 0)
        search_type_group.addButton(id_radio, 1)
        type_layout.addWidget(username_radio)
        type_layout.addWidget(id_radio)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # 搜索输入框
        input_layout = QHBoxLayout()
        keyword_input = QLineEdit()
        keyword_input.setPlaceholderText('请输入用户名或ID')
        search_btn = ModernButton('搜 索', 'primary')
        search_btn.setFixedWidth(80)
        input_layout.addWidget(keyword_input)
        input_layout.addWidget(search_btn)
        layout.addLayout(input_layout)
        
        # 搜索结果列表
        layout.addWidget(QLabel('搜索结果:'))
        result_list = QListWidget()
        result_list.setMinimumHeight(150)
        layout.addWidget(result_list)
        
        # 存储搜索结果
        search_results = []
        
        def do_search():
            keyword = keyword_input.text().strip()
            if not keyword:
                QMessageBox.warning(dialog, '提示', '请输入搜索关键词')
                return
            
            search_type = 'id' if search_type_group.checkedId() == 1 else 'username'
            
            if not self.client or not self.client.authenticated:
                QMessageBox.warning(dialog, '错误', '未连接到服务器')
                return
            
            # 发送搜索请求
            self.client.send_message({
                'type': 'search_user',
                'keyword': keyword,
                'search_type': search_type
            })
            
            # 等待响应
            import time
            for _ in range(20):
                for i, msg in enumerate(self.client.message_queue):
                    if msg.get('type') == 'search_result':
                        del self.client.message_queue[i]
                        search_results.clear()
                        search_results.extend(msg.get('users', []))
                        break
                else:
                    time.sleep(0.1)
                    continue
                break
            
            # 显示结果
            result_list.clear()
            if search_results:
                for user in search_results:
                    status_text = {'online': '在线', 'offline': '离线', 'banned': '禁言'}.get(user.get('status', 'offline'), '离线')
                    username = user.get('username', '')
                    item_text = f"[ID:{user['id']}] {username} ({status_text})"
                    item = QListWidgetItem(item_text)
                    item.setForeground(QColor('#333'))
                    item.setData(Qt.UserRole, user)
                    result_list.addItem(item)
                result_list.setCurrentRow(0)
            else:
                QMessageBox.information(dialog, '提示', '未找到相关用户')
        
        def do_add():
            current_item = result_list.currentItem()
            if not current_item:
                QMessageBox.warning(dialog, '提示', '请先搜索并选择要添加的好友')
                return
            
            user = current_item.data(Qt.UserRole)
            target_username = user.get('username', '')
            
            if not self.client or not self.client.authenticated:
                QMessageBox.warning(dialog, '错误', '未连接到服务器')
                return
            
            # 发送好友请求
            success = self.client.add_friend(target_username)
            if success:
                QMessageBox.information(dialog, '成功', f'已向 {target_username} 发送好友申请')
                dialog.accept()
            else:
                QMessageBox.warning(dialog, '失败', '发送好友申请失败，请稍后重试')
        
        search_btn.clicked.connect(do_search)
        keyword_input.returnPressed.connect(do_search)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        add_btn = ModernButton('添加好友', 'success')
        cancel_btn = ModernButton('取 消', 'default')
        add_btn.clicked.connect(do_add)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec_()
    
    def show_friend_requests(self):
        """显示好友申请"""
        if FRIEND_REQUEST_UI_AVAILABLE and FriendRequestManager:
            dialog = FriendRequestManager(self.client, self)
            dialog.exec_()
        else:
            QMessageBox.information(self, '提示', '好友申请功能暂不可用')
    
    def send_message(self):
        """发送消息"""
        if not self.current_chat_friend:
            QMessageBox.warning(self, '提示', '请先选择好友开始聊天')
            return
        
        message = self.message_input.toPlainText().strip()
        if not message:
            return
        
        # 发送消息到服务器
        if self.client and self.client.authenticated:
            self.client.send_chat(self.current_chat_friend, message)
            self.chat_history.append(f'<div style="text-align: right;"><b>{self.username}:</b> {message}</div>')
            self.message_input.clear()
        else:
            QMessageBox.warning(self, '错误', '未连接到服务器')


class FileDownloadDialog(QDialog):
    """文件下载对话框"""
    def __init__(self, from_username, file_name, file_data, parent=None):
        super().__init__(parent)
        self.from_username = from_username
        self.file_name = file_name
        self.file_data = file_data
        self.parent_window = parent
        self.setWindowTitle('文件下载')
        self.setFixedSize(400, 250)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel('📁 收到新文件')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1890FF; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # 文件信息
        info_widget = QWidget()
        info_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #D9D9D9;
                border-radius: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(15, 15, 15, 15)
        info_layout.setSpacing(10)
        
        # 发送者
        sender_label = QLabel(f'发送者: {self.from_username}')
        sender_label.setStyleSheet("font-size: 14px; color: #333;")
        info_layout.addWidget(sender_label)
        
        # 文件名
        name_label = QLabel(f'文件名: {self.file_name}')
        name_label.setStyleSheet("font-size: 14px; color: #333; font-weight: bold;")
        info_layout.addWidget(name_label)
        
        # 文件大小
        size_kb = len(self.file_data) / 1024
        size_text = f'{size_kb:.2f} KB' if size_kb < 1024 else f'{size_kb/1024:.2f} MB'
        size_label = QLabel(f'文件大小: {size_text}')
        size_label.setStyleSheet("font-size: 14px; color: #666;")
        info_layout.addWidget(size_label)
        
        layout.addWidget(info_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        download_btn = ModernButton('📥 下载文件', 'primary')
        download_btn.clicked.connect(self._download_file)
        btn_layout.addWidget(download_btn)
        
        cancel_btn = ModernButton('取 消', 'default')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _download_file(self):
        """下载文件"""
        from PyQt5.QtWidgets import QFileDialog
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            '保存文件', 
            self.file_name, 
            '所有文件 (*.*)'
        )
        
        if save_path:
            try:
                with open(save_path, 'wb') as f:
                    f.write(self.file_data)
                
                # 在聊天记录中显示保存成功
                if self.parent_window:
                    self.parent_window.chat_history.append(
                        f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #F6FFED; border-radius: 6px; display: inline-block;">'
                        f'<b style="color: #52C41A;">[文件接收]</b> 文件已保存: {self.file_name}'
                        f'</div>'
                    )
                
                QMessageBox.information(self, '成功', f'文件已保存到:\n{save_path}')
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, '错误', f'保存文件失败:\n{str(e)}')
        else:
            # 用户取消保存
            if self.parent_window:
                self.parent_window.chat_history.append(
                    f'<div style="margin: 8px 0; padding: 8px 12px; background-color: #FFF7E6; border-radius: 6px; display: inline-block;">'
                    f'<b style="color: #FA8C16;">[文件接收]</b> 已取消保存: {self.file_name}'
                    f'</div>'
                )


class ProfileDialog(QDialog):
    """个人资料对话框"""
    def __init__(self, username, client, parent=None):
        super().__init__(parent)
        self.username = username
        self.client = client
        self.avatar_path = getattr(client, 'avatar', '')  # 保存当前头像路径
        self.setWindowTitle('个人资料')
        self.setFixedSize(450, 550)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
            QLabel {
                font-size: 14px;
                color: #333;
                font-weight: bold;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #1890FF;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel('个人资料')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1890FF; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # 头像区域
        avatar_group = QGroupBox("头像设置")
        avatar_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        avatar_main_layout = QVBoxLayout(avatar_group)
        
        # 当前头像显示
        current_avatar_layout = QHBoxLayout()
        current_avatar_label = QLabel('当前头像:')
        current_avatar_label.setStyleSheet("font-weight: normal; color: #666;")
        current_avatar_layout.addWidget(current_avatar_label)
        
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(70, 70)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet("border: 2px solid #D9D9D9; border-radius: 35px;")
        self._update_avatar_display()
        current_avatar_layout.addWidget(self.avatar_label)
        current_avatar_layout.addStretch()
        avatar_main_layout.addLayout(current_avatar_layout)
        
        # 默认头像选择
        default_avatar_layout = QHBoxLayout()
        default_avatar_label = QLabel('默认头像:')
        default_avatar_label.setStyleSheet("font-weight: normal; color: #666;")
        default_avatar_layout.addWidget(default_avatar_label)
        
        self.male_avatar_btn = QPushButton()
        self.male_avatar_btn.setFixedSize(50, 50)
        self.male_avatar_btn.setToolTip('男性头像')
        self.male_avatar_btn.clicked.connect(lambda: self._select_default_avatar('m.webp'))
        self._set_default_avatar_button(self.male_avatar_btn, 'm.webp')
        default_avatar_layout.addWidget(self.male_avatar_btn)
        
        self.female_avatar_btn = QPushButton()
        self.female_avatar_btn.setFixedSize(50, 50)
        self.female_avatar_btn.setToolTip('女性头像')
        self.female_avatar_btn.clicked.connect(lambda: self._select_default_avatar('w.webp'))
        self._set_default_avatar_button(self.female_avatar_btn, 'w.webp')
        default_avatar_layout.addWidget(self.female_avatar_btn)
        
        # 上传自定义头像按钮
        upload_btn = ModernButton('上传自定义头像', 'primary')
        upload_btn.clicked.connect(self._upload_custom_avatar)
        default_avatar_layout.addWidget(upload_btn)
        
        default_avatar_layout.addStretch()
        avatar_main_layout.addLayout(default_avatar_layout)
        
        layout.addWidget(avatar_group)
        
        # 表单
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # 用户名（不可修改）
        username_label = QLabel('用户名:')
        self.username_input = QLineEdit(self.username)
        self.username_input.setReadOnly(True)
        form_layout.addRow(username_label, self.username_input)
        
        # 新密码
        password_label = QLabel('新密码:')
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('不修改请留空')
        form_layout.addRow(password_label, self.password_input)
        
        # 确认密码
        confirm_label = QLabel('确认密码:')
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText('不修改请留空')
        form_layout.addRow(confirm_label, self.confirm_input)
        
        layout.addLayout(form_layout)
        
        # 状态标签
        self.status_label = QLabel('')
        self.status_label.setStyleSheet("color: #666; font-size: 12px; font-weight: normal;")
        layout.addWidget(self.status_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = ModernButton('保 存', 'primary')
        save_btn.clicked.connect(self.save_profile)
        cancel_btn = ModernButton('取 消', 'default')
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        layout.addStretch()
    
    def _update_avatar_display(self):
        """更新头像显示"""
        try:
            if self.avatar_path and os.path.exists(self.avatar_path):
                pixmap = QPixmap(self.avatar_path)
                if not pixmap.isNull():
                    # 创建圆形头像
                    size = 70
                    rounded_pixmap = QPixmap(size, size)
                    rounded_pixmap.fill(Qt.transparent)
                    
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    
                    # 创建圆形路径
                    path = QPainterPath()
                    path.addEllipse(0, 0, size, size)
                    painter.setClipPath(path)
                    
                    # 缩放并绘制头像
                    scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    
                    self.avatar_label.setPixmap(rounded_pixmap)
                    return
        except Exception as e:
            logger.error(f"更新头像显示失败: {e}")
        
        # 显示默认头像
        import random
        default_avatars = ['w.webp', 'm.webp']
        
        # 根据用户名选择默认头像
        if self.username:
            first_char = self.username[0].lower()
            if first_char in 'abcdef':
                default_avatar = 'w.webp'
            else:
                default_avatar = 'm.webp'
        else:
            default_avatar = random.choice(default_avatars)
        
        # 尝试加载默认头像
        if os.path.exists(default_avatar):
            pixmap = QPixmap(default_avatar)
            if not pixmap.isNull():
                # 创建圆形头像
                size = 70
                rounded_pixmap = QPixmap(size, size)
                rounded_pixmap.fill(Qt.transparent)
                
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                
                # 创建圆形路径
                path = QPainterPath()
                path.addEllipse(0, 0, size, size)
                painter.setClipPath(path)
                
                # 缩放并绘制头像
                scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.end()
                
                self.avatar_label.setPixmap(rounded_pixmap)
                return
        
        # 如果默认头像也不存在，显示图标
        self.avatar_label.setText("👤")
        self.avatar_label.setStyleSheet("font-size: 40px; border: 2px solid #D9D9D9; border-radius: 35px;")
    
    def _set_default_avatar_button(self, button, avatar_file):
        """设置默认头像按钮"""
        try:
            if os.path.exists(avatar_file):
                pixmap = QPixmap(avatar_file)
                if not pixmap.isNull():
                    button.setIcon(QIcon(pixmap))
                    button.setIconSize(QSize(46, 46))
                    button.setStyleSheet("border: 2px solid #D9D9D9; border-radius: 25px;")
                    return
        except Exception as e:
            logger.error(f"设置默认头像按钮失败: {e}")
        
        button.setText('👤' if avatar_file == 'm.webp' else '👩')
        button.setStyleSheet("font-size: 24px; border: 2px solid #D9D9D9; border-radius: 25px;")
    
    def _select_default_avatar(self, avatar_file):
        """选择默认头像"""
        if os.path.exists(avatar_file):
            self.avatar_path = avatar_file
            self._update_avatar_display()
    
    def _upload_custom_avatar(self):
        """上传自定义头像"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '选择头像', 
            '', 
            '图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)'
        )
        
        if file_path:
            self.avatar_path = file_path
            self._update_avatar_display()
    
    def save_profile(self):
        """保存个人资料"""
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        
        if password:
            if len(password) < 6:
                QMessageBox.warning(self, '警告', '密码长度至少6位！')
                return
            
            if password != confirm:
                QMessageBox.warning(self, '警告', '两次输入的密码不一致！')
                return
        
        self.status_label.setText('正在保存...')
        
        try:
            # 构建更新数据
            update_data = {}
            if password:
                update_data['password'] = password
            
            if self.avatar_path:
                update_data['avatar'] = self.avatar_path
            
            if update_data:
                # 发送更新请求
                success = self.client.update_profile(**update_data)
                
                if success:
                    # 更新客户端的头像信息
                    if self.avatar_path:
                        self.client.avatar = self.avatar_path
                    QMessageBox.information(self, '成功', '个人资料更新成功！')
                    self.accept()
                else:
                    QMessageBox.warning(self, '失败', '更新失败，请稍后重试')
            else:
                QMessageBox.information(self, '提示', '没有需要更新的内容')
                self.accept()
                
        except Exception as e:
            QMessageBox.critical(self, '错误', f'更新过程中发生错误: {str(e)}')
        finally:
            self.status_label.setText('')


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    login_dialog = LoginDialog()
    login_dialog.exec_()



