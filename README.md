# Nova Chatting - 即时通讯系统

一个基于 PyQt5 和 Socket 的即时通讯系统，支持用户注册、登录、好友管理、实时聊天等功能。

## 功能特性

- 用户注册与登录
- 好友添加与管理
- 实时消息收发
- 头像自定义（支持默认头像和自定义上传）
- 消息历史记录
- 验证码安全验证
- 用户状态显示（在线/离线）

## 项目结构

```
通讯/
├── 客户端/                 # 客户端代码
│   ├── client.py          # 客户端主程序入口
│   ├── client_network.py  # 网络通信模块
│   ├── client_ui_new.py   # 用户界面模块
│   ├── friend_request_manager.py  # 好友请求管理
│   ├── config.json        # 客户端配置
│   ├── requirements.txt   # 依赖包
│   ├── m.webp             # 默认男性头像
│   ├── w.webp             # 默认女性头像
│   └── cons/              # 资源文件
│
├── 服务端/                 # 服务端代码
│   ├── server.py          # 服务端主程序入口
│   ├── network_server.py  # 网络服务模块
│   ├── server_ui.py       # 服务端管理界面
│   ├── user_ui.py         # 用户管理界面
│   ├── database.py        # 数据库操作模块
│   ├── im_database.db     # SQLite 数据库
│   ├── config.json        # 服务端配置
│   └── requirements.txt   # 依赖包
│
└── README.md              # 项目说明文档
```

## 环境要求

- Python 3.8+
- PyQt5 >= 5.15.0

## 安装与运行

### 1. 克隆项目

```bash
git clone https://github.com/pluto1213819/Wechat.git
cd Wechat
```

### 2. 安装依赖

**客户端：**
```bash
cd 客户端
pip install -r requirements.txt
```

**服务端：**
```bash
cd 服务端
pip install PyQt5>=5.15.0
```

### 3. 运行程序

**启动服务端：**
```bash
cd 服务端
python server.py
```

**启动客户端：**
```bash
cd 客户端
python client.py
```

## 使用说明

### 服务端管理

1. 启动服务端后，会显示管理界面
2. 可以查看在线用户、注册用户列表
3. 支持用户管理（添加、编辑、删除用户）
4. 可配置服务器端口和参数

### 客户端使用

1. 启动客户端后，进入登录界面
2. 新用户点击"注册账号"进行注册
3. 已有账号直接输入用户名密码登录
4. 登录后可以：
   - 添加好友
   - 查看好友列表
   - 发送/接收消息
   - 修改个人信息和头像

## 配置说明

### 客户端配置 (config.json)

```json
{
    "server": "127.0.0.1",
    "port": 8000
}
```

### 服务端配置 (config.json)

```json
{
    "host": "0.0.0.0",
    "port": 8000
}
```

## 技术栈

- **GUI**: PyQt5
- **数据库**: SQLite3
- **网络通信**: Python Socket
- **数据格式**: JSON

## 注意事项

1. 确保服务端先启动，客户端才能正常连接
2. 默认服务器地址为 `127.0.0.1:8000`
3. 头像文件支持 webp、png、jpg 格式
4. 数据库文件会自动创建，无需手动初始化

## 许可证

MIT License

## 作者

pluto1213819
