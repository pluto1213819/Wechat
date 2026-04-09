# client.py - 仿QQ即时通讯系统客户端主程序
import sys
import os

# 添加客户端目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from client_ui_new import LoginDialog, ChatMainWindow
from client_network import NetworkClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量，保存主窗口引用
main_window = None

def main():
    global main_window
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用样式
    app.setStyleSheet("""
        * {
            font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
        }
    """)
    
    # 显示登录对话框
    login_dialog = LoginDialog()
    
    def on_login_success(username, server_addr, token, client):
        """登录成功回调"""
        global main_window
        logger.info(f"✅ 用户 {username} 登录成功，打开主界面")
        
        # 创建并显示主窗口
        main_window = ChatMainWindow(username, server_addr, client)
        
        # 获取好友列表和离线消息等初始数据
        client.get_friends()
        client.get_friend_requests()
        client.get_groups()
        client.get_offline_messages()
        
        main_window.show()
        
        # 设置对话框结果为Accepted，然后关闭
        login_dialog.setResult(LoginDialog.Accepted)
        login_dialog.accept()
    
    # 连接信号
    login_dialog.login_success.connect(on_login_success)
    
    # 显示对话框
    result = login_dialog.exec_()
    
    if result == LoginDialog.Accepted:
        sys.exit(app.exec_())
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
