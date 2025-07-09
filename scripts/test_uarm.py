#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uArm 机械臂测试脚本
测试 uArm 机械臂的基本功能和垃圾分拣能力
"""

import sys
import os
import time
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.hardware.robot_arm import RobotArmController
from src.hardware.robot_arm_interface import Position, JointAngles

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_uarm_basic():
    """测试 uArm 机械臂基本功能"""
    logger.info("=" * 50)
    logger.info("开始测试 uArm 机械臂基本功能")
    logger.info("=" * 50)
    
    # 创建机械臂控制器
    config = {
        'arm_type': 'uarm',
        'port': None,  # 自动检测端口
        'baudrate': 115200,
        'speed_factor': 100
    }
    
    try:
        # 初始化机械臂
        logger.info("📦 初始化 uArm 机械臂...")
        arm = RobotArmController(config)
        
        # 连接机械臂
        logger.info("🔌 连接 uArm 机械臂...")
        if not arm.connect():
            logger.error("❌ 连接失败！请检查:")
            logger.error("  1. uArm 机械臂是否正确连接")
            logger.error("  2. 串口权限是否正确")
            logger.error("  3. uarm_demo 库是否可用")
            return False
        
        logger.info("✅ 连接成功！")
        
        # 获取机械臂状态
        logger.info("📊 获取机械臂状态...")
        status = arm.get_status()
        logger.info(f"状态: {status}")
        
        # 获取当前位置
        logger.info("📍 获取当前位置...")
        position = arm.current_position
        logger.info(f"当前位置: {position}")
        
        # 机械臂归位
        logger.info("🏠 机械臂归位...")
        if arm.home():
            logger.info("✅ 归位成功")
        else:
            logger.error("❌ 归位失败")
            return False
        
        # 测试移动到指定位置
        logger.info("🚀 测试移动到指定位置...")
        test_position = Position(x=200, y=0, z=100)
        if arm.move_to_position(test_position):
            logger.info(f"✅ 移动成功到: {test_position}")
        else:
            logger.error("❌ 移动失败")
            return False
        
        # 测试抓取和释放
        logger.info("🤏 测试抓取功能...")
        if arm.grab_object():
            logger.info("✅ 抓取成功")
            
            # 等待一会儿
            time.sleep(2)
            
            logger.info("🤲 测试释放功能...")
            if arm.release_object():
                logger.info("✅ 释放成功")
            else:
                logger.error("❌ 释放失败")
        else:
            logger.warning("⚠️ 抓取失败（可能没有物体）")
        
        # 测试关节运动
        logger.info("🔄 测试关节运动...")
        test_joints = JointAngles(j1=90, j2=90, j3=90, j4=0, j5=0, j6=0)
        if arm.move_to_joints(test_joints):
            logger.info("✅ 关节运动成功")
        else:
            logger.error("❌ 关节运动失败")
        
        # 再次归位
        logger.info("🏠 最终归位...")
        arm.home()
        
        logger.info("✅ uArm 机械臂基本功能测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        return False
    finally:
        # 断开连接
        if 'arm' in locals():
            arm.disconnect()


def test_uarm_garbage_sorting():
    """测试 uArm 机械臂垃圾分拣功能"""
    logger.info("=" * 50)
    logger.info("开始测试 uArm 机械臂垃圾分拣功能")
    logger.info("=" * 50)
    
    # 创建机械臂控制器
    config = {
        'arm_type': 'uarm',
        'port': None,  # 自动检测端口
        'baudrate': 115200,
        'speed_factor': 80
    }
    
    try:
        # 初始化机械臂
        logger.info("📦 初始化 uArm 机械臂...")
        arm = RobotArmController(config)
        
        # 连接机械臂
        logger.info("🔌 连接 uArm 机械臂...")
        if not arm.connect():
            logger.error("❌ 连接失败！")
            return False
        
        logger.info("✅ 连接成功！")
        
        # 机械臂归位
        logger.info("🏠 机械臂归位...")
        arm.home()
        
        # 测试垃圾分拣
        garbage_types = [
            'banana',        # 香蕉皮
            'beverages',     # 饮料瓶
            'cardboard_box', # 纸盒
            'chips',         # 薯片袋
            'plastic'        # 塑料
        ]
        
        logger.info("🗑️ 开始测试垃圾分拣...")
        for i, garbage_type in enumerate(garbage_types, 1):
            logger.info(f"📦 测试分拣 {i}/{len(garbage_types)}: {garbage_type}")
            
            # 模拟抓取垃圾
            logger.info("  🤏 模拟抓取垃圾...")
            arm.grab_object()
            
            # 分拣垃圾
            logger.info(f"  🗑️ 分拣垃圾到对应垃圾桶...")
            if arm.sort_garbage(garbage_type):
                logger.info(f"  ✅ {garbage_type} 分拣成功")
            else:
                logger.error(f"  ❌ {garbage_type} 分拣失败")
            
            # 短暂休息
            time.sleep(1)
        
        # 归位
        logger.info("🏠 最终归位...")
        arm.home()
        
        logger.info("✅ uArm 机械臂垃圾分拣测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        return False
    finally:
        # 断开连接
        if 'arm' in locals():
            arm.disconnect()


def test_virtual_arm():
    """测试虚拟机械臂功能"""
    logger.info("=" * 50)
    logger.info("开始测试虚拟机械臂功能")
    logger.info("=" * 50)
    
    # 创建虚拟机械臂控制器
    config = {'arm_type': 'virtual'}
    
    try:
        # 初始化虚拟机械臂
        logger.info("📦 初始化虚拟机械臂...")
        arm = RobotArmController(config)
        
        # 连接机械臂
        logger.info("🔌 连接虚拟机械臂...")
        if not arm.connect():
            logger.error("❌ 连接失败！")
            return False
        
        logger.info("✅ 连接成功！")
        
        # 获取机械臂状态
        status = arm.get_status()
        logger.info(f"虚拟机械臂状态: {status}")
        
        # 测试垃圾分拣
        logger.info("🗑️ 测试虚拟垃圾分拣...")
        if arm.sort_garbage('banana'):
            logger.info("✅ 虚拟垃圾分拣成功")
        else:
            logger.error("❌ 虚拟垃圾分拣失败")
        
        # 获取统计信息
        if hasattr(arm, 'get_statistics'):
            stats = arm.get_statistics()
            logger.info(f"统计信息: {stats}")
        
        logger.info("✅ 虚拟机械臂测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        return False
    finally:
        # 断开连接
        if 'arm' in locals():
            arm.disconnect()


def main():
    """主函数"""
    logger.info("🚀 开始 uArm 机械臂测试程序")
    
    # 显示选择菜单
    print("\n请选择测试模式:")
    print("1. 测试 uArm 机械臂基本功能")
    print("2. 测试 uArm 机械臂垃圾分拣功能")
    print("3. 测试虚拟机械臂功能")
    print("4. 运行所有测试")
    print("0. 退出")
    
    choice = input("\n请输入选择 (0-4): ").strip()
    
    try:
        if choice == '1':
            success = test_uarm_basic()
        elif choice == '2':
            success = test_uarm_garbage_sorting()
        elif choice == '3':
            success = test_virtual_arm()
        elif choice == '4':
            logger.info("🔄 运行所有测试...")
            success1 = test_virtual_arm()
            success2 = test_uarm_basic()
            success3 = test_uarm_garbage_sorting()
            success = success1 and success2 and success3
        elif choice == '0':
            logger.info("👋 退出测试程序")
            return
        else:
            logger.error("❌ 无效的选择")
            return
        
        if success:
            logger.info("🎉 所有测试通过！")
        else:
            logger.error("❌ 部分测试失败")
            
    except KeyboardInterrupt:
        logger.info("\n⏹️ 用户中断测试")
    except Exception as e:
        logger.error(f"❌ 程序执行错误: {e}")


if __name__ == "__main__":
    main() 