# server_ui.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QStatusBar,
    QGroupBox, QListWidget, QLineEdit,
    QSpinBox, QFormLayout, QSplitter,
    QAction, QStyleFactory, QMessageBox, QApplication,
    QMenu, QSystemTrayIcon, QMenuBar, QFileDialog,
    QGridLayout, QComboBox, QCheckBox, QInputDialog, QDialog, QDialogButtonBox,
    QFrame, QScrollArea
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCursor, QPalette, QLinearGradient, QPainter
import sys
import json
import os
from datetime import datetime
import psutil
import logging

try:
    from database import UserDatabase
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入数据库模块: {e}")
    DATABASE_AVAILABLE = False
    UserDatabase = None

try:
    from network_server import NetworkServer
    NETWORK_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入网络服务器模块: {e}")
    NETWORK_AVAILABLE = False
    NetworkServer = None

# UserManagerWindow的导入将在需要时进行


COLORS = {
    'bg_dark': '#1a1a2e',
    'bg_medium': '#16213e',
    'bg_light': '#0f3460',
    'accent': '#e94560',
    'accent_hover': '#ff6b6b',
    'success': '#00d9a5',
    'warning': '#ffc107',
    'text_primary': '#ffffff',
    'text_secondary': '#a0a0a0',
    'border': '#2d2d44',
    'card': '#1f1f38',
}


class ModernButton(QPushButton):
    def __init__(self, text, color_type='default', parent=None):
        super().__init__(text, parent)
        self.color_type = color_type
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()
    
    def _apply_style(self):
        if self.color_type == 'success':
            bg_color = COLORS['success']
            hover_color = '#00ffbb'
        elif self.color_type == 'danger':
            bg_color = COLORS['accent']
            hover_color = COLORS['accent_hover']
        elif self.color_type == 'primary':
            bg_color = COLORS['bg_light']
            hover_color = '#1a4a7a'
        else:
            bg_color = COLORS['card']
            hover_color = '#2a2a4a'
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {COLORS['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 15px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #3a3a5a;
                color: #6a6a8a;
            }}
        """)


class StatusCard(QFrame):
    def __init__(self, title, value, icon='', parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self._create_ui(title, value, icon)
    
    def _create_ui(self, title, value, icon):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 15px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
        """)
        
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 24px;
            font-weight: bold;
            font-family: 'Segoe UI', 'Microsoft YaHei UI';
        """)
        
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
    
    def set_value(self, value):
        self.value_label.setText(str(value))


class ServerStatusThread(QThread):
    status_updated = pyqtSignal(dict)
    
    def __init__(self, server_instance):
        super().__init__()
        self.server = server_instance
        self.running = True
        
    def run(self):
        while self.running:
            try:
                if self.server and hasattr(self.server, 'get_online_count'):
                    status = {
                        'online_count': self.server.get_online_count(),
                        'running': self.server.running if hasattr(self.server, 'running') else False
                    }
                    self.status_updated.emit(status)
            except Exception as e:
                logging.error(f"状态监控线程异常: {e}")
            self.msleep(1000)
    
    def stop(self):
        """停止线程"""
        self.running = False
        self.quit()
        self.wait(2000)


class ServerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server = None
        self.status_thread = None
        self.user_manager_window = None
        self.start_time = datetime.now()
        
        self.config = self._load_config()
        
        self.db = None
        if DATABASE_AVAILABLE:
            db_path = self.config.get('database', {}).get('path', 'im_database.db')
            try:
                self.db = UserDatabase(db_path)
            except Exception as e:
                print(f"数据库初始化失败: {e}")
                QMessageBox.critical(self, "错误", f"数据库初始化失败: {e}")
        
        self._setup_window()
        self._create_ui()
        self._setup_timers()
        self.update_ui_state(False)
        
        self.log_message("[系统] 服务器界面初始化完成")

    def _setup_window(self):
        self.setWindowTitle('Nova chatting - 服务端')
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(900, 550)

    def _load_config(self):
        config_path = 'config.json'
        default_config = {
            "server": {"host": "127.0.0.1", "port": 8000},
            "database": {"path": "im_database.db"},
            "logging": {"level": "INFO", "log_file": "server.log"}
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                return default_config
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return default_config

    def _setup_timers(self):
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_server_status)
        self.status_timer.start(2000)

    def _create_ui(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['bg_dark']};
            }}
            QWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text_primary']};
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
            }}
            QGroupBox {{
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
                font-size: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
            }}
            QLineEdit {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['accent']};
            }}
            QSpinBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QSpinBox:focus {{
                border: 1px solid {COLORS['accent']};
            }}
            QComboBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {COLORS['text_secondary']};
                margin-right: 8px;
            }}
            QListWidget {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 5px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['bg_light']};
            }}
            QCheckBox {{
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['card']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent']};
                border: 1px solid {COLORS['accent']};
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['bg_medium']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['border']};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QStatusBar {{
                background-color: {COLORS['bg_medium']};
                border-top: 1px solid {COLORS['border']};
                color: {COLORS['text_secondary']};
                font-size: 14px;
            }}
            QToolBar {{
                background-color: {COLORS['bg_medium']};
                border: none;
                spacing: 8px;
                padding: 8px;
            }}
            QToolButton {{
                background-color: transparent;
                color: {COLORS['text_primary']};
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 13px;
            }}
            QToolButton:hover {{
                background-color: {COLORS['card']};
            }}
            QMenu {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 25px;
                border-radius: 4px;
                color: {COLORS['text_primary']};
            }}
            QMenu::item:selected {{
                background-color: {COLORS['bg_light']};
            }}
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        self._create_header(main_layout)
        self._create_status_cards(main_layout)
        
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS['border']};
                width: 2px;
            }}
        """)
        
        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        
        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([280, 1020])
        
        main_layout.addWidget(content_splitter, 1)
        
        self._create_statusbar()
        self._create_toolbar()

    def _create_header(self, parent_layout):
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_medium']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        title_label = QLabel("即时通讯服务端")
        title_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {COLORS['text_primary']};
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        config_layout = QHBoxLayout()
        config_layout.setSpacing(10)
        
        host_label = QLabel("地址:")
        host_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        config_layout.addWidget(host_label)
        
        self.host_input = QLineEdit("127.0.0.1")
        self.host_input.setFixedWidth(120)
        self.host_input.setMinimumHeight(36)
        self.host_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {COLORS['text_primary']};
                font-size: 15px;
            }}
        """)
        config_layout.addWidget(self.host_input)
        
        port_label = QLabel("端口:")
        port_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        config_layout.addWidget(port_label)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(8000)
        self.port_input.setFixedWidth(90)
        self.port_input.setMinimumHeight(36)
        config_layout.addWidget(self.port_input)
        
        header_layout.addLayout(config_layout)
        
        header_layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.start_btn = ModernButton("启动服务", 'success')
        self.start_btn.setFixedSize(130, 42)
        self.start_btn.clicked.connect(self.start_server)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = ModernButton("停止服务", 'danger')
        self.stop_btn.setFixedSize(130, 42)
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        header_layout.addLayout(btn_layout)
        
        parent_layout.addWidget(header_frame)

    def _create_status_cards(self, parent_layout):
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        
        self.status_card = StatusCard("服务状态", "离线")
        self.uptime_card = StatusCard("运行时间", "00:00:00")
        self.clients_card = StatusCard("在线客户端", "0")
        self.cpu_card = StatusCard("CPU占用", "0%")
        self.memory_card = StatusCard("内存占用", "0 MB")
        
        self.status_card.setMinimumWidth(150)
        self.uptime_card.setMinimumWidth(150)
        self.clients_card.setMinimumWidth(150)
        self.cpu_card.setMinimumWidth(130)
        self.memory_card.setMinimumWidth(130)
        
        cards_layout.addWidget(self.status_card)
        cards_layout.addWidget(self.uptime_card)
        cards_layout.addWidget(self.clients_card)
        cards_layout.addWidget(self.cpu_card)
        cards_layout.addWidget(self.memory_card)
        
        parent_layout.addLayout(cards_layout)


    def _create_left_panel(self):
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        users_group = QGroupBox("在线用户")
        users_layout = QVBoxLayout(users_group)
        users_layout.setContentsMargins(15, 20, 15, 15)
        
        self.online_list = QListWidget()
        users_layout.addWidget(self.online_list)
        
        count_layout = QHBoxLayout()
        count_label = QLabel("在线人数:")
        count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.online_count_label = QLabel("0")
        self.online_count_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; font-size: 16px;")
        count_layout.addWidget(count_label)
        count_layout.addWidget(self.online_count_label)
        count_layout.addStretch()
        users_layout.addLayout(count_layout)
        
        left_layout.addWidget(users_group)
        
        actions_group = QGroupBox("快捷操作")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setContentsMargins(15, 20, 15, 15)
        actions_layout.setSpacing(10)
        
        # 始终显示用户管理按钮，点击时会检查模块是否可用
        user_btn = ModernButton("用户管理", 'primary')
        user_btn.clicked.connect(self.open_user_manager)
        actions_layout.addWidget(user_btn)
        
        stats_btn = ModernButton("查看统计", 'primary')
        stats_btn.clicked.connect(self.show_stats)
        actions_layout.addWidget(stats_btn)
        
        settings_btn = ModernButton("服务设置", 'primary')
        settings_btn.clicked.connect(self.open_settings)
        actions_layout.addWidget(settings_btn)
        
        left_layout.addWidget(actions_group)
        
        return left_widget

    def _create_right_panel(self):
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        monitor_group = QGroupBox("活动监控")
        monitor_layout = QVBoxLayout(monitor_group)
        monitor_layout.setContentsMargins(15, 20, 15, 15)
        
        filter_layout = QHBoxLayout()
        
        filter_label = QLabel("筛选:")
        filter_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        filter_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部事件", "登录/退出", "消息", "系统"])
        self.filter_combo.setFixedWidth(150)
        filter_layout.addWidget(self.filter_combo)
        
        filter_layout.addSpacing(20)
        
        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        filter_layout.addWidget(self.auto_scroll_check)
        
        filter_layout.addStretch()
        
        clear_btn = ModernButton("清空日志", 'default')
        clear_btn.setFixedWidth(120)
        clear_btn.clicked.connect(self.clear_log)
        filter_layout.addWidget(clear_btn)
        
        monitor_layout.addLayout(filter_layout)
        
        self.monitor_display = QTextEdit()
        self.monitor_display.setReadOnly(True)
        self.monitor_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                color: {COLORS['text_primary']};
                font-family: 'Consolas', 'Microsoft YaHei UI';
                font-size: 13px;
            }}
        """)
        
        monitor_layout.addWidget(self.monitor_display)
        
        right_layout.addWidget(monitor_group)
        
        return right_widget

    def _create_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_indicator = QLabel("离线")
        self.status_indicator.setStyleSheet(f"""
            color: {COLORS['accent']};
            font-weight: bold;
            font-size: 12px;
            padding: 2px 10px;
            background-color: {COLORS['card']};
            border-radius: 4px;
        """)
        self.status_bar.addPermanentWidget(self.status_indicator)
        
        self.status_connections = QLabel("连接数: 0")
        self.status_connections.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.status_bar.addPermanentWidget(self.status_connections)
        
        self.status_memory = QLabel("内存: -")
        self.status_memory.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.status_bar.addPermanentWidget(self.status_memory)
        
        self.status_time = QLabel("")
        self.status_time.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.status_bar.addPermanentWidget(self.status_time)
        
        self._update_time()
        timer = QTimer(self)
        timer.timeout.connect(self._update_time)
        timer.start(1000)
        
        self.status_bar.showMessage("就绪")

    def _create_toolbar(self):
        toolbar = self.addToolBar("工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        
        toolbar.addAction(self._create_action("启动", self.start_server, "启动服务器"))
        toolbar.addAction(self._create_action("停止", self.stop_server, "停止服务器"))
        toolbar.addSeparator()
        
        # 始终显示用户管理按钮，点击时会检查模块是否可用
        toolbar.addAction(self._create_action("用户", self.open_user_manager, "用户管理"))
        
        toolbar.addAction(self._create_action("统计", self.show_stats, "查看统计"))
        toolbar.addAction(self._create_action("设置", self.open_settings, "服务器设置"))
        toolbar.addSeparator()
        
        toolbar.addAction(self._create_action("帮助", self.show_help, "帮助"))
        toolbar.addAction(self._create_action("关于", self.show_about, "关于"))

    def _create_action(self, text, callback, tip):
        action = QAction(text, self)
        action.triggered.connect(callback)
        action.setToolTip(tip)
        return action

    def _update_time(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.status_time.setText(current_time)

    def update_ui_state(self, server_running: bool):
        if server_running:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.host_input.setEnabled(False)
            self.port_input.setEnabled(False)
            self.status_indicator.setText("在线")
            self.status_indicator.setStyleSheet(f"""
                color: {COLORS['success']};
                font-weight: bold;
                font-size: 12px;
                padding: 2px 10px;
                background-color: {COLORS['card']};
                border-radius: 4px;
            """)
            self.status_card.set_value("运行中")
        else:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.host_input.setEnabled(True)
            self.port_input.setEnabled(True)
            self.status_indicator.setText("离线")
            self.status_indicator.setStyleSheet(f"""
                color: {COLORS['accent']};
                font-weight: bold;
                font-size: 12px;
                padding: 2px 10px;
                background-color: {COLORS['card']};
                border-radius: 4px;
            """)
            self.status_card.set_value("离线")

    def start_server(self):
        host = self.host_input.text().strip()
        port = self.port_input.value()
        
        if not host:
            QMessageBox.warning(self, "警告", "请输入服务器地址!")
            return
        
        if not NETWORK_AVAILABLE or not self.db:
            QMessageBox.critical(self, "错误", "网络服务器或数据库模块不可用!")
            return
        
        try:
            self.server = NetworkServer(
                host=host,
                port=port,
                db=self.db,
                log_callback=self.log_message,
                monitor_callback=self.add_monitor_message
            )
            
            self.server.start()
            
            self.update_ui_state(True)
            self.start_time = datetime.now()
            
            self.status_thread = ServerStatusThread(self.server)
            self.status_thread.status_updated.connect(self._on_status_updated)
            self.status_thread.start()
            
            self.log_message(f"[系统] 服务器已启动，监听 {host}:{port}")
            self.add_monitor_message(f"[{datetime.now().strftime('%H:%M:%S')}] 服务器启动成功")
            self.status_bar.showMessage(f"服务器运行中 - {host}:{port}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动服务器失败: {str(e)}")
            self.log_message(f"[错误] 启动服务器失败: {e}")

    def stop_server(self):
        if self.server:
            self.server.stop()
            
            # 停止状态监控线程
            if self.status_thread and self.status_thread.isRunning():
                self.status_thread.stop()
            
            self.server = None
        
        self.update_ui_state(False)
        self.log_message("[系统] 服务器已停止")
        self.add_monitor_message(f"[{datetime.now().strftime('%H:%M:%S')}] 服务器已停止")
        self.status_bar.showMessage("服务器已停止")

    def _on_status_updated(self, status):
        online_count = status.get('online_count', 0)
        self.clients_card.set_value(str(online_count))
        self.status_connections.setText(f"连接数: {online_count}")

    def update_online_users(self):
        if self.server and hasattr(self.server, 'get_online_users'):
            try:
                online_users = self.server.get_online_users()
                self.online_list.clear()
                
                for user in online_users:
                    self.online_list.addItem(user)
                
                online_count = len(online_users)
                self.online_count_label.setText(str(online_count))
                self.clients_card.set_value(str(online_count))
                
            except Exception as e:
                self.log_message(f"[错误] 更新在线用户失败: {e}")

    def update_server_status(self):
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_card.set_value(f"{cpu_percent:.1f}%")
            
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.memory_card.set_value(f"{memory_mb:.1f} MB")
            self.status_memory.setText(f"内存: {memory_mb:.1f}MB")
            
            if self.server and hasattr(self.server, 'running') and self.server.running:
                uptime = datetime.now() - self.start_time
                hours, remainder = divmod(int(uptime.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.uptime_card.set_value(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
                # 更新在线用户列表
                self.update_online_users()
            
        except Exception as e:
            self.log_message(f"[错误] 更新服务器状态失败: {e}")

    def log_message(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        if "错误" in message or "失败" in message:
            self.status_bar.showMessage(f"错误: {message}", 5000)
        
        logging.info(message)

    def add_monitor_message(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if "登录" in message or "logged in" in message.lower():
            html = f'<div style="color: {COLORS["success"]};">[{timestamp}] {message}</div>'
        elif "退出" in message or "Exit" in message or "left" in message.lower():
            html = f'<div style="color: {COLORS["accent"]};">[{timestamp}] {message}</div>'
        elif "启动" in message.lower():
            html = f'<div style="color: #00b4d8; font-weight: bold;">[{timestamp}] {message}</div>'
        elif "停止" in message.lower():
            html = f'<div style="color: {COLORS["text_secondary"]}; font-weight: bold;">[{timestamp}] {message}</div>'
        elif "消息" in message.lower() or "chat" in message.lower():
            html = f'<div style="color: #9d4edd;">[{timestamp}] {message}</div>'
        else:
            html = f'<div style="color: {COLORS["text_primary"]};">[{timestamp}] {message}</div>'
        
        self.monitor_display.append(html)
        
        if self.auto_scroll_check.isChecked():
            cursor = self.monitor_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.monitor_display.setTextCursor(cursor)

    def clear_log(self):
        self.monitor_display.clear()
        self.add_monitor_message("日志已清空")

    def open_user_manager(self):
        # 动态导入UserManagerWindow
        try:
            from user_ui import UserManagerWindow
            USER_UI_AVAILABLE = True
        except ImportError as e:
            print(f"警告: 无法导入用户界面模块: {e}")
            USER_UI_AVAILABLE = False
            UserManagerWindow = None
        
        if not USER_UI_AVAILABLE or not self.db:
            QMessageBox.warning(self, "警告", "用户管理模块不可用")
            return
            
        try:
            if not hasattr(self, 'user_manager_window') or not self.user_manager_window:
                self.user_manager_window = UserManagerWindow(self.db)
            # 始终将user_manager_window引用传递给server，确保server能访问到最新的窗口实例
            if self.server:
                self.server.user_manager_window = self.user_manager_window
            self.user_manager_window.show()
            self.user_manager_window.raise_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开用户管理失败: {e}")

    def open_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("服务器设置")
        dialog.setFixedSize(400, 300)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
            }}
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QSpinBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("监听端口:"))
        port_input = QSpinBox()
        port_input.setRange(1024, 65535)
        port_input.setValue(self.port_input.value())
        port_layout.addWidget(port_input)
        layout.addLayout(port_layout)
        
        max_conn_layout = QHBoxLayout()
        max_conn_layout.addWidget(QLabel("最大连接数:"))
        max_conn_input = QSpinBox()
        max_conn_input.setRange(1, 1000)
        max_conn_input.setValue(100)
        max_conn_layout.addWidget(max_conn_input)
        layout.addLayout(max_conn_layout)
        
        heartbeat_layout = QHBoxLayout()
        heartbeat_layout.addWidget(QLabel("心跳间隔(秒):"))
        heartbeat_input = QSpinBox()
        heartbeat_input.setRange(10, 300)
        heartbeat_input.setValue(60)
        heartbeat_layout.addWidget(heartbeat_input)
        layout.addLayout(heartbeat_layout)
        
        layout.addStretch()
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_light']};
                color: {COLORS['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #1a4a7a;
            }}
        """)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            self.port_input.setValue(port_input.value())
            self.add_monitor_message(f"[{datetime.now().strftime('%H:%M:%S')}] 设置已更新")

    def show_stats(self):
        try:
            total_users = 0
            online_count = 0
            if self.db:
                users = self.db.get_all_users()
                total_users = len(users)
                online_count = len(self.db.get_online_users()) if hasattr(self.db, 'get_online_users') else 0
            
            server_running = self.server and hasattr(self.server, 'running') and self.server.running
            client_count = self.server.get_online_count() if server_running and hasattr(self.server, 'get_online_count') else 0
            
            stats_text = f"""
服务器统计信息
━━━━━━━━━━━━━━━━━━━━━━
总用户数: {total_users}
当前在线: {online_count}
活跃连接: {client_count}
服务器状态: {'运行中' if server_running else '已停止'}
监听地址: {self.host_input.text()}:{self.port_input.value()}
运行时间: {self.uptime_card.value_label.text()}
CPU占用: {self.cpu_card.value_label.text()}
内存占用: {self.memory_card.value_label.text()}
            """
            
            QMessageBox.information(self, "统计信息", stats_text.strip())
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取统计信息失败: {str(e)}")

    def show_help(self):
        help_text = """
即时通讯服务端 - 帮助

主要功能:
• 启动/停止服务器
• 实时用户监控
• 查看聊天消息
• 用户管理
• 系统状态监控

活动监控:
• 绿色: 用户登录
• 红色: 用户退出
• 紫色: 聊天消息
• 青色: 服务器事件

默认端口: 8000
功能: 用户认证、消息转发、状态通知
        """
        QMessageBox.information(self, "帮助", help_text.strip())

    def show_about(self):
        about_text = """
即时通讯服务端控制台

版本: 1.0.0
作者: 北华航天工业学院 网络工程专业

功能特性:
• 实时用户状态监控
• 消息转发和存储
• 用户认证和管理
• 好友系统管理
• 系统性能监控
• 实时日志显示
        """
        QMessageBox.about(self, "关于", about_text.strip())

    def closeEvent(self, event):
        if self.server and hasattr(self.server, 'running') and self.server.running:
            reply = QMessageBox.question(
                self, '确认退出',
                '服务器正在运行，确定要退出吗？',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.stop_server()
                if self.db:
                    self.db.close()
                event.accept()
            else:
                event.ignore()
        else:
            if self.db:
                self.db.close()
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    app.setApplicationName("即时通讯服务端")
    app.setApplicationVersion("1.0.0")
    
    font = QFont("Segoe UI", 12)
    app.setFont(font)
    
    try:
        window = ServerMainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
