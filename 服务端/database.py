# database.py - 仿QQ即时通讯系统数据库模块
import sqlite3
import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserDatabase:
    """用户数据库管理类"""
    
    def __init__(self, db_path='im_database.db'):
        if not db_path or db_path.strip() == '':
            db_path = 'im_database.db'
        self.db_path = db_path
        logger.info(f"数据库路径: {os.path.abspath(self.db_path)}")
        self._init_database()
        
    def _init_database(self):
        """初始化数据库表"""
        try:
            db_dir = os.path.dirname(os.path.abspath(self.db_path))
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"创建数据库目录: {db_dir}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT DEFAULT '',
                    password_hash TEXT NOT NULL,
                    avatar TEXT DEFAULT '',
                    status TEXT DEFAULT 'offline',
                    last_login TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    security_question TEXT DEFAULT '',
                    security_answer_hash TEXT DEFAULT '',
                    is_locked INTEGER DEFAULT 0,
                    login_attempts INTEGER DEFAULT 0,
                    lock_until TEXT DEFAULT NULL,
                    signature TEXT DEFAULT ''
                )
            ''')
            
            # 好友关系表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS friends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    friend_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    remark TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (friend_id) REFERENCES users(id),
                    UNIQUE(user_id, friend_id)
                )
            ''')
            
            # 群组表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    creator_id INTEGER NOT NULL,
                    avatar BLOB DEFAULT NULL,
                    description TEXT DEFAULT '',
                    max_members INTEGER DEFAULT 500,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creator_id) REFERENCES users(id)
                )
            ''')
            
            # 群成员表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (group_id, user_id),
                    FOREIGN KEY (group_id) REFERENCES groups(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 消息表（单聊和群聊）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER DEFAULT NULL,
                    group_id INTEGER DEFAULT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT DEFAULT 'text',
                    file_name TEXT DEFAULT NULL,
                    file_size INTEGER DEFAULT 0,
                    file_path TEXT DEFAULT NULL,
                    is_read INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender_id) REFERENCES users(id),
                    FOREIGN KEY (receiver_id) REFERENCES users(id),
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                )
            ''')
            
            # 离线消息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS offline_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receiver_id INTEGER NOT NULL,
                    sender_id INTEGER DEFAULT NULL,
                    group_id INTEGER DEFAULT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT DEFAULT 'text',
                    file_name TEXT DEFAULT NULL,
                    file_size INTEGER DEFAULT 0,
                    file_path TEXT DEFAULT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (receiver_id) REFERENCES users(id),
                    FOREIGN KEY (sender_id) REFERENCES users(id),
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                )
            ''')
            
            # 文件传输记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    file_path TEXT NOT NULL,
                    transfer_status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT DEFAULT NULL,
                    FOREIGN KEY (sender_id) REFERENCES users(id),
                    FOREIGN KEY (receiver_id) REFERENCES users(id)
                )
            ''')
            
            # 登录会话表（用于单设备登录限制）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    ip_address TEXT DEFAULT '',
                    device_info TEXT DEFAULT '',
                    last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_friends_user ON friends(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_friends_friend ON friends(friend_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_offline_messages_receiver ON offline_messages(receiver_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)')
            
            conn.commit()
            conn.close()
            logger.info(f"[OK] 数据库初始化完成: {os.path.abspath(self.db_path)}")
            
        except Exception as e:
            logger.error(f"[ERROR] 数据库初始化失败: {e}")
            raise
    
    def _hash_password(self, password: str) -> str:
        """使用SHA-256哈希密码"""
        try:
            salt = secrets.token_hex(16)
            hashed = hashlib.sha256((password + salt).encode()).hexdigest()
            return f"{salt}${hashed}"
        except Exception as e:
            logger.error(f"[ERROR] 密码哈希失败: {e}")
            return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            if not hashed_password:
                return False
            
            if '$' in hashed_password:
                salt, stored_hash = hashed_password.split('$', 1)
                new_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
                return new_hash == stored_hash
            else:
                return plain_password == hashed_password
        except Exception as e:
            logger.error(f"[ERROR] 密码验证失败: {e}")
            return False
    
    def get_user_by_username(self, username: str):
        """根据用户名获取用户信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password_hash, status, 
                       last_login, created_at, avatar, security_question,
                       is_locked, login_attempts, lock_until, signature
                FROM users WHERE username = ?
            ''', (username,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'password_hash': row[2],
                    'status': row[3] or 'offline',
                    'last_login': row[4],
                    'created_at': row[5],
                    'avatar': row[6],
                    'security_question': row[7] or '',
                    'is_locked': row[8] if row[8] is not None else 0,
                    'login_attempts': row[9] if row[9] is not None else 0,
                    'lock_until': row[10],
                    'signature': row[11] or ''
                }
            return None
        except Exception as e:
            logger.error(f"[ERROR] 获取用户失败: {e}")
            return None
    
    def get_user_by_id(self, user_id: int):
        """根据ID获取用户信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password_hash, status, 
                       last_login, created_at, avatar, security_question,
                       is_locked, login_attempts, lock_until, signature
                FROM users WHERE id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'password_hash': row[2],
                    'status': row[3] or 'offline',
                    'last_login': row[4],
                    'created_at': row[5],
                    'avatar': row[6],
                    'security_question': row[7] or '',
                    'is_locked': row[8] if row[8] is not None else 0,
                    'login_attempts': row[9] if row[9] is not None else 0,
                    'lock_until': row[10],
                    'signature': row[11] or ''
                }
            return None
        except Exception as e:
            logger.error(f"[ERROR] 获取用户失败: {e}")
            return None
    
    def add_user(self, username: str, password: str, 
                 security_question: str = "", security_answer: str = "", avatar: str = "") -> dict:
        """注册新用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return {'success': False, 'message': '用户名已存在'}
            
            password_hash = self._hash_password(password)
            security_answer_hash = self._hash_password(security_answer) if security_answer else ""
            
            cursor.execute('''
                INSERT INTO users (username, password, password_hash, 
                                  security_question, security_answer_hash, avatar)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, password, password_hash, security_question, security_answer_hash, avatar))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"[OK] 用户注册成功: {username}")
            return {'success': True, 'user_id': user_id, 'message': '注册成功'}
        except Exception as e:
            logger.error(f"[ERROR] 用户注册失败: {e}")
            return {'success': False, 'message': f'注册失败: {str(e)}'}
    
    def authenticate_user(self, username_or_id: str, password: str):
        """用户认证（带登录次数限制，支持用户名或ID登录）"""
        try:
            # 先尝试通过用户名查找
            user = self.get_user_by_username(username_or_id)
            
            # 如果找不到，尝试通过ID查找
            if not user:
                try:
                    user_id = int(username_or_id)
                    user = self.get_user_by_id(user_id)
                except (ValueError, TypeError):
                    pass
            
            if not user:
                return {'success': False, 'message': '该账号未注册'}
            
            username = user['username']
            
            # 检查账户是否被锁定
            if user.get('is_locked') == 1:
                lock_until = user.get('lock_until')
                if lock_until:
                    lock_time = datetime.strptime(lock_until, '%Y-%m-%d %H:%M:%S')
                    if datetime.now() < lock_time:
                        remaining_time = (lock_time - datetime.now()).seconds // 60
                        return {
                            'success': False, 
                            'message': f'账号已被锁定，请{remaining_time}分钟后再试'
                        }
                    else:
                        # 锁定时间已过，解锁账户
                        self._unlock_account(username)
            
            # 验证密码
            if self._verify_password(password, user['password_hash']):
                # 密码正确，重置登录尝试次数
                self._reset_login_attempts(username)
                
                # 更新最后登录时间
                self.update_user(user['id'], last_login=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                return {'success': True, 'user': user}
            else:
                # 密码错误，增加登录尝试次数
                attempts = self._increment_login_attempts(username)
                remaining = 5 - attempts
                
                if remaining <= 0:
                    # 超过最大尝试次数，锁定账户30分钟
                    self._lock_account(username, minutes=30)
                    return {
                        'success': False, 
                        'message': '密码错误次数过多，账号已被锁定30分钟'
                    }
                else:
                    return {
                        'success': False, 
                        'message': f'密码错误，剩余{remaining}次尝试机会'
                    }
        except Exception as e:
            logger.error(f"[ERROR] 用户认证异常: {e}")
            return {'success': False, 'message': f'认证异常: {str(e)}'}
    
    def _increment_login_attempts(self, username: str) -> int:
        """增加登录尝试次数"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET login_attempts = COALESCE(login_attempts, 0) + 1
                WHERE username = ?
            ''', (username,))
            conn.commit()
            
            cursor.execute('SELECT login_attempts FROM users WHERE username = ?', (username,))
            attempts = cursor.fetchone()[0]
            conn.close()
            return attempts
        except Exception as e:
            logger.error(f"[ERROR] 更新登录尝试次数失败: {e}")
            return 0
    
    def _reset_login_attempts(self, username: str):
        """重置登录尝试次数"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET login_attempts = 0, is_locked = 0, lock_until = NULL
                WHERE username = ?
            ''', (username,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[ERROR] 重置登录尝试次数失败: {e}")
    
    def _lock_account(self, username: str, minutes: int = 30):
        """锁定账户"""
        try:
            lock_until = datetime.now() + timedelta(minutes=minutes)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET is_locked = 1, lock_until = ?
                WHERE username = ?
            ''', (lock_until.strftime('%Y-%m-%d %H:%M:%S'), username))
            conn.commit()
            conn.close()
            logger.info(f"[WARNING] 用户 {username} 账户已被锁定")
        except Exception as e:
            logger.error(f"[ERROR] 锁定账户失败: {e}")
    
    def _unlock_account(self, username: str):
        """解锁账户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET is_locked = 0, lock_until = NULL, login_attempts = 0
                WHERE username = ?
            ''', (username,))
            conn.commit()
            conn.close()
            logger.info(f"[OK] 用户 {username} 账户已解锁")
        except Exception as e:
            logger.error(f"[ERROR] 解锁账户失败: {e}")
    
    def unlock_user_by_id(self, user_id: int) -> bool:
        """通过用户ID解锁账户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET is_locked = 0, lock_until = NULL, login_attempts = 0
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            if success:
                logger.info(f"[OK] 用户ID {user_id} 账户已解锁")
            return success
        except Exception as e:
            logger.error(f"[ERROR] 解锁账户失败: {e}")
            return False
    
    def lock_user_by_id(self, user_id: int, minutes: int = 30) -> bool:
        """通过用户ID锁定账户"""
        try:
            lock_until = datetime.now() + timedelta(minutes=minutes)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET is_locked = 1, lock_until = ?
                WHERE id = ?
            ''', (lock_until.strftime('%Y-%m-%d %H:%M:%S'), user_id))
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            if success:
                logger.info(f"[OK] 用户ID {user_id} 账户已锁定")
            return success
        except Exception as e:
            logger.error(f"[ERROR] 锁定账户失败: {e}")
            return False
    
    def verify_security_answer(self, username: str, answer: str) -> bool:
        """验证安全问题答案"""
        try:
            user = self.get_user_by_username(username)
            if not user:
                return False
            
            stored_hash = user.get('security_answer_hash', '')
            if not stored_hash:
                return False
            
            return self._verify_password(answer, stored_hash)
        except Exception as e:
            logger.error(f"[ERROR] 验证安全答案失败: {e}")
            return False
    
    def reset_password(self, username: str, new_password: str) -> bool:
        """重置密码"""
        try:
            new_hash = self._hash_password(new_password)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET password_hash = ?, login_attempts = 0, 
                              is_locked = 0, lock_until = NULL
                WHERE username = ?
            ''', (new_hash, username))
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            if success:
                logger.info(f"[OK] 用户 {username} 密码重置成功")
            return success
        except Exception as e:
            logger.error(f"[ERROR] 重置密码失败: {e}")
            return False
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """更新用户信息"""
        try:
            if not kwargs:
                return False
                
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                if key == 'password':
                    set_clauses.append("password_hash = ?")
                    values.append(self._hash_password(value))
                elif key == 'security_answer':
                    set_clauses.append("security_answer_hash = ?")
                    values.append(self._hash_password(value))
                else:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(user_id)
            sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql, values)
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            return success
        except Exception as e:
            logger.error(f"[ERROR] 更新用户失败: {e}")
            return False
    
    def search_users(self, keyword: str, search_type: str = 'username', current_user_id: int = None) -> list:
        """搜索用户（支持模糊搜索和精准查找）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if search_type == 'id':
                # 精准查找
                cursor.execute('''
                    SELECT id, username, status, signature
                    FROM users WHERE id = ? AND id != ?
                ''', (keyword, current_user_id or 0))
            else:
                # 模糊搜索
                cursor.execute('''
                    SELECT id, username, status, signature
                    FROM users WHERE username LIKE ? AND id != ?
                ''', (f'%{keyword}%', current_user_id or 0))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'id': row[0],
                'username': row[1],
                'status': row[2] or 'offline',
                'signature': row[3] or ''
            } for row in rows]
        except Exception as e:
            logger.error(f"[ERROR] 搜索用户失败: {e}")
            return []
    
    def send_friend_request(self, from_username: str, to_username: str) -> bool:
        """发送好友请求"""
        try:
            logger.info(f"[好友请求] 查询用户: from={from_username}, to={to_username}")
            from_user = self.get_user_by_username(from_username)
            to_user = self.get_user_by_username(to_username)
            
            logger.info(f"[好友请求] 查询结果: from_user={from_user is not None}, to_user={to_user is not None}")
            
            if not from_user or not to_user:
                logger.error(f"用户不存在: from={from_username}(found={from_user is not None}), to={to_username}(found={to_user is not None})")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否已经是好友
            cursor.execute('''
                SELECT * FROM friends 
                WHERE ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
                AND status = 'accepted'
            ''', (from_user['id'], to_user['id'], to_user['id'], from_user['id']))
            
            if cursor.fetchone():
                logger.error(f"已经是好友: {from_username} -> {to_username}")
                conn.close()
                return False
            
            # 检查是否已有待处理的申请
            cursor.execute('''
                SELECT * FROM friends 
                WHERE ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
                AND status = 'pending'
            ''', (from_user['id'], to_user['id'], to_user['id'], from_user['id']))
            
            if cursor.fetchone():
                logger.error(f"已有待处理申请: {from_username} -> {to_username}")
                conn.close()
                return False
            
            # 插入好友请求
            cursor.execute('''
                INSERT OR IGNORE INTO friends (user_id, friend_id, status)
                VALUES (?, ?, 'pending')
            ''', (from_user['id'], to_user['id']))
            
            conn.commit()
            logger.info(f"[OK] 好友请求发送成功: {from_username} -> {to_username}")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[ERROR] 发送好友请求失败: {e}")
            return False
    
    def accept_friend_request(self, from_username: str, to_username: str) -> bool:
        """接受好友请求"""
        try:
            from_user = self.get_user_by_username(from_username)
            to_user = self.get_user_by_username(to_username)
            
            if not from_user or not to_user:
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新请求状态为accepted
            cursor.execute('''
                UPDATE friends SET status = 'accepted'
                WHERE user_id = ? AND friend_id = ? AND status = 'pending'
            ''', (from_user['id'], to_user['id']))
            
            # 创建双向好友关系
            if cursor.rowcount > 0:
                cursor.execute('''
                    INSERT OR IGNORE INTO friends (user_id, friend_id, status)
                    VALUES (?, ?, 'accepted')
                ''', (to_user['id'], from_user['id']))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[ERROR] 接受好友请求失败: {e}")
            return False
    
    def reject_friend_request(self, from_username: str, to_username: str) -> bool:
        """拒绝好友请求"""
        try:
            from_user = self.get_user_by_username(from_username)
            to_user = self.get_user_by_username(to_username)
            
            if not from_user or not to_user:
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM friends 
                WHERE user_id = ? AND friend_id = ? AND status = 'pending'
            ''', (from_user['id'], to_user['id']))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[ERROR] 拒绝好友请求失败: {e}")
            return False
    
    def get_pending_friend_requests(self, username: str) -> list:
        """获取用户的待处理好友请求"""
        try:
            user = self.get_user_by_username(username)
            if not user:
                return []
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.username, u.signature, u.avatar
                FROM friends f JOIN users u ON f.user_id = u.id
                WHERE f.friend_id = ? AND f.status = 'pending'
            ''', (user['id'],))
            
            requests = []
            for row in cursor.fetchall():
                requests.append({
                    'username': row[0],
                    'signature': row[1] or '',
                    'avatar': row[2]
                })
            
            conn.close()
            return requests
        except Exception as e:
            logger.error(f"[ERROR] 获取好友请求失败: {e}")
            return []
    
    def get_all_friend_requests(self) -> list:
        """获取所有好友申请"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT f.id, u1.username as from_username, u2.username as to_username, 
                       f.status, f.created_at
                FROM friends f 
                JOIN users u1 ON f.user_id = u1.id
                JOIN users u2 ON f.friend_id = u2.id
                WHERE f.status IN ('pending', 'accepted', 'rejected')
                ORDER BY f.created_at DESC
            ''')
            
            requests = []
            for row in cursor.fetchall():
                requests.append({
                    'id': row[0],
                    'from_username': row[1],
                    'to_username': row[2],
                    'status': row[3],
                    'created_at': row[4]
                })
            
            conn.close()
            return requests
        except Exception as e:
            logger.error(f"[ERROR] 获取所有好友申请失败: {e}")
            return []
    
    def get_friends(self, username: str) -> list:
        """获取好友列表"""
        try:
            user = self.get_user_by_username(username)
            if not user:
                return []
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.username, u.status, u.signature, u.avatar
                FROM friends f JOIN users u ON f.friend_id = u.id
                WHERE f.user_id = ? AND f.status = 'accepted'
            ''', (user['id'],))
            
            friends = []
            for row in cursor.fetchall():
                friends.append({
                    'id': row[0],
                    'username': row[1],
                    'status': row[2] or 'offline',
                    'signature': row[3] or '',
                    'avatar': row[4]
                })
            
            conn.close()
            return friends
        except Exception as e:
            logger.error(f"[ERROR] 获取好友列表失败: {e}")
            return []
    
    def create_session(self, user_id: int, ip_address: str = '', device_info: str = '') -> str:
        """创建登录会话（用于单设备登录）"""
        try:
            # 先清除该用户的其他会话
            self.clear_user_sessions(user_id)
            
            token = secrets.token_urlsafe(32)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (user_id, session_token, ip_address, device_info)
                VALUES (?, ?, ?, ?)
            ''', (user_id, token, ip_address, device_info))
            conn.commit()
            conn.close()
            return token
        except Exception as e:
            logger.error(f"[ERROR] 创建会话失败: {e}")
            return ''
    
    def clear_user_sessions(self, user_id: int):
        """清除用户的所有会话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[ERROR] 清除会话失败: {e}")
    
    def validate_session(self, user_id: int, token: str) -> bool:
        """验证会话有效性"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sessions WHERE user_id = ? AND session_token = ?
            ''', (user_id, token))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"[ERROR] 验证会话失败: {e}")
            return False
    
    def create_group(self, name: str, creator_id: int, description: str = '') -> int:
        """创建群组"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO groups (name, creator_id, description)
                VALUES (?, ?, ?)
            ''', (name, creator_id, description))
            group_id = cursor.lastrowid
            
            # 创建者自动成为群主
            cursor.execute('''
                INSERT INTO group_members (group_id, user_id, role)
                VALUES (?, ?, 'admin')
            ''', (group_id, creator_id))
            
            conn.commit()
            conn.close()
            logger.info(f"[OK] 群组创建成功: {name} (ID: {group_id})")
            return group_id
        except Exception as e:
            logger.error(f"[ERROR] 创建群组失败: {e}")
            return 0
    
    def add_group_member(self, group_id: int, user_id: int, role: str = 'member') -> bool:
        """添加群成员"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO group_members (group_id, user_id, role)
                VALUES (?, ?, ?)
            ''', (group_id, user_id, role))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[ERROR] 添加群成员失败: {e}")
            return False
    
    def remove_group_member(self, group_id: int, user_id: int) -> bool:
        """移除群成员"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM group_members WHERE group_id = ? AND user_id = ?
            ''', (group_id, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[ERROR] 移除群成员失败: {e}")
            return False
    
    def get_group_members(self, group_id: int) -> list:
        """获取群成员列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.username, u.status, gm.role
                FROM group_members gm JOIN users u ON gm.user_id = u.id
                WHERE gm.group_id = ?
            ''', (group_id,))
            
            members = []
            for row in cursor.fetchall():
                members.append({
                    'id': row[0],
                    'username': row[1],
                    'status': row[2] or 'offline',
                    'role': row[3]
                })
            
            conn.close()
            return members
        except Exception as e:
            logger.error(f"[ERROR] 获取群成员失败: {e}")
            return []
    
    def get_user_groups(self, user_id: int) -> list:
        """获取用户加入的群组列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT g.id, g.name, g.description, g.creator_id, COUNT(gm.user_id) as member_count
                FROM groups g JOIN group_members gm ON g.id = gm.group_id
                WHERE gm.user_id = ?
                GROUP BY g.id
            ''', (user_id,))
            
            groups = []
            for row in cursor.fetchall():
                groups.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2] or '',
                    'creator_id': row[3],
                    'member_count': row[4]
                })
            
            conn.close()
            return groups
        except Exception as e:
            logger.error(f"[ERROR] 获取用户群组失败: {e}")
            return []
    
    def save_message(self, sender_id: int, receiver_id: int = None, 
                     group_id: int = None, content: str = '', 
                     message_type: str = 'text', **kwargs) -> int:
        """保存消息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (sender_id, receiver_id, group_id, content, 
                                    message_type, file_name, file_size, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sender_id, receiver_id, group_id, content, message_type,
                   kwargs.get('file_name'), kwargs.get('file_size', 0), kwargs.get('file_path')))
            msg_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return msg_id
        except Exception as e:
            logger.error(f"[ERROR] 保存消息失败: {e}")
            return 0
    
    def save_offline_message(self, receiver_id: int, sender_id: int = None,
                            group_id: int = None, content: str = '',
                            message_type: str = 'text', **kwargs) -> int:
        """保存离线消息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO offline_messages (receiver_id, sender_id, group_id, content,
                                            message_type, file_name, file_size, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (receiver_id, sender_id, group_id, content, message_type,
                   kwargs.get('file_name'), kwargs.get('file_size', 0), kwargs.get('file_path')))
            msg_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return msg_id
        except Exception as e:
            logger.error(f"[ERROR] 保存离线消息失败: {e}")
            return 0
    
    def get_offline_messages(self, user_id: int) -> list:
        """获取用户的离线消息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT om.id, om.sender_id, om.receiver_id, om.group_id, om.content,
                       om.message_type, om.file_name, om.file_size, om.file_path, om.created_at,
                       u.username
                FROM offline_messages om LEFT JOIN users u ON om.sender_id = u.id
                WHERE om.receiver_id = ?
                ORDER BY om.created_at ASC
            ''', (user_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'sender_id': row[1],
                    'receiver_id': row[2],
                    'group_id': row[3],
                    'content': row[4],
                    'message_type': row[5],
                    'file_name': row[6],
                    'file_size': row[7],
                    'file_path': row[8],
                    'created_at': row[9],
                    'sender_username': row[10]
                })
            
            conn.close()
            return messages
        except Exception as e:
            logger.error(f"[ERROR] 获取离线消息失败: {e}")
            return []
    
    def delete_offline_messages(self, user_id: int):
        """删除用户的离线消息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM offline_messages WHERE receiver_id = ?', (user_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[ERROR] 删除离线消息失败: {e}")
    
    def get_chat_history(self, user1_id: int, user2_id: int, limit: int = 50) -> list:
        """获取两个用户之间的聊天历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.id, m.sender_id, m.content, m.message_type, m.file_name,
                       m.created_at, u.username
                FROM messages m JOIN users u ON m.sender_id = u.id
                WHERE ((m.sender_id = ? AND m.receiver_id = ?) OR 
                       (m.sender_id = ? AND m.receiver_id = ?))
                      AND m.group_id IS NULL
                ORDER BY m.created_at DESC
                LIMIT ?
            ''', (user1_id, user2_id, user2_id, user1_id, limit))
            
            messages = []
            for row in reversed(cursor.fetchall()):
                messages.append({
                    'id': row[0],
                    'sender_id': row[1],
                    'content': row[2],
                    'message_type': row[3],
                    'file_name': row[4],
                    'created_at': row[5],
                    'sender_username': row[6]
                })
            
            conn.close()
            return messages
        except Exception as e:
            logger.error(f"[ERROR] 获取聊天历史失败: {e}")
            return []
    
    def get_all_users(self) -> list:
        """获取所有用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password, status, created_at, password_hash, avatar, is_locked
                FROM users ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'id': row[0],
                'username': row[1],
                'password': row[2] or '',
                'status': row[3] or 'offline',
                'created_at': row[4],
                'password_hash': row[5],
                'avatar': row[6] or '',
                'is_locked': row[7] if row[7] is not None else 0
            } for row in rows]
        except Exception as e:
            logger.error(f"[ERROR] 获取所有用户失败: {e}")
            return []
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 禁用外键约束
            cursor.execute('PRAGMA foreign_keys = OFF')
            
            # 先删除相关的数据
            # 删除好友关系（包括好友申请）
            cursor.execute('DELETE FROM friends WHERE user_id = ? OR friend_id = ?', (user_id, user_id))
            logger.info(f"[删除用户] 删除好友关系: {cursor.rowcount} 行")
            
            # 删除离线消息
            cursor.execute('DELETE FROM offline_messages WHERE receiver_id = ?', (user_id,))
            logger.info(f"[删除用户] 删除离线消息: {cursor.rowcount} 行")
            
            # 删除会话
            cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            logger.info(f"[删除用户] 删除会话: {cursor.rowcount} 行")
            
            # 删除群组成员关系
            cursor.execute('DELETE FROM group_members WHERE user_id = ?', (user_id,))
            logger.info(f"[删除用户] 删除群组成员: {cursor.rowcount} 行")
            
            # 删除消息记录
            cursor.execute('DELETE FROM messages WHERE sender_id = ? OR receiver_id = ?', (user_id, user_id))
            logger.info(f"[删除用户] 删除消息记录: {cursor.rowcount} 行")
            
            # 删除用户创建的群组
            cursor.execute('DELETE FROM groups WHERE creator_id = ?', (user_id,))
            logger.info(f"[删除用户] 删除群组: {cursor.rowcount} 行")
            
            # 最后删除用户
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            user_deleted = cursor.rowcount > 0
            logger.info(f"[删除用户] 删除用户: {cursor.rowcount} 行")
            
            conn.commit()
            
            # 重新启用外键约束
            cursor.execute('PRAGMA foreign_keys = ON')
            conn.close()
            
            if user_deleted:
                logger.info(f"[SUCCESS] 用户 {user_id} 已删除")
                return True
            else:
                logger.error(f"[ERROR] 用户 {user_id} 不存在")
                return False
        except Exception as e:
            logger.error(f"[ERROR] 删除用户失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
