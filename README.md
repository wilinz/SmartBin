# 🗑️ SmartBin 智能垃圾分拣系统

基于YOLOv8的实时垃圾识别与自动分拣系统，支持9种垃圾类别识别，配备Web界面和机械臂控制功能。

## 🌟 项目特色

- ✅ **高精度识别**: 基于YOLOv8模型，mAP@0.5达到91.1%
- ✅ **实时检测**: 支持摄像头实时检测，帧率1-5FPS可调
- ✅ **前后端分离**: Next.js + Flask架构，现代化UI设计
- ✅ **机械臂控制**: 支持虚拟机械臂和真实机械臂切换
- ✅ **智能分拣**: 自动抓取和分类垃圾到指定位置
- ✅ **可视化监控**: 实时状态监控和操作历史记录

## 📦 支持的垃圾类别

| 类别 | 中文名称 | 英文标识 | 分拣箱位置 |
|------|----------|----------|------------|
| 🍌 | 香蕉皮 | banana | 位置1 |
| 🍶 | 饮料瓶 | beverages | 位置2 |
| 📦 | 纸盒 | cardboard_box | 位置3 |
| 🥔 | 薯片袋 | chips | 位置4 |
| 🐟 | 鱼骨 | fish_bones | 位置5 |
| 🍜 | 泡面盒 | instant_noodles | 位置6 |
| 🥛 | 牛奶盒1 | milk_box_type1 | 位置7 |
| 🧈 | 牛奶盒2 | milk_box_type2 | 位置8 |
| ♻️ | 塑料 | plastic | 位置9 |

## 🏗️ 系统架构

```
SmartBin System
├── 前端 (React: Next.js + TypeScript)          # 端口: 3000
│   ├── 实时检测界面
│   ├── 机械臂控制面板
│   └── 系统状态监控
├── 后端 (Yolov8: Flask + Python)               # 端口: 5001
│   ├── YOLOv8 检测服务
│   ├── 机械臂控制服务
│   └── RESTful API
└── 硬件层
    ├── 摄像头 (USB/网络摄像头)
    └── 机械臂 (虚拟/真实)
```

## 📁 目录结构

```
smartbin/
├── 📄 README.md                    # 项目说明文档
├── 📄 requirements.txt             # Python依赖包
├── 🗂️ config/                      # 配置文件
│   ├── hardware_config.yaml       # 硬件配置
│   ├── model_config.yaml         # 模型配置
│   └── system_config.yaml        # 系统配置
├── 🗂️ data/                        # 原始数据集 (被gitignore)
│   ├── banana/                   # 各类垃圾数据
│   ├── beverages/                # ...
│   └── README.md                 # 数据集说明
├── 🗂️ datasets/                    # 处理后数据集 (被gitignore)
│   ├── converted/                # 转换后的数据
│   ├── yolo_dataset/            # YOLO格式数据
│   └── README.md                # 数据集说明
├── 🗂️ models/                      # 训练好的模型 (被gitignore)
├── 🗂️ src/                         # 后端源码
│   ├── data_processing/          # 数据处理
│   ├── hardware/                 # 硬件控制
│   ├── models/                   # 模型相关
│   ├── system/                   # 系统控制
│   ├── utils/                    # 工具函数
│   └── web_interface/            # Flask应用
├── 🗂️ web/                         # 前端源码 (Next.js)
│   ├── app/                      # Next.js 应用
│   ├── public/                   # 静态资源
│   └── package.json              # 前端依赖
├── 🗂️ scripts/                     # 工具脚本
├── 🗂️ logs/                        # 系统日志
└── 🗂️ docs/                        # 文档
```

## 🚀 快速开始

### 1. 环境要求

- **Python**: 3.8+
- **Node.js**: 18+
- **操作系统**: Windows/macOS/Linux
- **内存**: 8GB+
- **显卡**: 支持CUDA (可选)

### 2. 安装依赖

#### 后端依赖 (Python)
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 前端依赖 (Node.js)
```bash
cd web
npm install
```

### 3. 准备数据和模型

#### 数据集准备
```bash
# 如果有原始数据，运行数据预处理
python scripts/prepare_data.py

# 或者下载预训练模型 (推荐)
# 项目已包含预训练模型: https://github.com/wilinz/SmartBin/releases/download/1.0.0/best.pt
```

### 4. 启动系统

#### 方法一：分别启动前后端
```bash
# 终端1: 启动后端服务
python scripts/run_system.py

# 终端2: 启动前端服务
cd web
npm run dev
```

#### 方法三：前端多种启动模式

##### 开发模式 (推荐)
```bash
cd web
# 默认启动 (使用Turbopack加速)
npm run dev

# 指定端口
npm run dev -- --port 3000

# 关闭Turbopack (使用传统模式)
npm run dev -- --no-turbopack

# 或者使用yarn
yarn dev
```

##### 生产模式
```bash
cd web
# 构建生产版本
npm run build

# 启动生产服务器
npm run start
# 或者
npm start
```

##### 调试模式
```bash
cd web
# 启用Turbopack详细日志
npm run dev -- --show-all

# 指定端口
npm run dev -- --port 3001

# 开启实验性功能
npm run dev -- --experimental-https

# 禁用Turbopack (传统webpack模式)
npm run dev -- --no-turbopack
```

##### 后台运行
```bash
cd web
# 使用 PM2 (需要先安装: npm install -g pm2)
pm2 start npm --name "smartbin-frontend" -- run dev

# 使用 nohup (Linux/macOS)
nohup npm run dev > frontend.log 2>&1 &

# 查看后台进程
pm2 list
# 或者
ps aux | grep npm
```

##### Docker 启动 (可选)
```bash
cd web
# 构建 Docker 镜像
docker build -t smartbin-frontend .

# 运行容器
docker run -p 3000:3000 smartbin-frontend

# 或者使用 docker-compose
docker-compose up frontend
```

#### 方法四：环境变量配置启动

##### 创建环境配置文件
```bash
cd web
# 创建开发环境配置
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:5001
NEXT_PUBLIC_WS_URL=ws://localhost:5001
NODE_ENV=development
PORT=3000
EOF

# 创建生产环境配置
cat > .env.production << EOF
NEXT_PUBLIC_API_URL=http://your-backend-server.com:5001
NEXT_PUBLIC_WS_URL=ws://your-backend-server.com:5001
NODE_ENV=production
PORT=3000
EOF
```

##### 使用环境变量启动
```bash
cd web
# 指定环境启动
NODE_ENV=development npm run dev

# 自定义API地址
NEXT_PUBLIC_API_URL=http://192.168.1.100:5001 npm run dev

# 指定端口和API地址
PORT=3001 NEXT_PUBLIC_API_URL=http://localhost:5002 npm run dev
```

#### 方法五：多终端并行启动

##### 使用 tmux (推荐)
```bash
# 创建新会话
tmux new-session -d -s smartbin

# 分割窗口
tmux split-window -h

# 启动后端 (左窗口)
tmux send-keys -t smartbin:0.0 'python src/web_interface/app.py' Enter

# 启动前端 (右窗口)
tmux send-keys -t smartbin:0.1 'cd web && npm run dev' Enter

# 连接到会话
tmux attach-session -t smartbin
```

##### 使用 screen
```bash
# 创建后端会话
screen -dmS backend python src/web_interface/app.py

# 创建前端会话
screen -dmS frontend bash -c 'cd web && npm run dev'

# 查看所有会话
screen -ls

# 连接到会话
screen -r frontend
```

### 5. 访问系统

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:5001

#### 多端口访问 (如果自定义端口)
- **前端开发服务器**: http://localhost:3000 (默认)
- **前端生产服务器**: http://localhost:3000 (默认)
- **自定义端口示例**: http://localhost:3001
- **局域网访问**: http://[您的IP地址]:3000

#### 移动设备访问
```bash
# 查看本机IP地址
# Windows:
ipconfig
# macOS/Linux:
ifconfig

# 然后在移动设备浏览器访问
# 例如: http://192.168.1.100:3000
```

## 🎮 使用指南

### 1. 模型管理

1. **加载检测模型**
   - 点击"📥 加载检测模型"按钮
   - 系统会自动加载最佳模型
   - 状态栏显示"🤖 检测模型: 正常"

2. **模型性能**
   - **准确率**: mAP@0.5 = 91.1%
   - **速度**: 推理时间 < 100ms
   - **支持类别**: 9种垃圾类型

### 2. 机械臂管理

1. **选择机械臂类型**
   - 点击"🦾 机械臂管理" → "🔽 展开"
   - 选择机械臂类型：
     - **虚拟机械臂** (默认) - 用于演示和测试
     - **Universal Robots** - 需要TCP配置
     - **KUKA机械臂** - 需要KRL配置
     - **ABB机械臂** - 暂不支持

2. **连接机械臂**
   - 选择机械臂类型后点击"连接"
   - 状态栏显示"🦾 机械臂: 正常"

3. **机械臂控制**
   - **🏠 归位**: 机械臂回到初始位置
   - **🚨 急停**: 紧急停止所有动作
   - **测试分拣**: 测试特定垃圾类型的分拣流程

### 3. 实时检测

1. **启动摄像头检测**
   - 点击"📹 开始实时检测"
   - 授权摄像头访问权限
   - 调整检测参数：
     - **检测频率**: 0.5-5 FPS
     - **触发阈值**: 10-100% (推荐70%)

2. **检测流程**
   - 摄像头实时捕获画面
   - AI模型进行垃圾检测
   - 置信度 ≥ 阈值时触发机械臂
   - 自动抓取并分拣到对应位置

3. **停止检测**
   - 点击"🛑 停止实时检测"
   - 摄像头和检测服务停止

### 4. 图像检测

1. **上传图像**
   - 点击"📁 点击选择图像文件"
   - 选择JPG/PNG格式图像
   - 点击"🔍 开始检测"

2. **查看结果**
   - 显示带检测框的图像
   - 显示检测到的垃圾类型和置信度

### 5. 系统监控

#### 状态指示器
- **🤖 检测模型**: 模型加载状态
- **📹 摄像头**: 摄像头连接状态
- **🦾 机械臂**: 机械臂连接状态
- **🔍 实时检测**: 检测服务状态
- **✅ 系统就绪**: 整体系统状态

#### 机械臂状态
- **运行状态**: 空闲/运行中
- **抓取状态**: 有物体/空闲
- **当前位置**: (x, y, z) 坐标
- **配置参数**: 最大半径、负载、精度等

## 🔧 API 接口

### 系统状态
```http
GET /api/status
```

### 模型管理
```http
POST /api/load_model
POST /api/detect_image (multipart/form-data)
```

### 机械臂控制
```http
GET  /api/robot_arm/types
GET  /api/robot_arm/current_config
POST /api/robot_arm/switch_type
POST /api/robot_arm/connect
POST /api/robot_arm/disconnect
POST /api/robot_arm/grab
POST /api/robot_arm/home
POST /api/robot_arm/emergency_stop
POST /api/robot_arm/test_sort/{garbage_type}
```

## 🛠️ 配置说明

### 系统配置 (config/system_config.yaml)
```yaml
system:
  name: "SmartBin垃圾分拣系统"
  version: "1.0.0"
  debug: true

api:
  host: "0.0.0.0"
  port: 5001
  cors_enabled: true
```

### 模型配置 (config/model_config.yaml)
```yaml
model:
  name: "garbage_sorting"
  type: "yolov8"
  path: "models/garbage_sorting_1751471880/weights/best.pt"
  confidence_threshold: 0.5
  iou_threshold: 0.45
```

### 硬件配置 (config/hardware_config.yaml)
```yaml
camera:
  device_id: 0
  resolution: [640, 480]
  fps: 30

robot_arm:
  default_type: "virtual"
  move_speed: 100
  grab_force: 50
```

## 🐛 故障排除

### 常见问题

1. **前端启动失败**
   ```
   问题：npm run dev 无法启动
   解决方案：
   - 检查Node.js版本 (需要18+): node --version
   - 清除缓存: npm cache clean --force
   - 删除node_modules重新安装: rm -rf node_modules && npm install
   - 检查端口占用: lsof -i :3000 (macOS/Linux) 或 netstat -ano | findstr :3000 (Windows)
   - 使用不同端口: npm run dev -- --port 3001
   ```

2. **前端依赖安装失败**
   ```
   问题：npm install 报错
   解决方案：
   - 使用国内镜像: npm config set registry https://registry.npmmirror.com
   - 清除npm缓存: npm cache clean --force
   - 使用yarn替代: yarn install
   - 检查网络连接和防火墙设置
   - 更新npm版本: npm install -g npm@latest
   ```

3. **前端页面空白或样式异常**
   ```
   问题：页面显示不正常
   解决方案：
   - 硬刷新浏览器: Ctrl+F5 (Windows) 或 Cmd+Shift+R (macOS)
   - 清除浏览器缓存
   - 检查控制台错误信息 (F12)
   - 确认后端API服务正常运行
   - 验证API_URL配置: web/app/config/api.ts
   ```

4. **前后端连接失败**
   ```
   问题：前端无法连接后端API
   解决方案：
   - 确认后端服务在5001端口运行: curl http://localhost:5001/api/status
   - 检查CORS设置和防火墙
   - 验证API端点配置 (web/app/config/api.ts)
   - 查看浏览器网络标签是否有404/500错误
   - 检查环境变量: NEXT_PUBLIC_API_URL
   ```

5. **摄像头无法访问**
   ```
   问题：浏览器无法访问摄像头
   解决方案：
   - 检查摄像头是否被其他应用占用
   - 确认浏览器已授权摄像头权限
   - 使用HTTPS访问 (某些浏览器要求)
   - 尝试更换USB端口或摄像头
   - 检查浏览器兼容性 (推荐Chrome/Firefox)
   ```

6. **模型加载失败**
   ```
   问题：AI模型无法加载
   解决方案：
   - 检查模型文件是否存在
   - 确认Python环境已安装所有依赖
   - 查看logs/web_app.log获取详细错误信息
   - 验证模型路径配置正确
   - 确保有足够的内存空间
   ```

7. **机械臂连接失败**
   ```
   问题：机械臂无法连接或控制
   解决方案：
   - 虚拟机械臂应该始终可用
   - 真实机械臂需要正确的IP和配置
   - 检查机械臂状态指示器
   - 验证网络连接和权限设置
   - 查看系统日志获取错误详情
   ```

8. **性能问题**
   ```
   问题：系统运行缓慢
   解决方案：
   - 降低检测频率 (1-2 FPS)
   - 关闭不必要的浏览器标签
   - 检查系统资源占用
   - 确保有足够的内存 (推荐8GB+)
   - 考虑使用GPU加速 (如果可用)
   ```

### 日志查看
```bash
# 查看Web应用日志
tail -f logs/web_app.log

# 查看训练日志
tail -f logs/training.log

# 查看前端开发日志
cd web
npm run dev 2>&1 | tee frontend.log

# 查看前端构建日志
npm run build 2>&1 | tee build.log
```

### 前端开发技巧

#### 热重载和调试
```bash
cd web

# 启用详细日志
NEXT_TELEMETRY_DEBUG=1 npm run dev

# 查看构建详情
npm run build

# 分析构建输出
npx @next/bundle-analyzer

# 检查Next.js信息
npx next info
```

#### 前端性能优化
```bash
cd web

# 清理构建缓存
rm -rf .next/ node_modules/.cache/

# 重新构建
npm run build

# 检查包依赖
npm ls --depth=0

# 更新依赖
npm update

# 安全审计
npm audit

# 检查过期依赖
npm outdated
```

#### 代码检查和格式化
```bash
cd web

# 运行ESLint检查
npm run lint

# 自动修复ESLint问题
npm run lint -- --fix

# 手动TypeScript类型检查
npx tsc --noEmit

# 检查Next.js配置
npx next info

# 清理依赖
npm audit fix
```

## 🏆 性能指标

### 模型性能
- **mAP@0.5**: 91.1%
- **平均推理时间**: <100ms
- **模型大小**: ~6MB
- **支持类别**: 9种

### 系统性能
- **检测频率**: 1-5 FPS可调
- **响应时间**: <200ms
- **内存占用**: ~2GB
- **CPU占用**: ~30%

## 📄 许可证

本项目为教学和研究目的开发，遵循MIT许可证。

## 👨‍💻 开发团队

本项目为工程实训高级课程作业，支持团队协作开发。

---

📧 如有问题，请查看 `docs/` 目录下的详细文档或查看系统日志。 