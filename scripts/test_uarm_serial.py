#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试基于串口通信的 uArm 机械臂实现
基于 uarm_demo/uarm_demo.py 的可运行代码重新实现
"""

import sys
import os
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.hardware.robot_arm_uarm import UarmRobotArm
from src.hardware.robot_arm_interface import Position, JointAngles


def test_serial_connection():
    """测试串口连接"""
    print("=" * 50)
    print("🤖 测试 uArm 机械臂串口连接")
    print("=" * 50)
    
    # 创建机械臂实例
    config = {
        'baudrate': 115200,
        'timeout': 1
    }
    
    arm = UarmRobotArm(config)
    
    # 测试连接
    if arm.connect():
        print("✅ 串口连接成功")
        
        # 获取状态信息
        status = arm.get_status()
        print(f"📊 机械臂状态: {status}")
        
        # 测试基本功能
        test_basic_functions(arm)
        
        # 断开连接
        arm.disconnect()
        print("✅ 断开连接")
        
    else:
        print("❌ 串口连接失败")
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
    
    # 3. 测试移动到指定位置
    print("\n3. 测试移动到指定位置...")
    test_position = Position(x=150, y=0, z=100)
    if arm.move_to_position(test_position):
        print("✅ 移动成功")
        time.sleep(2)
        
        # 获取新位置
        new_position = arm.get_current_position()
        if new_position:
            print(f"✅ 新位置: x={new_position.x}, y={new_position.y}, z={new_position.z}")
    else:
        print("❌ 移动失败")
    
    # 4. 测试抓取和释放
    print("\n4. 测试抓取和释放...")
    if arm.grab_object():
        print("✅ 抓取成功")
        time.sleep(2)
        
        if arm.release_object():
            print("✅ 释放成功")
        else:
            print("❌ 释放失败")
    else:
        print("❌ 抓取失败")
    
    # 5. 测试垃圾分拣
    print("\n5. 测试垃圾分拣...")
    if arm.sort_garbage('banana'):
        print("✅ 垃圾分拣成功")
    else:
        print("❌ 垃圾分拣失败")


def test_gcode_commands():
    """测试G-code命令发送"""
    print("\n" + "=" * 30)
    print("📤 测试G-code命令发送")
    print("=" * 30)
    
    arm = UarmRobotArm()
    
    if arm.connect():
        try:
            # 测试基本G-code命令
            print("\n测试基本G-code命令:")
            
            # 1. 移动命令
            print("1. 发送移动命令...")
            arm.send_command("G0 X150 Y0 Z90 F1000")
            time.sleep(2)
            
            # 2. 机械爪控制
            print("2. 测试机械爪控制...")
            arm.send_command("M2232 V1")  # 关闭
            time.sleep(1)
            arm.send_command("M2232 V0")  # 打开
            
            # 3. 手腕角度控制
            print("3. 测试手腕角度控制...")
            arm.send_command("M2231 V0")
            time.sleep(1)
            
            print("✅ G-code命令测试完成")
            
        except Exception as e:
            print(f"❌ G-code命令测试失败: {e}")
        finally:
            arm.disconnect()
    else:
        print("❌ 连接失败，无法测试G-code命令")


def test_pick_and_place():
    """测试完整的拾取和放置流程"""
    print("\n" + "=" * 30)
    print("🤖 测试完整拾取和放置流程")
    print("=" * 30)
    
    arm = UarmRobotArm()
    
    if arm.connect():
        try:
            # 测试拾取物体功能
            print("测试拾取物体功能...")
            
            # 模拟物体位置和类别
            x, y = 100, 50  # 物体位置
            class_id = 0    # 香蕉类别
            
            if arm.pick_object(x, y, class_id):
                print("✅ 拾取和放置流程成功")
            else:
                print("❌ 拾取和放置流程失败")
                
        except Exception as e:
            print(f"❌ 拾取和放置流程测试失败: {e}")
        finally:
            arm.disconnect()
    else:
        print("❌ 连接失败，无法测试拾取和放置流程")


def test_classification_positions():
    """测试分类位置计算"""
    print("\n" + "=" * 30)
    print("📍 测试分类位置计算")
    print("=" * 30)
    
    arm = UarmRobotArm()
    
    # 测试不同类别的位置计算
    test_cases = [
        (0, "banana"),
        (1, "beverages"),
        (2, "cardboard_box"),
        (3, "chips"),
        (4, "fish_bones"),
        (5, "instant_noodles"),
        (6, "milk_box_type1"),
        (7, "milk_box_type2"),
        (8, "plastic")
    ]
    
    print("类别ID -> 分类位置:")
    for class_id, class_name in test_cases:
        position = arm.get_classification_position(class_id)
        print(f"  {class_id} ({class_name}): ({position[0]}, {position[1]})")
    
    print("✅ 分类位置计算测试完成")


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 30)
    print("⚠️ 测试错误处理")
    print("=" * 30)
    
    arm = UarmRobotArm()
    
    # 测试未连接状态下的操作
    print("1. 测试未连接状态下的操作...")
    if not arm.move_to_position(Position(x=100, y=0, z=50)):
        print("✅ 未连接状态正确处理")
    
    # 测试不支持的垃圾类型
    print("2. 测试不支持的垃圾类型...")
    if arm.connect():
        if not arm.sort_garbage('unknown_type'):
            print("✅ 不支持的垃圾类型正确处理")
        arm.disconnect()
    
    print("✅ 错误处理测试完成")


if __name__ == "__main__":
    print("🚀 开始测试基于串口通信的 uArm 机械臂实现")
    print("基于 uarm_demo/uarm_demo.py 的可运行代码重新实现")
    
    try:
        # 基本连接测试
        test_serial_connection()
        
        # G-code命令测试
        test_gcode_commands()
        
        # 完整拾取和放置流程测试
        test_pick_and_place()
        
        # 分类位置计算测试
        test_classification_positions()
        
        # 错误处理测试
        test_error_handling()
        
        print("\n🎉 所有测试完成！")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 