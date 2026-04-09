# network_server.py - 仿QQ即时通讯系统服务端网络模块
import socket
import threading
import json
import time
import struct
from datetime import datetime
import logging
import os
import hashlib
import base64

# 导入数据库模块（在同一文件中定义）
# UserDatabase 类定义在 database.py 中，但为了简化，我们在这里直接引用

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientThread(threading.Thread):
    """处理单个客户端连接和通信的线程"""
    
    def __init__(self, client_socket, client_address, server_instance, db):
        super().__init__(daemon=True)
        self.client_socket = client_socket
        self.client_address = client_address
        self.server = server_instance
        self.db = db
        self.username = None
        self.user_id = None
        self.session_token = None
        self.running = True
        self.client_socket.settimeout(15.0)  # 15秒超时
        self.ip, self.port = client_address
        self.last_heartbeat = datetime.now()
        
    def run(self):
        """客户端连接处理主循环"""
        try:
            while self.running:
                auth_data = self._receive_message()
                if not auth_data:
                    break
                    
                msg_type = auth_data.get('type')
                
                if msg_type == 'auth':
                    if not self._handle_auth(auth_data):
                        break
                    # 主消息循环
                    self._message_loop()
                elif msg_type == 'register':
                    self._handle_register(auth_data)
                elif msg_type == 'reset_password':
                    self._handle_reset_password(auth_data)
                else:
                    logger.warning(f"未认证的消息类型: {msg_type}")
                    
        except socket.timeout:
            if self.username:
                logger.info(f"[心跳超时] 用户 {self.username} 连接超时")
            else:
                logger.info(f"[连接超时] 客户端 {self.ip}:{self.port} 连接超时")
        except (ConnectionResetError, json.JSONDecodeError) as e:
            logger.error(f"[网络异常] 客户端 {self.ip}:{self.port}: {e}")
        except Exception as e:
            logger.error(f"[错误] 客户端处理异常: {e}")
        finally:
            self._cleanup()
    
    def _message_loop(self):
        """主消息循环"""
        while self.running:
            try:
                msg_data = self._receive_message()
                if not msg_data:
                    break
                
                msg_type = msg_data.get('type')
                
                # 消息路由
                handlers = {
                    'chat': self._handle_chat_message,
                    'group_chat': self._handle_group_chat,
                    'request_user_list': self._handle_user_list_request,
                    'search_user': self._handle_search_user,
                    'add_friend': self._handle_add_friend,
                    'get_friends': self._handle_get_friends,
                    'accept_friend': self._handle_accept_friend,
                    'reject_friend': self._handle_reject_friend,
                    'get_friend_requests': self._handle_get_friend_requests,
                    'heartbeat': self._handle_heartbeat,
                    'logout': self._handle_logout,
                    'create_group': self._handle_create_group,
                    'join_group': self._handle_join_group,
                    'leave_group': self._handle_leave_group,
                    'get_groups': self._handle_get_groups,
                    'get_group_members': self._handle_get_group_members,
                    'get_chat_history': self._handle_get_chat_history,
                    'update_profile': self._handle_update_profile,
                    'file_transfer_request': self._handle_file_transfer_request,
                    'file_transfer_response': self._handle_file_transfer_response,
                    'file_data': self._handle_file_data,
                    'get_offline_messages': self._handle_get_offline_messages,
                }
                
                handler = handlers.get(msg_type)
                if handler:
                    handler(msg_data)
                else:
                    logger.warning(f"未知消息类型: {msg_type}")
                
            except socket.timeout:
                # 检查心跳超时
                if (datetime.now() - self.last_heartbeat).seconds > 90:
                    logger.info(f"用户 {self.username} 心跳超时，断开连接")
                    break
                continue
            except Exception as e:
                logger.error(f"消息处理异常: {e}")
                break
    
    def _handle_auth(self, msg_data):
        """处理认证请求"""
        username = msg_data.get('username', '').strip()
        password = msg_data.get('password', '').strip()
        
        if not username or not password:
            self._send_message({
                'type': 'auth_response',
                'success': False,
                'message': '用户名和密码不能为空'
            })
            return False
        
        result = self.db.authenticate_user(username, password)
        
        if result['success']:
            user = result['user']
            self.username = username
            self.user_id = user['id']
            
            # 先通知同名用户下线（单设备登录）
            self._kick_existing_user(username)
            
            # 创建新会话
            self.session_token = self.db.create_session(
                user['id'], 
                self.ip, 
                f"{self.ip}:{self.port}"
            )
            
            # 发送认证成功响应
            self._send_message({
                'type': 'auth_response',
                'success': True,
                'username': username,
                'user_id': user['id'],
                'nickname': user.get('nickname', ''),
                'session_token': self.session_token,
                'avatar': user.get('avatar', '')
            })
            
            # 记录日志
            self._log_message(f"[登录] 用户 '{username}' ({self.ip}) 登录成功")
            
            # 注册客户端到服务器
            if hasattr(self.server, 'client_authenticated'):
                self.server.client_authenticated(self.username, self, self.ip)
            
            # 更新用户在线状态
            self.db.update_user(user['id'], status='online')
            
            return True
        else:
            self._send_message({
                'type': 'auth_response',
                'success': False,
                'message': result['message']
            })
            return False
    
    def _kick_existing_user(self, username: str):
        """踢出已登录的同名用户"""
        with self.server.lock:
            if username in self.server.clients:
                old_client = self.server.clients[username]
                try:
                    old_client._send_message({
                        'type': 'kicked',
                        'message': '您的账号在其他地方登录，已被强制下线'
                    })
                    old_client.running = False
                    logger.info(f"[踢出] 用户 {username} 旧设备被踢出")
                except Exception as e:
                    logger.error(f"踢出旧设备失败: {e}")
    
    def _get_existing_session(self, user_id: int) -> str:
        """获取用户的现有会话token"""
        conn = sqlite3.connect(self.server.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT session_token FROM sessions WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def _handle_register(self, msg_data):
        """处理注册请求"""
        username = msg_data.get('username', '').strip()
        password = msg_data.get('password', '')
        nickname = msg_data.get('nickname', '').strip()
        security_question = msg_data.get('security_question', '').strip()
        security_answer = msg_data.get('security_answer', '')
        avatar = msg_data.get('avatar', '')
        
        if not username or not password:
            self._send_message({
                'type': 'register_response',
                'success': False,
                'message': '用户名和密码不能为空'
            })
            return
        
        if len(username) < 3 or len(username) > 20:
            self._send_message({
                'type': 'register_response',
                'success': False,
                'message': '用户名长度必须在3-20个字符之间'
            })
            return
        
        if len(password) < 6:
            self._send_message({
                'type': 'register_response',
                'success': False,
                'message': '密码长度至少6个字符'
            })
            return
        
        result = self.db.add_user(username, password, nickname, security_question, security_answer, avatar)
        
        self._send_message({
            'type': 'register_response',
            'success': result['success'],
            'message': result['message']
        })
    
    def _handle_reset_password(self, msg_data):
        """处理密码重置"""
        username = msg_data.get('username', '').strip()
        answer = msg_data.get('security_answer', '')
        new_password = msg_data.get('new_password', '')
        
        if not all([username, answer, new_password]):
            self._send_message({
                'type': 'reset_password_response',
                'success': False,
                'message': '请填写完整信息'
            })
            return
        
        # 验证安全问题答案
        if self.db.verify_security_answer(username, answer):
            if self.db.reset_password(username, new_password):
                self._send_message({
                    'type': 'reset_password_response',
                    'success': True,
                    'message': '密码重置成功'
                })
            else:
                self._send_message({
                    'type': 'reset_password_response',
                    'success': False,
                    'message': '密码重置失败'
                })
        else:
            self._send_message({
                'type': 'reset_password_response',
                'success': False,
                'message': '安全问题答案错误'
            })
    
    def _handle_heartbeat(self, msg_data):
        """处理心跳包"""
        self.last_heartbeat = datetime.now()
        
        # 更新用户在线状态
        if self.user_id:
            self.db.update_user(self.user_id, status='online')
        
        self._send_message({'type': 'heartbeat_ack'})
    
    def _handle_logout(self, msg_data=None):
        """处理注销请求"""
        self._log_message(f"[注销] 用户 '{self.username}' 注销退出")
        
        # 更新离线状态
        if self.user_id:
            self.db.update_user(self.user_id, status='offline')
        
        # 清除会话
        if self.session_token:
            self.db.clear_user_sessions(self.user_id)
        
        # 从服务器移除
        if hasattr(self.server, 'client_disconnected'):
            self.server.client_disconnected(self.username)
        
        self.running = False
    
    def _handle_chat_message(self, msg_data):
        """处理私聊消息"""
        content = msg_data.get('content', '')
        target_username = msg_data.get('to', 'all')
        
        if not content.strip():
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 保存消息到数据库
        target_user = self.db.get_user_by_username(target_username)
        if target_user and self.user_id:
            self.db.save_message(
                sender_id=self.user_id,
                receiver_id=target_user['id'],
                content=content,
                message_type='text'
            )
        
        # 如果目标用户在线，发送消息
        with self.server.lock:
            if target_username in self.server.clients:
                target_client = self.server.clients[target_username]
                target_client._send_message({
                    'type': 'chat',
                    'from': self.username,
                    'to': target_username,
                    'content': content,
                    'timestamp': timestamp
                })
            elif target_user:
                # 目标用户不在线，保存为离线消息
                self.db.save_offline_message(
                    receiver_id=target_user['id'],
                    sender_id=self.user_id,
                    content=content,
                    message_type='text'
                )
        
        # 发送确认给发送者
        self._send_message({
            'type': 'chat_sent',
            'to': target_username,
            'timestamp': timestamp
        })
    
    def _handle_group_chat(self, msg_data):
        """处理群聊消息"""
        group_id = msg_data.get('group_id')
        content = msg_data.get('content', '')
        
        if not group_id or not content.strip():
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 保存消息
        if self.user_id:
            self.db.save_message(
                sender_id=self.user_id,
                group_id=group_id,
                content=content,
                message_type='text'
            )
        
        # 获取群成员并发送消息
        members = self.db.get_group_members(group_id)
        message = {
            'type': 'group_chat',
            'from': self.username,
            'group_id': group_id,
            'content': content,
            'timestamp': timestamp
        }
        
        with self.server.lock:
            for member in members:
                member_username = member['username']
                if member_username in self.server.clients and member_username != self.username:
                    self.server.clients[member_username]._send_message(message)
                elif member['id'] != self.user_id:
                    # 成员不在线，保存离线消息
                    self.db.save_offline_message(
                        receiver_id=member['id'],
                        group_id=group_id,
                        content=content,
                        message_type='text'
                    )
    
    def _handle_search_user(self, msg_data):
        """处理搜索用户"""
        keyword = msg_data.get('keyword', '').strip()
        search_type = msg_data.get('search_type', 'nickname')
        
        if not keyword:
            self._send_message({
                'type': 'search_result',
                'users': [],
                'success': True
            })
            return
        
        users = self.db.search_users(keyword, search_type, self.user_id)
        
        self._send_message({
            'type': 'search_result',
            'users': users,
            'success': True
        })
    
    def _handle_add_friend(self, msg_data):
        """处理添加好友请求"""
        target_username = msg_data.get('target_username', '').strip()
        
        logger.info(f"[添加好友] 收到请求: from={self.username}, to={target_username}")
        
        if not target_username or not self.username:
            logger.warning(f"[添加好友] 参数无效: target={target_username}, self={self.username}")
            self._send_message({
                'type': 'friend_request_sent',
                'success': False,
                'error': '参数无效'
            })
            return
        
        result = self.db.send_friend_request(self.username, target_username)
        logger.info(f"[添加好友] 数据库操作结果: {result}")
        
        if result:
            self._send_message({
                'type': 'friend_request_sent',
                'target_username': target_username,
                'success': True
            })
            
            # 通知接收者
            with self.server.lock:
                if target_username in self.server.clients:
                    target_client = self.server.clients[target_username]
                    user_info = self.db.get_user_by_username(self.username)
                    target_client._send_message({
                        'type': 'friend_request_received',
                        'from_username': self.username,
                        'from_nickname': user_info.get('nickname', self.username)
                    })
        else:
            self._send_message({
                'type': 'friend_request_sent',
                'success': False,
                'error': '好友请求发送失败，可能已存在好友关系或请求'
            })
    
    def _handle_get_friends(self, msg_data=None):
        """处理获取好友列表"""
        friends = self.db.get_friends(self.username)
        
        # 更新好友在线状态
        online_friends = []
        with self.server.lock:
            for friend in friends:
                is_online = friend['username'] in self.server.clients
                friend['status'] = 'online' if is_online else 'offline'
                online_friends.append(friend)
        
        self._send_message({
            'type': 'friends_list',
            'friends': online_friends,
            'success': True
        })
    
    def _handle_accept_friend(self, msg_data):
        """处理接受好友请求"""
        from_username = msg_data.get('from_username')
        
        if from_username and self.db.accept_friend_request(from_username, self.username):
            self._send_message({
                'type': 'friend_request_accepted',
                'from_username': from_username,
                'success': True
            })
            
            # 通知对方
            with self.server.lock:
                if from_username in self.server.clients:
                    self.server.clients[from_username]._send_message({
                        'type': 'friend_request_accepted',
                        'from_username': self.username,
                        'success': True
                    })
        else:
            self._send_message({
                'type': 'friend_request_accepted',
                'from_username': from_username,
                'success': False,
                'error': '接受好友请求失败'
            })
    
    def _handle_reject_friend(self, msg_data):
        """处理拒绝好友请求"""
        from_username = msg_data.get('from_username')
        
        if from_username and self.db.reject_friend_request(from_username, self.username):
            self._send_message({
                'type': 'friend_request_rejected',
                'from_username': from_username,
                'success': True
            })
        else:
            self._send_message({
                'type': 'friend_request_rejected',
                'from_username': from_username,
                'success': False
            })
    
    def _handle_get_friend_requests(self, msg_data=None):
        """处理获取好友申请列表"""
        requests = self.db.get_pending_friend_requests(self.username)
        self._send_message({
            'type': 'friend_requests_list',
            'requests': requests,
            'success': True
        })
    
    def _handle_create_group(self, msg_data):
        """处理创建群组"""
        name = msg_data.get('name', '').strip()
        description = msg_data.get('description', '').strip()
        
        if not name:
            self._send_message({
                'type': 'create_group_response',
                'success': False,
                'error': '群组名称不能为空'
            })
            return
        
        if self.user_id:
            group_id = self.db.create_group(name, self.user_id, description)
            if group_id:
                self._send_message({
                    'type': 'create_group_response',
                    'success': True,
                    'group_id': group_id,
                    'message': f'群组 "{name}" 创建成功'
                })
            else:
                self._send_message({
                    'type': 'create_group_response',
                    'success': False,
                    'error': '创建群组失败'
                })
    
    def _handle_join_group(self, msg_data):
        """处理加入群组"""
        group_id = msg_data.get('group_id')
        
        if group_id and self.user_id:
            if self.db.add_group_member(group_id, self.user_id):
                self._send_message({
                    'type': 'join_group_response',
                    'success': True,
                    'group_id': group_id,
                    'message': '加入群组成功'
                })
            else:
                self._send_message({
                    'type': 'join_group_response',
                    'success': False,
                    'error': '加入群组失败'
                })
    
    def _handle_leave_group(self, msg_data):
        """处理离开群组"""
        group_id = msg_data.get('group_id')
        
        if group_id and self.user_id:
            if self.db.remove_group_member(group_id, self.user_id):
                self._send_message({
                    'type': 'leave_group_response',
                    'success': True,
                    'message': '已退出群组'
                })
            else:
                self._send_message({
                    'type': 'leave_group_response',
                    'success': False,
                    'error': '退出群组失败'
                })
    
    def _handle_get_groups(self, msg_data=None):
        """处理获取用户的群组列表"""
        if self.user_id:
            groups = self.db.get_user_groups(self.user_id)
            self._send_message({
                'type': 'groups_list',
                'groups': groups,
                'success': True
            })
    
    def _handle_get_group_members(self, msg_data):
        """处理获取群成员列表"""
        group_id = msg_data.get('group_id')
        
        if group_id:
            members = self.db.get_group_members(group_id)
            # 更新在线状态
            with self.server.lock:
                for member in members:
                    member['is_online'] = member['username'] in self.server.clients
            
            self._send_message({
                'type': 'group_members_list',
                'group_id': group_id,
                'members': members,
                'success': True
            })
    
    def _handle_get_chat_history(self, msg_data):
        """处理获取聊天历史"""
        target_username = msg_data.get('target_username')
        limit = msg_data.get('limit', 50)
        
        if target_username and self.user_id:
            target_user = self.db.get_user_by_username(target_username)
            if target_user:
                messages = self.db.get_chat_history(self.user_id, target_user['id'], limit)
                self._send_message({
                    'type': 'chat_history',
                    'messages': messages,
                    'target_username': target_username,
                    'success': True
                })
    
    def _handle_update_profile(self, msg_data):
        """处理更新个人资料"""
        updates = {}
        
        if 'nickname' in msg_data:
            updates['nickname'] = msg_data['nickname'].strip()
        if 'signature' in msg_data:
            updates['signature'] = msg_data['signature'].strip()
        if 'password' in msg_data:
            new_password = msg_data['password']
            if len(new_password) >= 6:
                updates['password'] = new_password
        if 'security_question' in msg_data:
            updates['security_question'] = msg_data['security_question']
        if 'security_answer' in msg_data:
            updates['security_answer'] = msg_data['security_answer']
        if 'avatar' in msg_data:
            updates['avatar'] = msg_data['avatar']
        
        if updates and self.user_id:
            success = self.db.update_user(self.user_id, **updates)
            self._send_message({
                'type': 'profile_updated',
                'success': success,
                'message': '个人资料更新成功' if success else '更新失败'
            })
            
            # 通知用户管理界面刷新
            if success and hasattr(self.server, 'user_manager_window'):
                try:
                    if self.server.user_manager_window and self.server.user_manager_window.isVisible():
                        self.server.user_manager_window.load_users()
                except Exception as e:
                    logger.error(f"刷新用户管理界面失败: {e}")
    
    def _handle_file_transfer_request(self, msg_data):
        """处理文件传输请求"""
        target_username = msg_data.get('target_username')
        file_name = msg_data.get('file_name')
        file_size = msg_data.get('file_size', 0)
        
        if all([target_username, file_name, self.user_id]):
            # 转发请求给目标用户
            with self.server.lock:
                if target_username in self.server.clients:
                    self.server.clients[target_username]._send_message({
                        'type': 'file_transfer_request',
                        'from_username': self.username,
                        'file_name': file_name,
                        'file_size': file_size
                    })
                    self._send_message({
                        'type': 'file_transfer_request_sent',
                        'success': True
                    })
                else:
                    self._send_message({
                        'type': 'file_transfer_request_sent',
                        'success': False,
                        'error': '目标用户不在线'
                    })
    
    def _handle_file_transfer_response(self, msg_data):
        """处理文件传输响应"""
        from_username = msg_data.get('from_username')
        accepted = msg_data.get('accepted', False)
        
        with self.server.lock:
            if from_username in self.server.clients:
                self.server.clients[from_username]._send_message({
                    'type': 'file_transfer_response',
                    'from_username': self.username,
                    'accepted': accepted
                })
    
    def _handle_file_data(self, msg_data):
        """处理文件数据传输"""
        target_username = msg_data.get('target_username')
        file_data = msg_data.get('data')
        file_name = msg_data.get('file_name')
        
        if all([target_username, file_data, self.user_id]):
            with self.server.lock:
                if target_username in self.server.clients:
                    self.server.clients[target_username]._send_message({
                        'type': 'file_data',
                        'from_username': self.username,
                        'file_name': file_name,
                        'data': file_data
                    })
    
    def _handle_get_offline_messages(self, msg_data=None):
        """处理获取离线消息"""
        if self.user_id:
            messages = self.db.get_offline_messages(self.user_id)
            self._send_message({
                'type': 'offline_messages',
                'messages': messages,
                'success': True
            })
            # 删除已发送的离线消息
            self.db.delete_offline_messages(self.user_id)
    
    def _handle_user_list_request(self, msg_data=None):
        """处理用户列表请求"""
        all_users = []
        with self.server.lock:
            for username, client in self.server.clients.items():
                if username != self.username:
                    all_users.append(username)
        
        self._send_message({
            'type': 'user_list',
            'users': all_users
        })
    
    def _send_message(self, message: dict):
        """发送消息给此客户端"""
        try:
            msg_json = json.dumps(message, ensure_ascii=False).encode('utf-8')
            msg_len = struct.pack('!I', len(msg_json))
            self.client_socket.sendall(msg_len + msg_json)
        except (BrokenPipeError, ConnectionResetError, OSError):
            self.running = False
    
    def _receive_message(self):
        """从客户端接收消息"""
        try:
            raw_len = self._recvall(4)
            if not raw_len:
                return None
            msg_len = struct.unpack('!I', raw_len)[0]
            json_data = self._recvall(msg_len)
            if json_data:
                return json.loads(json_data.decode('utf-8'))
        except (struct.error, ConnectionResetError, json.JSONDecodeError, OSError):
            pass
        return None
    
    def _recvall(self, n: int):
        """确保接收到n个字节"""
        data = b''
        while len(data) < n:
            try:
                packet = self.client_socket.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            except socket.timeout:
                continue
            except (ConnectionResetError, OSError):
                return None
        return data
    
    def _log_message(self, message: str):
        """记录日志消息"""
        if hasattr(self.server, 'log_callback'):
            self.server.log_callback(message)
        if hasattr(self.server, 'monitor_callback'):
            self.server.monitor_callback(message)
        logger.info(message)
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.username and self.user_id:
                # 更新离线状态
                self.db.update_user(self.user_id, status='offline')
                
                # 清除会话
                if self.session_token:
                    self.db.clear_user_sessions(self.user_id)
                
                # 从服务器移除
                if hasattr(self.server, 'client_disconnected'):
                    self.server.client_disconnected(self.username)
            
            self.client_socket.close()
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")


class IMServer:
    """即时通讯服务器主类"""
    
    def __init__(self, host='127.0.0.1', port=8000, db_path='im_database.db', db=None, log_callback=None, monitor_callback=None):
        self.host = host
        self.port = port
        self.db_path = db_path
        self.server_socket = None
        self.running = False
        self.clients = {}  # {username: ClientThread}
        self.lock = threading.Lock()
        
        # 支持直接传入数据库实例
        if db:
            self.db = db
        else:
            self.db = UserDatabase(db_path)
        
        # 回调函数
        self.log_callback = log_callback or (lambda msg: None)
        self.monitor_callback = monitor_callback or (lambda msg: None)
        self.client_connected_callback = None
        self.client_disconnected_callback = None
        self.client_authenticated_callback = None
        
        # 启动心跳检查线程
        self.heartbeat_check_thread = None
    
    def start(self):
        """启动服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(100)
            self.server_socket.settimeout(1.0)
            self.running = True
            
            self._log_message(f"[OK] 服务器已启动，监听 {self.host}:{self.port}")
            
            # 启动服务器线程
            import threading
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            # 启动心跳检查线程
            self.heartbeat_check_thread = threading.Thread(target=self._check_heartbeats, daemon=True)
            self.heartbeat_check_thread.start()
            
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            raise
    
    def _run_server(self):
        """服务器运行线程"""
        try:
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    client_thread = ClientThread(client_socket, client_address, self, self.db)
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"接受连接出错: {e}")
                        
        finally:
            self.stop()
    
    def _check_heartbeats(self):
        """定期检查心跳超时的用户"""
        while self.running:
            try:
                time.sleep(15)  # 每15秒检查一次
                
                if not self.running:
                    break
                
                # 检查所有在线用户的心跳
                current_time = datetime.now()
                offline_users = []
                
                with self.lock:
                    for username, client_thread in list(self.clients.items()):
                        if hasattr(client_thread, 'last_heartbeat'):
                            time_diff = (current_time - client_thread.last_heartbeat).total_seconds()
                            if time_diff > 30:  # 超过30秒没有心跳
                                logger.info(f"[心跳超时] 用户 {username} 超过30秒未发送心跳，自动离线")
                                # 更新数据库状态
                                if client_thread.user_id:
                                    self.db.update_user(client_thread.user_id, status='offline')
                                offline_users.append(username)
                
                # 移除离线用户
                with self.lock:
                    for username in offline_users:
                        if username in self.clients:
                            del self.clients[username]
                                
            except Exception as e:
                logger.error(f"心跳检查出错: {e}")
    
    def stop(self):
        """停止服务器"""
        self.running = False
        
        # 关闭所有客户端连接
        with self.lock:
            for client in self.clients.values():
                client.running = False
            self.clients.clear()
        
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # 等待服务器线程结束
        if hasattr(self, 'server_thread') and self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)
        
        print("[OK] 服务器已停止")
    
    def _log_message(self, message: str):
        """记录日志消息"""
        if self.log_callback:
            try:
                self.log_callback(message)
            except:
                pass
        logger.info(message)
    
    def log_callback(self, message: str):
        """设置日志回调"""
        self.log_callback = lambda msg: None
    
    def monitor_callback(self, message: str):
        """设置监控回调"""
        self.monitor_callback = lambda msg: None
    
    def client_connected(self, ip: str):
        """客户端连接回调"""
        pass
    
    def client_disconnected(self, username: str):
        """客户端断开连接回调"""
        with self.lock:
            if username in self.clients:
                del self.clients[username]
        self._log_message(f"📤 用户 '{username}' 已断开连接")
    
    def client_authenticated(self, username: str, client_thread: ClientThread, ip: str):
        """客户端认证成功回调"""
        with self.lock:
            self.clients[username] = client_thread
        self._log_message(f"👤 用户 '{username}' 已认证 (IP: {ip})")
    
    def get_online_count(self) -> int:
        """获取在线用户数"""
        with self.lock:
            return len(self.clients)
    
    def get_online_users(self) -> list:
        """获取在线用户列表"""
        with self.lock:
            return list(self.clients.keys())
    
    def kick_user(self, username: str):
        """踢出用户"""
        with self.lock:
            if username in self.clients:
                self.clients[username]._send_message({
                    'type': 'kicked',
                    'message': '您已被管理员踢出'
                })
                self.clients[username].running = False
                return True
        return False


# 导入sqlite3用于会话查询
import sqlite3

# 导入数据库模块
from database import UserDatabase

# 兼容旧代码：NetworkServer 是 IMServer 的别名
NetworkServer = IMServer
