#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartBin 智能垃圾分拣系统 - 一键启动脚本
自动检查依赖、下载模型、启动前后端服务
"""

import os
import sys
import time
import signal
import subprocess
import threading
import urllib.request
import urllib.error
from pathlib import Path
import importlib.util

# 服务配置
BACKEND_SCRIPT = "scripts/run_system.py"
FRONTEND_DIR = "web"
FRONTEND_SCRIPT = "npm run dev"

# 模型文件配置
MODEL_URL = "https://github.com/wilinz/SmartBin/releases/download/1.0.0/best.pt"
MODEL_DIR = "models"
MODEL_FILE = "best.pt"
MODEL_PATH = Path(MODEL_DIR) / MODEL_FILE
EXPECTED_SIZE = 6 * 1024 * 1024  # 6MB

# 全局进程变量
backend_process = None
frontend_process = None
shutdown_event = threading.Event()

def print_banner():
    """显示启动横幅"""
    print("=" * 60)
    print("🗑️  SmartBin 智能垃圾分拣系统 - 一键启动")
    print("=" * 60)
    print("🚀 正在启动前端和后端服务...")
    print()

def create_model_directory():
    """创建模型目录"""
    model_dir = Path(MODEL_DIR)
    model_dir.mkdir(exist_ok=True)
    print(f"📁 模型目录已创建: {model_dir.absolute()}")

def download_progress_hook(block_num, block_size, total_size):
    """下载进度回调函数"""
    if total_size > 0:
        percent = min(100, (block_num * block_size * 100) // total_size)
        downloaded = min(block_num * block_size, total_size)
        print(f"\r📥 下载进度: {percent:3d}% ({downloaded:,} / {total_size:,} bytes)", end='', flush=True)

def check_python_dependencies():
    """检查Python依赖是否已安装"""
    print("🔍 检查Python依赖...")
    
    # 检查关键依赖
    required_packages = [
        ('flask', 'Flask'),
        ('ultralytics', 'ultralytics'),
        ('cv2', 'opencv-python'),
        ('torch', 'torch'),
        ('numpy', 'numpy'),
        ('PIL', 'Pillow')
    ]
    
    missing_packages = []
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ 缺少以下Python包: {', '.join(missing_packages)}")
        print("📦 正在安装Python依赖...")
        
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Python依赖安装成功")
                return True
            else:
                print(f"❌ Python依赖安装失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 安装Python依赖时出错: {e}")
            return False
    else:
        print("✅ Python依赖已安装")
        return True

def check_node_dependencies():
    """检查Node.js依赖是否已安装"""
    print("🔍 检查Node.js依赖...")
    
    web_dir = Path("web")
    node_modules = web_dir / "node_modules"
    
    if not node_modules.exists():
        print("❌ Node.js依赖未安装")
        print("📦 正在安装Node.js依赖...")
        
        try:
            result = subprocess.run([
                'npm', 'install'
            ], cwd=web_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Node.js依赖安装成功")
                return True
            else:
                print(f"❌ Node.js依赖安装失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 安装Node.js依赖时出错: {e}")
            return False
    else:
        print("✅ Node.js依赖已安装")
        return True

def download_model():
    """下载预训练模型"""
    model_path = Path("models/best.pt")
    
    if model_path.exists():
        print("✅ 模型文件已存在")
        return True
    
    print("📥 正在下载预训练模型...")
    try:
        result = subprocess.run([sys.executable, "setup.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 模型下载成功")
            return True
        else:
            print(f"❌ 模型下载失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 下载模型时出错: {e}")
        return False

def stream_output(process, prefix):
    """实时输出进程日志"""
    while not shutdown_event.is_set():
        try:
            line = process.stdout.readline()
            if line:
                print(f"[{prefix}] {line.strip()}")
            elif process.poll() is not None:
                break
        except Exception as e:
            if not shutdown_event.is_set():
                print(f"[{prefix}] 日志读取错误: {e}")
            break

def start_backend():
    """启动后端服务"""
    global backend_process
    
    print("🚀 启动后端服务...")
    try:
        backend_process = subprocess.Popen(
            [sys.executable, "scripts/run_system.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # 启动日志监控线程
        backend_thread = threading.Thread(
            target=stream_output,
            args=(backend_process, "后端"),
            daemon=True
        )
        backend_thread.start()
        
        return True
    except Exception as e:
        print(f"❌ 启动后端服务失败: {e}")
        return False

def start_frontend():
    """启动前端服务"""
    global frontend_process
    
    print("🌐 启动前端服务...")
    try:
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd="web",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # 启动日志监控线程
        frontend_thread = threading.Thread(
            target=stream_output,
            args=(frontend_process, "前端"),
            daemon=True
        )
        frontend_thread.start()
        
        return True
    except Exception as e:
        print(f"❌ 启动前端服务失败: {e}")
        return False

def signal_handler(signum, frame):
    """处理Ctrl+C信号"""
    print("\n🛑 收到停止信号，正在关闭服务...")
    shutdown_event.set()
    stop_services()
    sys.exit(0)

def stop_services():
    """停止所有服务"""
    global frontend_process, backend_process
    
    if backend_process and backend_process.poll() is None:
        print("🔧 正在停止后端服务...")
        try:
            backend_process.terminate()
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()
        except Exception as e:
            print(f"停止后端服务时出错: {e}")
    
    if frontend_process and frontend_process.poll() is None:
        print("🌐 正在停止前端服务...")
        try:
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_process.kill()
        except Exception as e:
            print(f"停止前端服务时出错: {e}")
    
    print("✅ 所有服务已停止")

def main():
    """主函数"""
    print("🎯 SmartBin智能垃圾分拣系统启动器")
    print("=" * 50)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 1. 检查Python依赖
    if not check_python_dependencies():
        print("❌ Python依赖检查失败，请手动安装: pip install -r requirements.txt")
        return False
    
    # 2. 检查Node.js依赖
    if not check_node_dependencies():
        print("❌ Node.js依赖检查失败，请手动安装: cd web && npm install")
        return False
    
    # 3. 下载模型
    if not download_model():
        print("❌ 模型下载失败，请手动运行: python setup.py")
        return False
    
    # 4. 启动后端服务
    if not start_backend():
        print("❌ 后端服务启动失败")
        return False
    
    # 5. 启动前端服务
    if not start_frontend():
        print("❌ 前端服务启动失败")
        stop_services()
        return False
    
    print("\n✅ 系统启动成功！")
    print("📱 前端界面: http://localhost:3000")
    print("🔧 后端API: http://localhost:5001")
    print("⚡ 按 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 6. 等待服务启动
    print("⏳ 等待服务完全启动...")
    time.sleep(15)
    
    # 7. 监控服务状态
    try:
        while not shutdown_event.is_set():
            # 检查后端服务状态
            if backend_process and backend_process.poll() is not None:
                exit_code = backend_process.returncode
                if exit_code != 0:
                    print(f"❌ 后端服务启动失败 (退出码: {exit_code})")
                    stop_services()
                    return False
            
            # 检查前端服务状态
            if frontend_process and frontend_process.poll() is not None:
                exit_code = frontend_process.returncode
                if exit_code != 0:
                    print(f"❌ 前端服务启动失败 (退出码: {exit_code})")
                    stop_services()
                    return False
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        pass
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 