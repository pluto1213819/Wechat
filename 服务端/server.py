# server.py
import sys
import os
import json
import logging
import ctypes

# 设置Windows任务栏图标
if sys.platform == "win32":
    myappid = '北华航天工业学院.Nova chatting.服务端.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# 设置应用程序路径
def set_application_path():
    """设置应用程序路径"""
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    sys.path.insert(0, application_path)
    os.chdir(application_path)
    return application_path

# 检查配置文件
def check_config_file():
    """检查配置文件是否存在，如果不存在则创建默认配置"""
    config_path = 'config.json'
    if not os.path.exists(config_path):
        try:
            default_config = {
                "server": {
                    "host": "127.0.0.1",
                    "port": 8000,
                    "max_connections": 100,
                    "timeout": 30,
                    "heartbeat_interval": 60
                },
                "database": {
                    "path": "im_database.db"
                },
                "logging": {
                    "level": "INFO",
                    "log_file": "server.log"
                }
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            print(f"[系统] 已创建默认配置文件: {config_path}")
            return True
            
        except Exception as e:
            print(f"[错误] 创建配置文件失败: {e}")
            return False
    return True

# 检查依赖库
def check_dependencies():
    """检查必要的依赖库是否已安装"""
    required_packages = ['PyQt5', 'bcrypt']
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"[错误] 缺少必要的依赖库: {', '.join(missing_packages)}")
        print("请使用以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

# 创建必要的目录
def create_necessary_directories():
    """创建必要的目录"""
    directories = ['avatars', 'backups', 'logs']
    
    for directory in directories:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print(f"[系统] 创建目录: {directory}/")
            except Exception as e:
                print(f"[警告] 创建目录 {directory} 失败: {e}")

# 设置日志系统
def setup_logging():
    """设置日志系统"""
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            log_config = config.get('logging', {})
            log_file = log_config.get('log_file', 'server.log')
            log_level = log_config.get('level', 'INFO')
        else:
            log_file = 'server.log'
            log_level = 'INFO'
        
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        level = level_map.get(log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        print(f"[系统] 日志系统已初始化，日志级别: {log_level}")
        return True
        
    except Exception as e:
        print(f"[错误] 日志系统初始化失败: {e}")
        return False

# 检查端口是否被占用
def check_port_available(host='0.0.0.0', port=8000):
    """检查端口是否可用"""
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"[警告] 端口 {port} 已被占用")
            return False
        
        return True
        
    except Exception as e:
        print(f"[错误] 检查端口失败: {e}")
        return False

# 主函数
def main():
    """主函数"""
    print("=" * 50)
    print("Nova chatting - 服务端")
    print("版本: 1.0.0")
    print("作者: 北华航天工业学院 网络工程")
    print("=" * 50)
    
    # 1. 设置应用程序路径
    app_path = set_application_path()
    print(f"[系统] 应用程序路径: {app_path}")
    
    # 2. 检查配置文件
    if not check_config_file():
        print("[错误] 配置文件检查失败，程序无法启动！")
        return 1
    
    # 3. 检查依赖库
    if not check_dependencies():
        print("[错误] 缺少必要的依赖库，请检查安装！")
        return 1
    
    # 4. 创建必要目录
    create_necessary_directories()
    
    # 5. 设置日志
    if not setup_logging():
        print("[警告] 日志系统初始化失败，但程序将继续运行")
    
    # 6. 加载配置检查端口
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        server_config = config.get('server', {})
        host = server_config.get('host', '127.0.0.1')
        port = server_config.get('port', 8000)
        
        if not check_port_available(host, port):
            print(f"[警告] 端口 {port} 可能已被占用，是否继续启动？")
            print("[提示] 输入 'y' 继续，输入 'n' 退出")
            reply = input().strip().lower()
            if reply != 'y':
                return 1
                
    except Exception as e:
        logging.error(f"加载配置失败: {e}")
    
    # 7. 初始化Qt应用程序
    print("[系统] 正在初始化Qt应用程序...")
    
    # 导入Qt相关模块（必须在创建QApplication之前！）
    from PyQt5.QtWidgets import QApplication, QStyleFactory, QMessageBox
    from PyQt5.QtGui import QFont, QIcon
    from PyQt5.QtCore import Qt, QCoreApplication
    
    # 设置高DPI支持（必须在创建QApplication之前！）
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序元数据
    app.setApplicationName("Nova chatting - 服务端")
    app.setOrganizationName("北华航天工业学院")
    app.setOrganizationDomain("nciae.edu.cn")
    app.setApplicationVersion("1.0.0")
    
    # 设置应用程序样式
    app.setStyle(QStyleFactory.create('Fusion'))
    
    # 设置全局字体
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
    
    # 8. 创建主窗口
    print("[系统] 正在创建主窗口...")
    
    # 直接导入ServerMainWindow，确保在创建QApplication之后导入
    from server_ui import ServerMainWindow
    try:
        window = ServerMainWindow()
        print("[系统] 主窗口创建成功")
    except Exception as e:
        logging.error(f"创建主窗口失败: {e}")
        QMessageBox.critical(None, "错误", f"创建主窗口失败: {str(e)}")
        return 1
    
    # 9. 显示主窗口
    window.show()
    print("[系统] 主窗口已显示")
    
    # 10. 启动消息循环
    print("[系统] 应用程序启动完成")
    print("=" * 50)
    
    return_code = app.exec_()
    
    print("[系统] 应用程序已退出")
    return return_code

# 程序入口
if __name__ == '__main__':
    # 设置控制台编码
    if sys.platform == "win32":
        import locale
        if locale.getpreferredencoding().upper() != "UTF-8":
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    # 运行主函数
    exit_code = main()
    
    # 清理资源
    import gc
    gc.collect()
    
    # 退出程序
    sys.exit(exit_code)