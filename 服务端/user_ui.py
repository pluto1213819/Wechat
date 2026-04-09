# user_ui.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QComboBox,
    QGroupBox, QFormLayout, QMessageBox,
    QDialog, QDialogButtonBox, QInputDialog,
    QHeaderView, QTabWidget, QGridLayout,
    QCheckBox, QSpinBox, QToolBar, QAction, QFileDialog
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QBrush, QPainterPath
from datetime import datetime
import logging
import os

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserManagerWindow(QMainWindow):
    """用户管理窗口"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_users()
    
    def init_ui(self):
        self.setWindowTitle("用户管理")
        self.setGeometry(100, 100, 900, 550)
        
        # 设置字体
        font = QFont("Microsoft YaHei UI", 9)
        self.setFont(font)
        
        # 设置整体样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #1890ff;
            }
            QPushButton:pressed {
                background-color: #e6f7ff;
            }
            QTableWidget {
                border: 1px solid #d9d9d9;
                background-color: #ffffff;
                gridline-color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #fafafa;
                padding: 8px;
                border: 1px solid #d9d9d9;
                font-weight: bold;
                color: #333;
            }
            QLabel {
                color: #333;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("用户管理系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: #333;")
        layout.addWidget(title_label)
        
        # 工具栏按钮
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setToolTip("刷新用户列表")
        refresh_btn.clicked.connect(self.load_users)
        toolbar.addWidget(refresh_btn)
        
        # 添加用户按钮
        add_btn = QPushButton("➕ 添加用户")
        add_btn.setToolTip("添加新用户")
        add_btn.clicked.connect(self.add_user)
        toolbar.addWidget(add_btn)
        
        # 编辑按钮
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.setToolTip("编辑选中用户")
        edit_btn.clicked.connect(self.edit_user)
        toolbar.addWidget(edit_btn)
        
        # 锁定按钮
        lock_btn = QPushButton("🔒 锁定")
        lock_btn.setToolTip("锁定选中用户（禁止登录）")
        lock_btn.clicked.connect(self.lock_user_account)
        toolbar.addWidget(lock_btn)
        
        # 解锁按钮
        unlock_btn = QPushButton("🔓 解锁")
        unlock_btn.setToolTip("解锁选中用户（允许登录）")
        unlock_btn.clicked.connect(self.unlock_user_account)
        toolbar.addWidget(unlock_btn)
        
        # 删除按钮
        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.setToolTip("删除选中用户")
        delete_btn.clicked.connect(self.delete_user)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 用户表格：ID、头像、用户名、密码、状态、锁定状态
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["ID", "头像", "用户名", "密码", "状态", "锁定状态"])
        
        # 设置表格属性
        self.user_table.setAlternatingRowColors(True)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # 设置列宽比例 - 更协调的比例
        header = self.user_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # ID - 固定宽度
        self.user_table.setColumnWidth(0, 60)
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # 头像 - 固定宽度
        self.user_table.setColumnWidth(1, 100)
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 用户名 - 自动拉伸
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 密码 - 自动拉伸
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # 状态 - 固定宽度
        self.user_table.setColumnWidth(4, 80)
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # 锁定状态 - 固定宽度
        self.user_table.setColumnWidth(5, 80)
        
        # 设置行高
        self.user_table.verticalHeader().setDefaultSectionSize(70)
        self.user_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.user_table, 1)
    
    def _create_default_avatar(self, username):
        """创建默认头像"""
        # 根据用户名选择默认头像
        if username:
            first_char = username[0].lower()
            if first_char in 'abcdef':
                default_avatar = os.path.join('..', '客户端', 'w.webp')
            else:
                default_avatar = os.path.join('..', '客户端', 'm.webp')
        else:
            default_avatar = os.path.join('..', '客户端', 'm.webp')
        
        # 尝试加载默认头像文件
        if os.path.exists(default_avatar):
            pixmap = QPixmap(default_avatar)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(65, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                return pixmap
        
        # 如果默认头像不存在，创建蓝色圆形头像
        pixmap = QPixmap(65, 65)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制圆形背景
        painter.setBrush(QBrush(QColor(24, 144, 255)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 65, 65)
        
        # 绘制首字母
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Microsoft YaHei UI", 26, QFont.Bold)
        painter.setFont(font)
        initial = username[0].upper() if username else "?"
        painter.drawText(pixmap.rect(), Qt.AlignCenter, initial)
        
        painter.end()
        return pixmap
    
    def load_users(self):
        """加载用户列表"""
        try:
            users = self.db.get_all_users()
            # 按ID从小到大排序
            users = sorted(users, key=lambda x: x.get('id', 0))
            self.user_table.setRowCount(len(users))
            
            for row, user in enumerate(users):
                # ID
                id_item = QTableWidgetItem(str(user['id']))
                id_item.setTextAlignment(Qt.AlignCenter)
                self.user_table.setItem(row, 0, id_item)
                
                # 头像
                avatar_item = QTableWidgetItem()
                avatar_item.setTextAlignment(Qt.AlignCenter)
                username = user.get('username', '')
                avatar_path = user.get('avatar', '')
                
                if avatar_path and os.path.exists(avatar_path):
                    pixmap = QPixmap(avatar_path)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(65, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        avatar_item.setIcon(QIcon(pixmap))
                        avatar_item.setSizeHint(QSize(65, 65))
                else:
                    default_avatar = self._create_default_avatar(username)
                    avatar_item.setIcon(QIcon(default_avatar))
                    avatar_item.setSizeHint(QSize(65, 65))
                
                self.user_table.setItem(row, 1, avatar_item)
                
                # 用户名
                username_item = QTableWidgetItem(username)
                username_item.setTextAlignment(Qt.AlignCenter)
                self.user_table.setItem(row, 2, username_item)
                
                # 密码（显示明文）
                password = user.get('password', '')
                password_item = QTableWidgetItem(password if password else '未设置')
                password_item.setTextAlignment(Qt.AlignCenter)
                password_item.setForeground(QColor(100, 100, 100))
                self.user_table.setItem(row, 3, password_item)
                
                # 状态
                status = user.get('status', 'offline')
                if status not in ['online', 'offline', 'banned']:
                    status = 'offline'
                
                status_text = {
                    'online': '在线',
                    'offline': '离线',
                    'banned': '禁言'
                }.get(status, '离线')
                
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignCenter)
                if status == 'online':
                    status_item.setForeground(QColor(82, 196, 26))  # 绿色
                elif status == 'banned':
                    status_item.setForeground(QColor(255, 77, 79))  # 红色
                else:
                    status_item.setForeground(QColor(140, 140, 140))  # 灰色
                self.user_table.setItem(row, 4, status_item)
                
                # 锁定状态
                is_locked = user.get('is_locked', 0)
                if is_locked == 1 or status == 'banned':
                    lock_text = "已锁定"
                    lock_color = QColor(255, 77, 79)  # 红色
                else:
                    lock_text = "正常"
                    lock_color = QColor(82, 196, 26)  # 绿色
                
                lock_item = QTableWidgetItem(lock_text)
                lock_item.setTextAlignment(Qt.AlignCenter)
                lock_item.setForeground(lock_color)
                self.user_table.setItem(row, 5, lock_item)
            
            self.statusBar().showMessage(f"已加载 {len(users)} 个用户", 3000)
            
        except Exception as e:
            logger.error(f"加载用户列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载用户列表失败: {e}")
    
    def change_user_status(self, status):
        """改变选中用户的状态"""
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择一个或多个用户！")
            return
        
        user_ids = []
        for row in selected_rows:
            user_id = int(self.user_table.item(row.row(), 0).text())
            user_ids.append(user_id)
        
        action = "锁定" if status == 'banned' else "解锁"
        reply = QMessageBox.question(
            self, 
            f"确认{action}", 
            f"确定要{action}{len(user_ids)}个用户吗？", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        success_count = 0
        for user_id in user_ids:
            if self.db.update_user(user_id, status=status):
                success_count += 1
        
        QMessageBox.information(
            self, 
            "操作完成", 
            f"成功{action}{success_count}个用户，失败{len(user_ids)-success_count}个用户"
        )
        
        self.load_users()
    
    def lock_user_account(self):
        """锁定用户账户（禁止登录）"""
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择一个或多个用户！")
            return
        
        user_ids = []
        for row in selected_rows:
            user_id = int(self.user_table.item(row.row(), 0).text())
            user_ids.append(user_id)
        
        reply = QMessageBox.question(
            self, 
            "确认锁定", 
            f"确定要锁定{len(user_ids)}个用户的账户吗？\n锁定后用户将无法登录。", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        success_count = 0
        for user_id in user_ids:
            if self.db.lock_user_by_id(user_id):
                success_count += 1
        
        QMessageBox.information(
            self, 
            "操作完成", 
            f"成功锁定{success_count}个用户账户，失败{len(user_ids)-success_count}个用户"
        )
        
        self.load_users()
    
    def unlock_user_account(self):
        """解锁用户账户（允许登录）"""
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择一个或多个用户！")
            return
        
        user_ids = []
        for row in selected_rows:
            user_id = int(self.user_table.item(row.row(), 0).text())
            user_ids.append(user_id)
        
        reply = QMessageBox.question(
            self, 
            "确认解锁", 
            f"确定要解锁{len(user_ids)}个用户的账户吗？\n解锁后用户可以正常登录。", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        success_count = 0
        for user_id in user_ids:
            if self.db.unlock_user_by_id(user_id):
                success_count += 1
        
        QMessageBox.information(
            self, 
            "操作完成", 
            f"成功解锁{success_count}个用户账户，失败{len(user_ids)-success_count}个用户"
        )
        
        self.load_users()
    
    def add_user(self):
        """添加用户"""
        dialog = AddUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            username, password, confirm, avatar = dialog.get_user_data()
            
            if username and password:
                if password != confirm:
                    QMessageBox.warning(self, "密码不一致", "两次输入的密码不一致，请重新输入！")
                    return
                
                # 调用数据库的add_user方法，传入头像参数
                success = self.db.add_user(username, password, avatar=avatar)
                if success.get('success'):
                    QMessageBox.information(self, "成功", f"用户 '{username}' 添加成功！")
                    self.load_users()
                else:
                    QMessageBox.warning(self, "失败", success.get('message', f"用户 '{username}' 已存在！"))
    
    def edit_user(self):
        """编辑用户"""
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择一个用户！")
            return
        
        row = selected_rows[0].row()
        user_id = int(self.user_table.item(row, 0).text())
        username = self.user_table.item(row, 2).text()
        
        user_info = self.db.get_user_by_id(user_id)
        if not user_info:
            QMessageBox.warning(self, "错误", f"用户 '{username}' 不存在！")
            return
        
        dialog = EditUserDialog(self, user_info)
        if dialog.exec_() == QDialog.Accepted:
            update_data = dialog.get_update_data()
            if update_data:
                if self.db.update_user(user_id, **update_data):
                    QMessageBox.information(self, "成功", f"用户 '{username}' 更新成功！")
                    self.load_users()
                else:
                    QMessageBox.warning(self, "失败", "更新用户失败！")
    
    def delete_user(self):
        """删除用户"""
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择一个用户！")
            return
        
        row = selected_rows[0].row()
        user_id = int(self.user_table.item(row, 0).text())
        username = self.user_table.item(row, 2).text()
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除用户 '{username}' 吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.delete_user(user_id):
                QMessageBox.information(self, "成功", f"用户 '{username}' 已删除")
                self.load_users()
            else:
                QMessageBox.warning(self, "失败", "删除用户失败！")


class AddUserDialog(QDialog):
    """添加用户对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.avatar_path = ''  # 保存头像路径
        self.setWindowTitle("添加用户")
        self.setFixedSize(380, 380)
        self.init_ui()
    
    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 13px;
                color: #333;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 6px 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # 用户名
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("请输入用户名（英文和数字）")
        form_layout.addRow("用户名*:", self.username_edit)
        
        # 头像区域
        avatar_group_box = QGroupBox("头像设置")
        avatar_group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                margin-top: 6px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        avatar_main_layout = QVBoxLayout(avatar_group_box)
        
        # 当前头像显示
        current_avatar_layout = QHBoxLayout()
        current_avatar_label = QLabel('当前头像:')
        current_avatar_label.setStyleSheet("font-weight: normal; color: #666;")
        current_avatar_layout.addWidget(current_avatar_label)
        
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(50, 50)
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
        male_avatar_btn.setFixedSize(40, 40)
        male_avatar_btn.setToolTip('男性头像')
        male_avatar_btn.clicked.connect(lambda: self._select_default_avatar('m.webp'))
        self._set_default_avatar_button(male_avatar_btn, 'm.webp')
        default_avatar_layout.addWidget(male_avatar_btn)
        
        female_avatar_btn = QPushButton()
        female_avatar_btn.setFixedSize(40, 40)
        female_avatar_btn.setToolTip('女性头像')
        female_avatar_btn.clicked.connect(lambda: self._select_default_avatar('w.webp'))
        self._set_default_avatar_button(female_avatar_btn, 'w.webp')
        default_avatar_layout.addWidget(female_avatar_btn)
        
        upload_btn = QPushButton("上传")
        upload_btn.clicked.connect(self.upload_avatar)
        default_avatar_layout.addWidget(upload_btn)
        default_avatar_layout.addStretch()
        avatar_main_layout.addLayout(default_avatar_layout)
        
        layout.addWidget(avatar_group_box)
        
        # 密码
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密码*:", self.password_edit)
        
        # 确认密码
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText("请确认密码")
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("确认密码*:", self.confirm_edit)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _update_avatar_display(self):
        """更新头像显示"""
        if self.avatar_path and os.path.exists(self.avatar_path):
            pixmap = QPixmap(self.avatar_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.avatar_label.setPixmap(pixmap)
                return
        
        # 默认显示👤图标
        self.avatar_label.setText("👤")
        self.avatar_label.setStyleSheet("font-size: 24px; border: 2px solid #D9D9D9; border-radius: 24px;")
        self.avatar_label.setAlignment(Qt.AlignCenter)
    
    def _set_default_avatar_button(self, button, avatar_file):
        """设置默认头像按钮"""
        try:
            # 检查客户端目录中的默认头像
            client_avatar_path = os.path.join('..', '客户端', avatar_file)
            if os.path.exists(client_avatar_path):
                pixmap = QPixmap(client_avatar_path)
                if not pixmap.isNull():
                    # 创建圆形头像
                    size = 36
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
                    
                    button.setIcon(QIcon(rounded_pixmap))
                    button.setIconSize(QSize(size, size))
                    button.setStyleSheet("border: 1px solid #D9D9D9; border-radius: 20px;")
                    return
        except Exception as e:
            logger.error(f"设置默认头像按钮失败: {e}")
        
        button.setText('👤' if avatar_file == 'm.webp' else '👩')
        button.setStyleSheet("font-size: 16px; border: 1px solid #D9D9D9; border-radius: 20px;")
    
    def _select_default_avatar(self, avatar_file):
        """选择默认头像"""
        # 检查客户端目录中的默认头像
        client_avatar_path = os.path.join('..', '客户端', avatar_file)
        if os.path.exists(client_avatar_path):
            self.avatar_path = client_avatar_path
            self._update_avatar_display()
        else:
            QMessageBox.information(self, '提示', f'默认头像文件 {avatar_file} 不存在')
    
    def upload_avatar(self):
        """上传头像"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择头像", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if file_path:
            self.avatar_path = file_path
            self._update_avatar_display()
    
    def get_user_data(self):
        """获取用户数据"""
        return (
            self.username_edit.text().strip(),
            self.password_edit.text(),
            self.confirm_edit.text(),
            self.avatar_path
        )
    
    def accept(self):
        """验证并接受"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()
        
        if not username:
            QMessageBox.warning(self, "错误", "请输入用户名！")
            return
        
        if not username.isalnum():
            QMessageBox.warning(self, "错误", "用户名只能包含英文和数字！")
            return
        
        if not password:
            QMessageBox.warning(self, "错误", "请输入密码！")
            return
        
        if password != confirm:
            QMessageBox.warning(self, "错误", "两次输入的密码不一致！")
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "错误", "密码长度至少6位！")
            return
        
        super().accept()


class EditUserDialog(QDialog):
    """编辑用户对话框"""
    
    def __init__(self, parent=None, user_info=None):
        super().__init__(parent)
        self.user_info = user_info or {}
        self.avatar_path = self.user_info.get('avatar', '')
        self.setWindowTitle(f"编辑用户 - {self.user_info.get('username', '')}")
        self.setFixedSize(350, 300)
        self.init_ui()
    
    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 13px;
                color: #333;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 6px 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # 用户名（只读）
        username_label = QLabel(self.user_info.get('username', ''))
        username_label.setStyleSheet("font-weight: bold;")
        form_layout.addRow("用户名:", username_label)
        
        # 头像
        avatar_layout = QHBoxLayout()
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(48, 48)
        self._update_avatar_display()
        avatar_layout.addWidget(self.avatar_label)
        
        upload_btn = QPushButton("上传头像")
        upload_btn.clicked.connect(self.upload_avatar)
        avatar_layout.addWidget(upload_btn)
        avatar_layout.addStretch()
        form_layout.addRow("头像:", avatar_layout)
        
        # 新密码
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("留空表示不修改密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("新密码:", self.password_edit)
        
        # 确认密码
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText("请确认新密码")
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("确认密码:", self.confirm_edit)
        
        # 显示密码复选框
        self.show_password_cb = QCheckBox("显示密码")
        self.show_password_cb.stateChanged.connect(self.toggle_password_visibility)
        form_layout.addRow("", self.show_password_cb)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _update_avatar_display(self):
        """更新头像显示"""
        if self.avatar_path and os.path.exists(self.avatar_path):
            pixmap = QPixmap(self.avatar_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.avatar_label.setPixmap(pixmap)
                return
        
        # 默认头像
        username = self.user_info.get('username', '?')
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(24, 144, 255)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 48, 48)
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Microsoft YaHei UI", 20, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, username[0].upper() if username else "?")
        painter.end()
        self.avatar_label.setPixmap(pixmap)
    
    def upload_avatar(self):
        """上传头像"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择头像", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.avatar_path = file_path
            self._update_avatar_display()
    
    def toggle_password_visibility(self, state):
        """切换密码可见性"""
        if state == Qt.Checked:
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.confirm_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.confirm_edit.setEchoMode(QLineEdit.Password)
    
    def get_update_data(self):
        """获取更新数据"""
        update_data = {}
        
        new_password = self.password_edit.text().strip()
        confirm_password = self.confirm_edit.text().strip()
        
        if new_password:
            if new_password != confirm_password:
                QMessageBox.warning(self, "错误", "两次输入的密码不一致！")
                return None
            if len(new_password) < 6:
                QMessageBox.warning(self, "错误", "密码长度至少6位！")
                return None
            update_data['password'] = new_password
        
        if self.avatar_path:
            update_data['avatar'] = self.avatar_path
        
        return update_data
    
    def accept(self):
        """验证并接受"""
        new_password = self.password_edit.text().strip()
        confirm_password = self.confirm_edit.text().strip()
        
        if new_password:
            if new_password != confirm_password:
                QMessageBox.warning(self, "错误", "两次输入的密码不一致！")
                return
            if len(new_password) < 6:
                QMessageBox.warning(self, "错误", "密码长度至少6位！")
                return
        
        super().accept()


# 测试代码
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    # 模拟数据库用于测试
    class MockDatabase:
        def __init__(self):
            self.users = [
                {'id': 1, 'username': 'admin', 'status': 'offline', 'is_locked': 0, 'avatar': ''},
                {'id': 2, 'username': 'user1', 'status': 'offline', 'is_locked': 0, 'avatar': ''},
                {'id': 3, 'username': 'user2', 'status': 'offline', 'is_locked': 0, 'avatar': ''},
                {'id': 4, 'username': 'test', 'status': 'offline', 'is_locked': 0, 'avatar': ''},
            ]
        
        def get_all_users(self):
            return self.users
        
        def get_user_by_id(self, user_id):
            for user in self.users:
                if user['id'] == user_id:
                    return user
            return None
        
        def create_user(self, username, password):
            new_user = {
                'id': len(self.users) + 1,
                'username': username,
                'status': 'offline',
                'is_locked': 0,
                'avatar': '',
                'last_login': None,
                'created_at': '2024-11-20 10:00:00'
            }
            self.users.append(new_user)
            return True
        
        def update_user(self, user_id, **kwargs):
            for user in self.users:
                if user['id'] == user_id:
                    for key, value in kwargs.items():
                        user[key] = value
                    return True
            return False
        
        def delete_user(self, user_id):
            for i, user in enumerate(self.users):
                if user['id'] == user_id:
                    self.users.pop(i)
                    return True
            return False
    
    app = QApplication(sys.argv)
    db = MockDatabase()
    window = UserManagerWindow(db)
    window.show()
    sys.exit(app.exec_())
