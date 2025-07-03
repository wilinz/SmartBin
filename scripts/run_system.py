#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统运行脚本
启动垃圾分拣系统的Web界面
"""

import sys
import socket
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.web_interface.app import create_app
from src.utils.config_loader import config_loader


def is_port_available(host, port):
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0
    except Exception:
        return False


def find_available_port(host, start_port, max_attempts=10):
    """查找可用端口"""
    for i in range(max_attempts):
        port = start_port + i
        if is_port_available(host, port):
            return port
    return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动垃圾分拣系统Web界面')
    parser.add_argument('--host', type=str, default=None,
                       help='服务器主机地址')
    parser.add_argument('--port', type=int, default=None,
                       help='服务器端口')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试模式')
    parser.add_argument('--no-debug', action='store_true',
                       help='禁用调试模式')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SmartBin 垃圾分拣系统")
    print("=" * 60)
    
    # 创建Flask应用
    app = create_app()
    
    # 获取配置
    web_config = config_loader.get_web_server_config()
    host = args.host or web_config.get('host', '127.0.0.1')
    requested_port = args.port or web_config.get('port', 5001)
    
    # 强制使用5001端口（或用户指定端口）
    port = requested_port
    if not is_port_available(host, port):
        print(f"⚠️  端口 {port} 被占用")
        print(f"💡 请先停止占用端口 {port} 的进程，或使用 --port 参数指定其他端口")
        print(f"   例如: python scripts/run_system.py --port {port + 1}")
        
        # 仍然尝试启动，让用户看到具体错误信息
        print(f"⚠️  仍然尝试启动在端口 {port}...")
    else:
        print(f"✅ 端口 {port} 可用")
    
    # 调试模式设置
    if args.debug:
        debug = True
    elif args.no_debug:
        debug = False
    else:
        debug = web_config.get('debug', True)
    
    print(f"服务器地址: http://{host}:{port}")
    print(f"调试模式: {'开启' if debug else '关闭'}")
    print("\n功能模块:")
    print("  • 实时垃圾检测")
    print("  • 模型训练管理")
    print("  • 系统状态监控")
    print("  • 机械臂控制")
    print("  • 数据可视化")
    
    print("\nAPI接口:")
    print(f"  • 系统状态: http://{host}:{port}/api/status")
    print(f"  • 图像检测: http://{host}:{port}/api/detect_image")
    print(f"  • 视频流: http://{host}:{port}/video_feed")
    print(f"  • 模型管理: http://{host}:{port}/api/load_model")
    
    print(f"\n🌐 前端界面: http://localhost:3000")
    print(f"   (前端会自动连接到: http://{host}:{port})")
    
    print("\n" + "=" * 60)
    print("启动Web服务器...")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True,
            use_reloader=False  # 避免重复加载
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        if "Address already in use" in str(e):
            print("💡 提示: 尝试使用不同端口，例如:")
            print(f"   python scripts/run_system.py --port {port + 1}")
        sys.exit(1)


if __name__ == "__main__":
    main() 