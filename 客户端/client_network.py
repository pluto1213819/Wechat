# client_network.py - 仿QQ即时通讯系统客户端网络模块
# 负责与服务器的所有网络通信

import socket
import struct
import json
import threading
import time
from datetime import datetime
import logging
import base64
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkClient:
    """客户端网络通信类"""
    
    def __init__(self, host='127.0.0.1', port=8000):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.authenticated = False
        self.username = None
        self.user_id = None
        self.session_token = None
        self.avatar = None  # 用户头像
        
        # 消息队列和回调
        self.message_queue = []
        self.callbacks = {}
        self.receive_thread = None
        self.running = False
        
        # 错误信息
        self.last_error = None
        
        # 加密相关
        self.encryption_key = None  # 用于加密的密钥
    
    def _encrypt(self, data):
        """加密数据"""
        if not self.encryption_key:
            return data
        
        # 简单的XOR加密，实际应用中应该使用更安全的加密算法
        encrypted = bytearray()
        for i, byte in enumerate(data):
            key_byte = ord(self.encryption_key[i % len(self.encryption_key)])
            encrypted.append(byte ^ key_byte)
        return bytes(encrypted)
    
    def _decrypt(self, data):
        """解密数据"""
        if not self.encryption_key:
            return data
        
        # 简单的XOR解密
        decrypted = bytearray()
        for i, byte in enumerate(data):
            key_byte = ord(self.encryption_key[i % len(self.encryption_key)])
            decrypted.append(byte ^ key_byte)
        return bytes(decrypted)
    
    def connect(self):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"✅ 连接服务器成功: {self.host}:{self.port}")
            return True
        except Exception as e:
            self.last_error = f"连接失败: {str(e)}"
            logger.error(f"❌ 连接失败: {e}")
            return False
    
    def login(self, username, password):
        """登录"""
        if not self.connected:
            self.last_error = "未连接到服务器"
            return False
        
        try:
            msg = {
                'type': 'auth',
                'username': username,
                'password': password
            }
            
            if not self.send_message(msg):
                self.last_error = "发送登录请求失败"
                return False
            
            # 直接接收响应（不使用消息队列）
            for _ in range(15):  # 最多等待4.5秒
                try:
                    raw_len = self._recvall(4)
                    if raw_len:
                        msg_len = struct.unpack('!I', raw_len)[0]
                        json_data = self._recvall(msg_len)
                        if json_data:
                            response = json.loads(json_data.decode('utf-8'))
                            if response.get('type') == 'auth_response':
                                if response.get('success'):
                                    self.authenticated = True
                                    self.username = username
                                    self.user_id = response.get('user_id')
                                    self.session_token = response.get('session_token')
                                    self.avatar = response.get('avatar', '')  # 保存头像信息
                                    logger.info(f"✅ 登录成功: {username} (ID: {self.user_id})")
                                    # 登录成功后启动接收线程
                                    self._start_receive_thread()
                                    return True
                                else:
                                    self.last_error = response.get('message', '登录失败')
                                    logger.error(f"❌ 登录失败: {self.last_error}")
                                    return False
                except Exception as e:
                    logger.error(f"接收登录响应异常: {e}")
                    break
                time.sleep(0.3)
            
            self.last_error = "登录超时"
            return False
            
        except Exception as e:
            self.last_error = f"登录异常: {str(e)}"
            logger.error(f"❌ 登录异常: {e}")
            return False
    
    def register(self, username, password, nickname='', security_question='', security_answer='', avatar=''):
        """注册新用户"""
        if not self.connected:
            return {'success': False, 'message': '未连接到服务器'}
        
        try:
            msg = {
                'type': 'register',
                'username': username,
                'password': password,
                'nickname': nickname,
                'security_question': security_question,
                'security_answer': security_answer,
                'avatar': avatar
            }
            
            if not self.send_message(msg):
                return {'success': False, 'message': '发送注册请求失败'}
            
            logger.info("注册请求已发送，等待响应...")
            
            # 设置接收超时
            self.socket.settimeout(10)
            
            try:
                # 接收数据长度
                raw_len = self.socket.recv(4)
                if not raw_len or len(raw_len) < 4:
                    logger.error(f"接收长度失败: raw_len={raw_len}")
                    return {'success': False, 'message': '接收数据长度失败'}
                
                msg_len = struct.unpack('!I', raw_len)[0]
                logger.info(f"接收到消息长度: {msg_len}")
                
                # 接收消息内容
                json_data = b''
                while len(json_data) < msg_len:
                    chunk = self.socket.recv(msg_len - len(json_data))
                    if not chunk:
                        logger.error(f"接收数据中断: 已接收 {len(json_data)}/{msg_len}")
                        return {'success': False, 'message': '接收数据中断'}
                    json_data += chunk
                
                logger.info(f"接收到完整数据: {len(json_data)} 字节")
                
                response = json.loads(json_data.decode('utf-8'))
                logger.info(f"解析响应: {response}")
                
                if response.get('type') == 'register_response':
                    return {
                        'success': response.get('success', False),
                        'message': response.get('message', '')
                    }
                else:
                    return {'success': False, 'message': f"收到非注册响应: {response.get('type')}"}
                    
            except socket.timeout:
                logger.error("接收响应超时")
                return {'success': False, 'message': '注册超时，服务器未响应'}
            except Exception as e:
                logger.error(f"接收响应异常: {e}")
                return {'success': False, 'message': f'接收响应异常: {str(e)}'}
            finally:
                # 恢复阻塞模式
                self.socket.settimeout(None)
            
        except Exception as e:
            logger.error(f"注册异常: {e}")
            return {'success': False, 'message': f'注册异常: {str(e)}'}
    
    def _recvall(self, n):
        """接收指定字节数的数据"""
        if not self.socket:
            return None
        data = b''
        while len(data) < n:
            try:
                packet = self.socket.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            except socket.timeout:
                return None
            except Exception as e:
                logger.error(f"接收数据异常: {e}")
                return None
        return data
    
    def reset_password(self, username, answer, new_password):
        """重置密码"""
        if not self.connected:
            return {'success': False, 'message': '未连接到服务器'}
        
        try:
            msg = {
                'type': 'reset_password',
                'username': username,
                'security_answer': answer,
                'new_password': new_password
            }
            
            if not self.send_message(msg):
                return {'success': False, 'message': '发送请求失败'}
            
            for _ in range(5):
                for i, msg in enumerate(self.message_queue):
                    if msg.get('type') == 'reset_password_response':
                        del self.message_queue[i]
                        return {
                            'success': msg.get('success', False),
                            'message': msg.get('message', '')
                        }
                time.sleep(0.3)
            
            return {'success': False, 'message': '操作超时'}
            
        except Exception as e:
            return {'success': False, 'message': f'异常: {str(e)}'}
    
    def send_chat(self, target_username, content):
        """发送私聊消息"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'chat',
            'to': target_username,
            'content': content
        }
        return self.send_message(msg)
    
    def send_group_chat(self, group_id, content):
        """发送群聊消息"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'group_chat',
            'group_id': group_id,
            'content': content
        }
        return self.send_message(msg)
    
    def search_user(self, keyword, search_type='nickname'):
        """搜索用户"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'search_user',
            'keyword': keyword,
            'search_type': search_type
        }
        return self.send_message(msg)
    
    def add_friend(self, target_username):
        """发送好友请求"""
        if not self.authenticated:
            logger.warning("⚠️ 未认证，无法发送好友请求")
            return False
        
        msg = {
            'type': 'add_friend',
            'target_username': target_username
        }
        
        logger.info(f"📤 发送好友请求: {target_username}")
        
        if not self.send_message(msg):
            logger.error("❌ 发送好友请求消息失败")
            return False
        
        # 等待响应
        for _ in range(10):
            for i, msg in enumerate(self.message_queue):
                if msg.get('type') == 'friend_request_sent':
                    del self.message_queue[i]
                    success = msg.get('success', False)
                    error = msg.get('error', '')
                    if success:
                        logger.info(f"✅ 好友请求发送成功: -> {target_username}")
                    else:
                        logger.warning(f"⚠️ 好友请求发送失败: {error}")
                    return success
            time.sleep(0.3)
        
        logger.warning("⚠️ 好友请求响应超时")
        return False
    
    def accept_friend_request(self, from_username):
        """接受好友请求"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'accept_friend',
            'from_username': from_username
        }
        return self.send_message(msg)
    
    def reject_friend_request(self, from_username):
        """拒绝好友请求"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'reject_friend',
            'from_username': from_username
        }
        return self.send_message(msg)
    
    def get_friends(self):
        """获取好友列表"""
        if not self.authenticated:
            return False
        
        msg = {'type': 'get_friends'}
        return self.send_message(msg)
    
    def get_friend_requests(self):
        """获取好友请求列表"""
        if not self.authenticated:
            return False
        
        msg = {'type': 'get_friend_requests'}
        return self.send_message(msg)
    
    def create_group(self, name, description=''):
        """创建群组"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'create_group',
            'name': name,
            'description': description
        }
        return self.send_message(msg)
    
    def join_group(self, group_id):
        """加入群组"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'join_group',
            'group_id': group_id
        }
        return self.send_message(msg)
    
    def leave_group(self, group_id):
        """离开群组"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'leave_group',
            'group_id': group_id
        }
        return self.send_message(msg)
    
    def get_groups(self):
        """获取用户的群组列表"""
        if not self.authenticated:
            return False
        
        msg = {'type': 'get_groups'}
        return self.send_message(msg)
    
    def get_offline_messages(self):
        """获取离线消息"""
        if not self.authenticated:
            return False
        
        msg = {'type': 'get_offline_messages'}
        return self.send_message(msg)
    
    def send_file_request(self, target_username, file_name, file_size):
        """发送文件传输请求"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'file_transfer_request',
            'target_username': target_username,
            'file_name': file_name,
            'file_size': file_size
        }
        return self.send_message(msg)
    
    def send_file_response(self, from_username, accepted):
        """发送文件传输响应"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'file_transfer_response',
            'from_username': from_username,
            'accepted': accepted
        }
        return self.send_message(msg)
    
    def send_file_data(self, target_username, file_name, file_data):
        """发送文件数据"""
        if not self.authenticated:
            return False
        
        # 将二进制文件数据编码为base64字符串
        file_data_base64 = base64.b64encode(file_data).decode('utf-8')
        
        msg = {
            'type': 'file_data',
            'target_username': target_username,
            'file_name': file_name,
            'data': file_data_base64
        }
        return self.send_message(msg)
    
    def update_profile(self, **kwargs):
        """更新个人资料"""
        if not self.authenticated:
            return False
        
        msg = {
            'type': 'update_profile',
            **kwargs
        }
        return self.send_message(msg)
    
    def logout(self):
        """注销"""
        if self.authenticated and self.connected:
            msg = {'type': 'logout'}
            self.send_message_direct(msg)
            self.authenticated = False
            logger.info(f"👋 用户 {self.username} 已注销")
    
    def send_heartbeat(self):
        """发送心跳包"""
        if self.authenticated and self.connected:
            msg = {'type': 'heartbeat'}
            return self.send_message_direct(msg)
        return False
    
    def send_message(self, message):
        """发送消息并等待确认（用于需要响应的操作）"""
        if not self.connected:
            return False
        
        return self.send_message_direct(message)
    
    def send_message_direct(self, message):
        """直接发送消息（不等待响应）"""
        if not self.connected or not self.socket:
            return False
        
        try:
            msg_json = json.dumps(message, ensure_ascii=False).encode('utf-8')
            
            # 加密消息
            if self.encryption_key:
                msg_json = self._encrypt(msg_json)
            
            msg_len = struct.pack('!I', len(msg_json))
            self.socket.sendall(msg_len + msg_json)
            return True
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            logger.error(f"❌ 发送消息失败: {e}")
            self.connected = False
            return False
    
    def register_callback(self, message_type, callback):
        """注册消息回调函数"""
        self.callbacks[message_type] = callback
    
    def _start_receive_thread(self):
        """启动接收线程"""
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
    
    def _receive_loop(self):
        """接收消息循环"""
        while self.running and self.connected:
            try:
                raw_len = self._recvall(4)
                if not raw_len:
                    break
                
                msg_len = struct.unpack('!I', raw_len)[0]
                json_data = self._recvall(msg_len)
                
                if json_data:
                    # 解密消息
                    if self.encryption_key:
                        json_data = self._decrypt(json_data)
                    
                    message = json.loads(json_data.decode('utf-8'))
                    
                    # 添加到消息队列
                    self.message_queue.append(message)
                    
                    # 调用对应的回调函数
                    msg_type = message.get('type')
                    callback = self.callbacks.get(msg_type)
                    if callback:
                        try:
                            callback(message)
                        except Exception as e:
                            logger.error(f"回调执行错误 ({msg_type}): {e}")
                            
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                logger.error(f"❌ 连接断开: {e}")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"❌ 接收消息错误: {e}")
                break
        
        self.running = False
    
    def _recvall(self, n):
        """确保接收到n个字节"""
        data = b''
        while len(data) < n:
            try:
                packet = self.socket.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            except socket.timeout:
                continue
            except (ConnectionResetError, OSError):
                return None
        return data
    
    def close(self):
        """关闭连接"""
        self.running = False
        self.authenticated = False
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        logger.info("🔒 连接已关闭")
