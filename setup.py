#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartBin 智能垃圾分拣系统 - 安装脚本
自动下载预训练模型文件到指定目录
"""

import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
import hashlib

# 模型文件配置
MODEL_URL = "https://github.com/wilinz/SmartBin/releases/download/1.0.0/best.pt"
MODEL_DIR = "models"
MODEL_FILE = "best.pt"
MODEL_PATH = Path(MODEL_DIR) / MODEL_FILE

# 预期文件大小 (约6MB)
EXPECTED_SIZE = 6 * 1024 * 1024  # 6MB

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

def download_model():
    """下载预训练模型文件"""
    try:
        print(f"🚀 开始下载预训练模型...")
        print(f"📍 下载地址: {MODEL_URL}")
        print(f"💾 保存位置: {MODEL_PATH.absolute()}")
        
        # 下载文件
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH, download_progress_hook)
        print()  # 换行
        
        # 检查文件大小
        file_size = MODEL_PATH.stat().st_size
        print(f"✅ 下载完成! 文件大小: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
        
        # 验证文件大小是否合理
        if file_size < EXPECTED_SIZE * 0.5:  # 如果小于预期大小的50%
            print(f"⚠️  警告: 文件大小异常，可能下载不完整")
            return False
        
        return True
        
    except urllib.error.URLError as e:
        print(f"❌ 网络错误: {e}")
        print("💡 请检查网络连接或稍后重试")
        return False
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP错误: {e}")
        print("💡 请检查下载地址是否正确")
        return False
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False

def verify_model():
    """验证模型文件"""
    if not MODEL_PATH.exists():
        return False
    
    file_size = MODEL_PATH.stat().st_size
    if file_size == 0:
        print("❌ 模型文件为空")
        return False
    
    print(f"✅ 模型文件验证通过: {file_size:,} bytes")
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("🗑️  SmartBin 智能垃圾分拣系统 - 模型安装")
    print("=" * 60)
    
    # 检查是否已存在模型文件
    if MODEL_PATH.exists():
        file_size = MODEL_PATH.stat().st_size
        print(f"📋 发现已存在的模型文件: {MODEL_PATH}")
        print(f"📏 文件大小: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
        
        # 询问是否重新下载
        while True:
            choice = input("❓ 是否重新下载模型文件? (y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                print("🔄 将重新下载模型文件...")
                break
            elif choice in ['n', 'no', '否']:
                print("✅ 使用现有模型文件")
                print("🎉 安装完成!")
                return
            else:
                print("❌ 请输入 y 或 n")
    
    # 创建模型目录
    create_model_directory()
    
    # 下载模型文件
    if download_model():
        if verify_model():
            print("🎉 模型文件下载并验证成功!")
            print()
            print("📋 安装完成! 现在可以启动系统:")
            print("   1. 启动后端: python scripts/run_system.py")
            print("   2. 启动前端: cd web && npm run dev")
            print("   3. 访问界面: http://localhost:3000")
        else:
            print("❌ 模型文件验证失败，请重新运行安装脚本")
            sys.exit(1)
    else:
        print("❌ 模型文件下载失败")
        print("💡 您可以手动下载模型文件:")
        print(f"   1. 访问: {MODEL_URL}")
        print(f"   2. 下载文件并保存到: {MODEL_PATH.absolute()}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ 安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 安装过程中发生错误: {e}")
        sys.exit(1) 