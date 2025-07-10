#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动Streamlit应用的脚本
"""

import subprocess
import sys
import os

def check_dependencies():
    """
    检查必要的依赖是否已安装
    """
    required_packages = ['streamlit', 'plotly', 'pandas']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def main():
    print("🚀 正在启动数据集可视化工具...")
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查数据集是否存在
    if not os.path.exists("dataset-with-label"):
        print("⚠️  警告: 没有找到dataset-with-label文件夹")
        print("请确保数据集文件夹存在于当前目录")
    
    # 启动streamlit应用
    try:
        print("🌐 启动Web应用...")
        print("应用将在浏览器中自动打开")
        print("如未自动打开，请手动访问: http://localhost:8501")
        print("\n按 Ctrl+C 停止应用")
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.headless", "false",
            "--server.port", "8501"
        ])
    except KeyboardInterrupt:
        print("\n✋ 应用已停止")
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")

if __name__ == "__main__":
    main() 