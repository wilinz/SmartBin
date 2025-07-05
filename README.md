# 🗑️ SmartBin 智能垃圾分拣系统

基于YOLOv8的实时垃圾识别与自动分拣系统，支持9种垃圾类别识别，配备Web界面和机械臂控制功能。

## 🌟 项目特色

- ✅ **高精度识别**: 基于YOLOv8模型，mAP@0.5达到91.1%
- ✅ **实时检测**: 支持摄像头实时检测和图像上传检测
- ✅ **前后端分离**: Next.js + Flask架构，现代化UI设计
- ✅ **机械臂控制**: 支持虚拟机械臂和真实机械臂
- ✅ **智能分拣**: 自动抓取和分类垃圾到指定位置
- ✅ **可视化监控**: 实时状态监控和操作历史记录

## 📦 支持的垃圾类别

| 类别 | 中文名称 | 英文标识 | 垃圾分类 |
|------|----------|----------|----------|
| 🍌 | 香蕉皮 | banana | 有机垃圾 |
| 🍶 | 饮料瓶 | beverages | 可回收垃圾 |
| 📦 | 纸盒 | cardboard_box | 可回收垃圾 |
| 🥔 | 薯片袋 | chips | 其他垃圾 |
| 🐟 | 鱼骨 | fish_bones | 有机垃圾 |
| 🍜 | 泡面盒 | instant_noodles | 其他垃圾 |
| 🥛 | 牛奶盒1 | milk_box_type1 | 可回收垃圾 |
| 🧈 | 牛奶盒2 | milk_box_type2 | 可回收垃圾 |
| ♻️ | 塑料 | plastic | 可回收垃圾 |

## 🚀 快速开始

💡 **2步快速启动**：安装环境 → 一键启动 (自动下载模型)

### 1. 环境要求

⚠️ **使用前请确保您的计算机已安装以下环境：**

- **Python**: 3.8+ (必须)
- **Node.js**: 18+ (必须)

### 2. 环境安装

#### 安装Python
```bash
# macOS (使用Homebrew)
brew install python

# Windows (使用Chocolatey)
choco install python

# Windows (手动安装)
# 从官网下载安装包: https://www.python.org/downloads/

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip

# 验证安装
python --version
pip --version
```

#### 安装Node.js
```bash
# macOS (使用Homebrew)
brew install nodejs

# Windows (使用Chocolatey)
choco install nodejs

# Windows (手动安装)
# 从官网下载安装包: https://nodejs.org/

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install nodejs npm

# 验证安装
node --version
npm --version
```

#### 安装Chocolatey (Windows包管理器)
如果您使用Windows且没有安装Chocolatey，请先安装：
```powershell
# 以管理员权限运行PowerShell，然后执行：
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 验证安装
choco --version
```

### 3. 项目依赖安装

```bash
# 1. 安装Python依赖
pip install -r requirements.txt

# 2. 安装前端依赖
cd web
npm install
```

### 4. 下载预训练模型

#### 自动下载 (推荐)
**一键启动脚本会自动下载模型，无需手动操作！**

```bash
# 直接运行一键启动，会自动检查并下载模型
python start.py
```

#### 单独下载 (可选)
如果需要单独下载模型，可以使用：

```bash
# 运行安装脚本
python setup.py
```

**下载功能：**
- 🚀 自动从GitHub Release下载预训练模型
- 📁 自动创建models目录
- 📥 显示下载进度
- ✅ 验证文件完整性
- 🔄 支持重新下载

#### 手动下载
如果自动下载失败，可以手动下载：

```bash
# 1. 创建models目录
mkdir -p models

# 2. 下载模型文件
# 访问: https://github.com/wilinz/SmartBin/releases/download/1.0.0/best.pt
# 将文件保存到: models/best.pt
```

### 5. 模型文件说明

#### 预训练模型位置
```
models/
├── best.pt                    # 主要模型文件 (系统会自动加载)
└── garbage_sorting_*/         # 训练历史记录文件夹
    └── weights/
        ├── best.pt           # 最佳模型
        └── last.pt           # 最新模型
```

📋 **模型说明：**
- **默认模型路径**: `models/best.pt`
- **模型类型**: YOLOv8n (轻量级版本)
- **模型大小**: ~6MB
- **训练精度**: mAP@0.5 = 91.1%
- **支持类别**: 9种垃圾分类

#### 原始数据集转换 (可选)
如果您有原始数据集需要转换，请按以下步骤操作：

1. **准备原始数据**
   ```
   data/
   ├── banana/              # 香蕉皮图片
   ├── beverages/           # 饮料瓶图片
   ├── cardboard_box/       # 纸盒图片
   ├── chips/               # 薯片袋图片
   ├── fish_bones/          # 鱼骨图片
   ├── instant_noodles/     # 泡面盒图片
   ├── milk_box_type1/      # 牛奶盒1图片
   ├── milk_box_type2/      # 牛奶盒2图片
   └── plastic/             # 塑料图片
   ```

2. **转换数据集格式**
   ```bash
   # 运行数据预处理脚本
   python scripts/prepare_data.py
   ```

3. **转换后的数据结构**
   ```
   datasets/
   ├── converted/           # 转换后的数据
   │   ├── images/         # 所有图片
   │   └── labels/         # 对应的标签文件
   └── yolo_dataset/       # YOLO格式数据集
       ├── dataset.yaml    # 数据集配置
       ├── train/          # 训练集 (70%)
       ├── val/            # 验证集 (20%)
       └── test/           # 测试集 (10%)
   ```

4. **重新训练模型 (可选)**
   ```bash
   # 如果需要重新训练模型
   python scripts/train_model.py
   ```

💡 **注意事项：**
- 使用 `python start.py` 一键启动会自动下载预训练模型
- 系统会自动加载 `models/best.pt` 文件
- 首次启动需要下载约6MB的模型文件，请确保网络畅通
- 只有在需要自定义数据集或改进模型时才需要数据转换
- 原始数据集转换主要用于开发和实验目的

### 6. 启动系统

#### 方法一：一键启动 (推荐)
```bash
# 一键启动前端和后端服务
python start.py
```

**一键启动功能：**
- 📦 自动下载预训练模型 (如果不存在)
- 🚀 自动启动后端服务 (端口5001)
- 🌐 自动启动前端服务 (端口3000)
- 📋 显示启动状态和访问地址
- 🔍 检查依赖和模型文件
- ⏹️ 按Ctrl+C优雅停止所有服务

#### 方法二：分别启动
```bash
# 1. 启动后端 (第一个终端)
python scripts/run_system.py

# 2. 启动前端 (第二个终端)
cd web
npm run dev
```

### 7. 访问系统

- **前端界面**: http://localhost:3000

## 🎯 完整启动流程

```bash
# 1. 安装依赖
pip install -r requirements.txt
cd web && npm install && cd ..

# 2. 一键启动 (自动下载模型)
python start.py

# 3. 浏览器访问 http://localhost:3000
```

🎉 **就这么简单！** 启动脚本会自动下载模型并启动系统。

## 🎮 使用指南

### 基本操作

1. **开始检测**
   - 打开浏览器访问 http://localhost:3000
   - 点击"📥 加载检测模型"按钮
   - 系统会自动加载默认模型

2. **图像检测**
   - 点击"📁 选择图像文件"
   - 上传JPG/PNG图像
   - 点击"🔍 开始检测"查看结果

3. **实时检测**
   - 点击"📹 开始实时检测"
   - 授权摄像头权限
   - 系统会自动检测并分拣垃圾

4. **机械臂控制**
   - 默认使用虚拟机械臂
   - 可以查看分拣状态和历史记录
   - 支持手动控制和测试

### 系统状态

- **🤖 检测模型**: 显示模型加载状态
- **🦾 机械臂**: 显示机械臂连接状态
- **🔍 实时检测**: 显示检测服务状态
- **✅ 系统就绪**: 显示整体系统状态

## 🔧 配置说明

### 模型配置
- 默认模型路径: `models/best.pt`
- 可在 `config/model_config.yaml` 中修改配置
- 支持自定义模型路径

### 硬件配置
- 摄像头: 默认使用设备ID 0
- 机械臂: 默认使用虚拟机械臂
- 可在 `config/hardware_config.yaml` 中修改

## 🐛 常见问题

1. **一键启动失败**
   - 检查是否在项目根目录: `ls setup.py start.py`
   - 确认已安装依赖: `pip install -r requirements.txt`
   - 检查网络连接 (模型文件需要从GitHub下载)
   - 查看详细错误信息

2. **前端无法启动**
   - 检查Node.js版本: `node --version`
   - 重新安装依赖: `npm install`
   - 尝试不同端口: `npm run dev -- --port 3001`

3. **后端无法启动**
   - 检查Python版本: `python --version`
   - 重新安装依赖: `pip install -r requirements.txt`
   - 检查端口占用: `lsof -i :5001`

4. **摄像头无法访问**
   - 检查摄像头权限
   - 确认摄像头未被其他应用占用
   - 使用HTTPS访问

5. **模型加载失败**
   - 检查模型文件是否存在
   - 查看日志: `logs/web_app.log`
   - 确认内存足够

## 📁 项目结构

```
smartbin/
├── config/                     # 配置文件
├── src/                        # 后端源码
│   ├── models/                 # 模型相关
│   ├── hardware/               # 硬件控制
│   └── web_interface/          # Flask应用
├── web/                        # 前端源码
├── models/                     # 训练好的模型
├── scripts/                    # 工具脚本
├── logs/                       # 系统日志
├── setup.py                    # 模型下载脚本
├── start.py                    # 一键启动脚本
└── requirements.txt            # Python依赖
```

## 🏆 性能指标

- **准确率**: mAP@0.5 = 91.1%
- **推理时间**: <100ms
- **检测频率**: 1-5 FPS
- **模型大小**: ~6MB

## 📄 许可证

本项目遵循MIT许可证，用于教学和研究目的。

---

💡 **提示**: 如遇问题，请查看 `logs/` 目录下的日志文件获取详细信息。 