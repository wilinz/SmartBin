#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试更新后的 uArm 机械臂实现
基于 arm1.py 的可运行代码重新实现
"""

import sys
import os
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.hardware.robot_arm_uarm import UarmRobotArm
from src.hardware.robot_arm_interface import Position, JointAngles


def test_uarm_connection():
    """测试 uArm 连接"""
    print("=" * 50)
    print("🤖 测试 uArm 机械臂连接")
    print("=" * 50)
    
    # 创建机械臂实例
    config = {
        'baudrate': 115200,
        'speed_factor': 100
    }
    
    arm = UarmRobotArm(config)
    
    # 测试连接
    if arm.connect():
        print("✅ 连接成功")
        
        # 获取状态信息
        status = arm.get_status()
        print(f"📊 机械臂状态: {status}")
        
        # 测试基本功能
        test_basic_functions(arm)
        
        # 断开连接
        arm.disconnect()
        print("✅ 断开连接")
        
    else:
        print("❌ 连接失败")
        return False
    
    return True


def test_basic_functions(arm):
    """测试基本功能"""
    print("\n" + "=" * 30)
    print("🧪 测试基本功能")
    print("=" * 30)
    
    # 1. 测试复位
    print("\n1. 测试复位...")
    if arm.home():
        print("✅ 复位成功")
    else:
        print("❌ 复位失败")
    
    # 2. 测试获取当前位置
    print("\n2. 测试获取当前位置...")
    position = arm.get_current_position()
    if position:
        print(f"✅ 当前位置: x={position.x}, y={position.y}, z={position.z}")
    else:
        print("❌ 获取位置失败")
    
    # 3. 测试获取关节角度
    print("\n3. 测试获取关节角度...")
    joints = arm.get_current_joints()
    if joints:
        print(f"✅ 关节角度: {joints.to_list()}")
    else:
        print("❌ 获取关节角度失败")
    
    # 4. 测试移动到指定位置
    print("\n4. 测试移动到指定位置...")
    test_position = Position(x=200, y=0, z=100)
    if arm.move_to_position(test_position):
        print("✅ 移动成功")
        time.sleep(2)
        
        # 获取新位置
        new_position = arm.get_current_position()
        if new_position:
            print(f"✅ 新位置: x={new_position.x}, y={new_position.y}, z={new_position.z}")
    else:
        print("❌ 移动失败")
    
    # 5. 测试抓取和释放
    print("\n5. 测试抓取和释放...")
    if arm.grab_object():
        print("✅ 抓取成功")
        time.sleep(2)
        
        if arm.release_object():
            print("✅ 释放成功")
        else:
            print("❌ 释放失败")
    else:
        print("❌ 抓取失败")
    
    # 6. 测试垃圾分拣
    print("\n6. 测试垃圾分拣...")
    if arm.sort_garbage('banana'):
        print("✅ 垃圾分拣成功")
    else:
        print("❌ 垃圾分拣失败")


def test_detailed_status():
    """测试详细状态信息"""
    print("\n" + "=" * 30)
    print("📊 获取详细状态信息")
    print("=" * 30)
    
    arm = UarmRobotArm()
    
    if arm.connect():
        try:
            # 获取所有状态信息（类似 arm1.py 的演示）
            print("\n📋 uArm 设备信息:")
            print(f"电源状态: {arm.arm.get_power_status()}")
            print(f"设备信息: {arm.arm.get_device_info()}")
            print(f"吸盘限位开关: {arm.arm.get_limit_switch()}")
            print(f"电动夹状态: {arm.arm.get_gripper_catch()}")
            print(f"吸盘状态: {arm.arm.get_pump_status()}")
            print(f"模式状态: {arm.arm.get_mode()}")
            print(f"机械臂角度: {arm.arm.get_servo_angle()}")
            print(f"极坐标: {arm.arm.get_polar()}")
            print(f"xyz坐标: {arm.arm.get_position()}")
            
        except Exception as e:
            print(f"❌ 获取状态信息失败: {e}")
        finally:
            arm.disconnect()
    else:
        print("❌ 连接失败，无法获取状态信息")


def test_movement_demo():
    """测试移动演示（基于 arm1.py 的移动演示）"""
    print("\n" + "=" * 30)
    print("🎮 移动演示")
    print("=" * 30)
    
    arm = UarmRobotArm()
    
    if arm.connect():
        try:
            # 复位
            arm.home()
            
            # 设置手腕角度
            print("设置手腕角度...")
            arm.arm.set_wrist(180)
            time.sleep(1)
            arm.arm.set_wrist(90)
            
            # 蜂鸣器
            print("蜂鸣器测试...")
            arm.arm.set_buzzer(frequency=1000)
            time.sleep(0.5)
            
            # 移动演示
            print("移动演示...")
            arm.move_to_position(Position(x=200, y=0, z=100))
            time.sleep(2)
            
            # 极坐标移动
            print("极坐标移动...")
            arm.arm.set_polar(stretch=200, rotation=90, height=150)
            time.sleep(2)
            
            # 关节角度控制
            print("关节角度控制...")
            arm.arm.set_servo_angle(servo_id=0, angle=60)
            time.sleep(2)
            
            print("✅ 移动演示完成")
            
        except Exception as e:
            print(f"❌ 移动演示失败: {e}")
        finally:
            arm.disconnect()
    else:
        print("❌ 连接失败，无法进行移动演示")


if __name__ == "__main__":
    print("🚀 开始测试更新后的 uArm 机械臂实现")
    print("基于 arm1.py 的可运行代码重新实现")
    
    try:
        # 基本连接测试
        test_uarm_connection()
        
        # 详细状态测试
        test_detailed_status()
        
        # 移动演示
        test_movement_demo()
        
        print("\n🎉 所有测试完成！")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 