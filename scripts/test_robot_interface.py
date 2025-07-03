#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机械臂抽象接口测试脚本
验证新的抽象接口架构是否正常工作
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.hardware.robot_arm import (
    create_robot_arm_controller,
    get_supported_arm_types,
    get_arm_type_info,
    RobotArmController,
    Position,
    JointAngles
)


def test_abstract_interface():
    """测试抽象接口架构"""
    print("🧪 机械臂抽象接口测试")
    print("=" * 60)
    
    # 1. 测试支持的机械臂类型
    print("1. 支持的机械臂类型:")
    arm_types = get_supported_arm_types()
    for arm_type in arm_types:
        info = get_arm_type_info(arm_type)
        print(f"   • {info['name']}: {info['description']}")
        print(f"     功能: {', '.join(info['features'])}")
        print(f"     需要配置: {'是' if info['config_required'] else '否'}")
        print()
    
    # 2. 测试虚拟机械臂创建
    print("2. 创建虚拟机械臂:")
    try:
        arm_controller = create_robot_arm_controller('virtual')
        print("   ✅ 虚拟机械臂创建成功")
        
        # 测试基本功能
        if arm_controller.connect():
            print("   ✅ 连接成功")
            
            # 测试状态查询
            status = arm_controller.get_status()
            print(f"   📊 状态: {status['status']}")
            print(f"   🔗 连接: {status['connected']}")
            
            # 测试配置信息
            config = arm_controller.get_configuration()
            if config:
                print(f"   ⚙️ 配置: 最大半径 {config.max_reach}mm, 负载 {config.max_payload}kg")
            
            # 测试归位
            if arm_controller.home():
                print("   ✅ 归位成功")
            
            # 测试移动
            test_position = Position(100, 200, 150)
            if arm_controller.move_to_position(test_position):
                print(f"   ✅ 移动到位置 {test_position} 成功")
            
            # 测试关节移动
            test_joints = JointAngles(10, 20, 30, 0, 0, 0)
            if arm_controller.move_to_joints(test_joints):
                print(f"   ✅ 关节移动成功")
            
            # 测试抓取
            if arm_controller.grab_object():
                print("   ✅ 抓取测试成功")
                
                # 测试释放
                if arm_controller.release_object():
                    print("   ✅ 释放测试成功")
            
            # 测试垃圾分拣（虚拟机械臂专用功能）
            if arm_controller.sort_garbage('plastic'):
                print("   ✅ 垃圾分拣测试成功")
            
            # 测试统计信息
            stats = arm_controller.get_statistics()
            print(f"   📈 操作统计: 总数 {stats['total_operations']}, 成功 {stats['successful_operations']}")
            
            # 断开连接
            if arm_controller.disconnect():
                print("   ✅ 断开连接成功")
            
        else:
            print("   ❌ 连接失败")
            
    except Exception as e:
        print(f"   ❌ 虚拟机械臂测试失败: {e}")
    
    print()
    
    # 3. 测试向后兼容性
    print("3. 向后兼容性测试:")
    try:
        # 使用原有的接口方式
        from src.hardware.robot_arm import RobotArmController
        
        old_style_arm = RobotArmController()
        if old_style_arm.connect():
            print("   ✅ 向后兼容接口工作正常")
            
            # 测试属性访问
            print(f"   📊 连接状态: {old_style_arm.is_connected}")
            print(f"   📊 机械臂状态: {old_style_arm.status}")
            print(f"   📊 抓取状态: {old_style_arm.has_object}")
            
            old_style_arm.disconnect()
        else:
            print("   ❌ 向后兼容接口连接失败")
            
    except Exception as e:
        print(f"   ❌ 向后兼容性测试失败: {e}")
    
    print()
    
    # 4. 测试类型切换
    print("4. 机械臂类型切换测试:")
    try:
        arm_controller = create_robot_arm_controller('virtual')
        arm_controller.connect()
        
        print("   🔄 当前类型: virtual")
        
        # 注意：由于没有真实的UR机械臂，这个测试会失败，但可以验证切换逻辑
        # if arm_controller.switch_arm_type('ur', {'host': '192.168.1.100'}):
        #     print("   ✅ 切换到UR机械臂成功")
        # else:
        #     print("   ⚠️ 切换到UR机械臂失败（预期结果，因为没有真实硬件）")
        
        print("   ℹ️ 类型切换功能已实现（需要真实硬件测试）")
        
        arm_controller.disconnect()
        
    except Exception as e:
        print(f"   ❌ 类型切换测试失败: {e}")
    
    print()
    
    # 5. 测试错误处理
    print("5. 错误处理测试:")
    try:
        arm_controller = create_robot_arm_controller('virtual')
        
        # 测试未连接时的操作
        if not arm_controller.move_to_position(Position(0, 0, 0)):
            print("   ✅ 未连接状态下的操作正确被拒绝")
        
        # 连接后测试
        arm_controller.connect()
        
        # 测试紧急停止
        if arm_controller.emergency_stop():
            print("   ✅ 紧急停止功能正常")
        
        # 测试错误重置
        if arm_controller.reset_errors():
            print("   ✅ 错误重置功能正常")
        
        arm_controller.disconnect()
        
    except Exception as e:
        print(f"   ❌ 错误处理测试失败: {e}")
    
    print()
    print("🏁 机械臂抽象接口测试完成")


def test_performance():
    """性能测试"""
    print("\n🚀 性能测试")
    print("=" * 60)
    
    try:
        arm_controller = create_robot_arm_controller('virtual')
        arm_controller.connect()
        
        # 测试移动性能
        print("测试移动性能...")
        positions = [
            Position(100, 100, 100),
            Position(200, 200, 200),
            Position(150, 150, 150),
            Position(50, 50, 50),
            Position(0, 0, 100)
        ]
        
        start_time = time.time()
        for i, position in enumerate(positions):
            arm_controller.move_to_position(position)
            print(f"   移动 {i+1}/5 完成")
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / len(positions)
        
        print(f"✅ 性能测试结果:")
        print(f"   总时间: {total_time:.2f}秒")
        print(f"   平均移动时间: {avg_time:.2f}秒")
        print(f"   移动频率: {1/avg_time:.2f} 次/秒")
        
        # 测试抓取性能
        print("\n测试抓取性能...")
        start_time = time.time()
        for i in range(5):
            arm_controller.grab_object()
            arm_controller.release_object()
        end_time = time.time()
        
        grab_time = (end_time - start_time) / 5
        print(f"   平均抓取-释放周期: {grab_time:.2f}秒")
        
        arm_controller.disconnect()
        
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")


def interactive_mode():
    """交互式测试模式"""
    print("\n🎮 交互式测试模式")
    print("=" * 60)
    
    try:
        arm_controller = create_robot_arm_controller('virtual')
        
        if not arm_controller.connect():
            print("❌ 连接失败")
            return
        
        print("✅ 机械臂已连接")
        print("\n可用命令:")
        print("  status   - 查看状态")
        print("  home     - 归位")
        print("  move x y z - 移动到位置")
        print("  grab     - 抓取")
        print("  release  - 释放")
        print("  sort <type> - 垃圾分拣")
        print("  stats    - 统计信息")
        print("  config   - 配置信息")
        print("  quit     - 退出")
        print()
        
        while True:
            try:
                cmd = input("🤖 > ").strip().lower()
                
                if cmd == 'quit' or cmd == 'exit':
                    break
                elif cmd == 'status':
                    status = arm_controller.get_status()
                    print(f"状态: {status['status']}")
                    print(f"连接: {status['connected']}")
                    print(f"位置: {status['current_position']}")
                    print(f"抓取: {status['has_object']}")
                    
                elif cmd == 'home':
                    if arm_controller.home():
                        print("✅ 归位成功")
                    else:
                        print("❌ 归位失败")
                        
                elif cmd.startswith('move '):
                    try:
                        parts = cmd.split()
                        x, y, z = map(float, parts[1:4])
                        position = Position(x, y, z)
                        if arm_controller.move_to_position(position):
                            print(f"✅ 移动到 {position} 成功")
                        else:
                            print("❌ 移动失败")
                    except ValueError:
                        print("❌ 格式错误，使用: move x y z")
                        
                elif cmd == 'grab':
                    if arm_controller.grab_object():
                        print("✅ 抓取成功")
                    else:
                        print("❌ 抓取失败")
                        
                elif cmd == 'release':
                    if arm_controller.release_object():
                        print("✅ 释放成功")
                    else:
                        print("❌ 释放失败")
                        
                elif cmd.startswith('sort '):
                    garbage_type = cmd.split(' ', 1)[1]
                    if arm_controller.sort_garbage(garbage_type):
                        print(f"✅ {garbage_type} 分拣成功")
                    else:
                        print(f"❌ {garbage_type} 分拣失败")
                        
                elif cmd == 'stats':
                    stats = arm_controller.get_statistics()
                    print(f"总操作: {stats['total_operations']}")
                    print(f"成功: {stats['successful_operations']}")
                    print(f"失败: {stats['failed_operations']}")
                    
                elif cmd == 'config':
                    config = arm_controller.get_configuration()
                    if config:
                        print(f"最大半径: {config.max_reach}mm")
                        print(f"最大负载: {config.max_payload}kg")
                        print(f"自由度: {config.degrees_of_freedom}")
                        print(f"精度: {config.precision}mm")
                    
                elif cmd == 'help':
                    print("可用命令: status, home, move, grab, release, sort, stats, config, quit")
                    
                else:
                    print("❓ 未知命令，输入 'help' 查看帮助")
                    
            except KeyboardInterrupt:
                print("\n👋 中断退出")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")
        
        arm_controller.disconnect()
        print("👋 再见!")
        
    except Exception as e:
        print(f"❌ 交互式测试失败: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='机械臂抽象接口测试工具')
    parser.add_argument('--performance', '-p', action='store_true', help='运行性能测试')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互式测试模式')
    
    args = parser.parse_args()
    
    # 运行基本测试
    test_abstract_interface()
    
    # 可选的性能测试
    if args.performance:
        test_performance()
    
    # 可选的交互式测试
    if args.interactive:
        interactive_mode() 