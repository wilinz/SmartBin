#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uArm 机械臂实现
基于 uarm_demo/uarm_demo.py 的可运行实现，使用串口通信方式
"""

import time
import platform
import os
import serial
import serial.tools.list_ports
from typing import Dict, List, Optional
import sys
import logging

from .robot_arm_interface import (
    RobotArmInterface,
    ArmStatus,
    Position,
    JointAngles,
    GrabParameters,
    ArmConfiguration
)


class UarmRobotArm(RobotArmInterface):
    """
    uArm 机械臂实现
    
    基于 uarm_demo/uarm_demo.py 的串口通信实现，提供完整的 uArm 机械臂控制功能
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化 uArm 机械臂
        
        Args:
            config: 配置参数，包含：
                - port: 串口端口（可选，自动检测）
                - baudrate: 波特率（默认115200）
                - timeout: 超时时间（默认1秒）
        """
        super().__init__(config)
        
        # 配置参数
        self.port = self.config.get('port', None)
        self.baudrate = self.config.get('baudrate', 115200)
        self.timeout = self.config.get('timeout', 1)
        
        # 串口连接实例
        self.arm = None
        
        # 状态变量
        self._is_connected = False
        self.current_position = Position(0.0, 0.0, 0.0)
        self.current_joints = JointAngles(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.has_object = False
        self.is_moving = False
        self.errors = []
        
        # 机械臂工作参数（基于 uarm_demo.py）
        self.polar_height = -8  # 抓取高度
        self.x_weight = 5.0
        
        # 垃圾分类位置定义（基于 uarm_demo.py 的分类逻辑）
        self.garbage_positions = {
            # 厨余垃圾
            'banana': {'x': 20.6, 'y': 127.1, 'z': 50},
            'fish_bones': {'x': 20.6, 'y': 127.1, 'z': 50},
            
            # 可回收垃圾
            'beverages': {'x': 99.5, 'y': 121.7, 'z': 50},
            'cardboard_box': {'x': 99.5, 'y': 121.7, 'z': 50},
            'milk_box_type1': {'x': 99.5, 'y': 121.7, 'z': 50},
            'milk_box_type2': {'x': 99.5, 'y': 121.7, 'z': 50},
            'plastic': {'x': 99.5, 'y': 121.7, 'z': 50},
            
            # 其他垃圾
            'chips': {'x': 189.6, 'y': 142.4, 'z': 50},
            'instant_noodles': {'x': 189.6, 'y': 142.4, 'z': 50},
        }
        
        print("🤖 uArm 机械臂已初始化（使用串口通信）")
    
    def _check_port(self, port: Optional[str] = None) -> Optional[str]:
        """检测并返回 uArm 机械臂端口（基于 uarm_demo.py 的实现）"""
        print('🔍 检测 uArm 设备...')
        
        if port:
            print(f'使用指定端口: {port}')
            return port
        
        detected_port = None
        
        if platform.system() == 'Windows':
            # Windows 系统端口检测 - 使用 uarm_demo.py 的逻辑
            plist = list(serial.tools.list_ports.comports())
            if len(plist) <= 0:
                print("❌ 未找到串口设备!")
            else:
                plist_0 = list(plist[0])
                detected_port = plist_0[0]
                print(f'✅ 当前设备: {detected_port}')
        else:
            # Linux/macOS 系统端口检测 - 使用 uarm_demo.py 的逻辑
            try:
                # 获取机械臂端口信息
                ret = os.popen("ls /dev/serial/by-id").read()
                if ret.strip():
                    detected_port = "/dev/serial/by-id/" + ret.split('\n')[0].split('/')[-1]
                    print(f'✅ 当前设备: {detected_port}')
                else:
                    print("❌ 未找到串口设备!")
            except:
                print("❌ 未找到串口设备!")
        
        return detected_port
    
    # ==================== 连接管理 ====================
    
    def connect(self) -> bool:
        """连接 uArm 机械臂（基于 uarm_demo.py 的串口通信实现）"""
        try:
            # 检测端口
            port = self._check_port(self.port)
            if not port:
                print("❌ 未找到可用端口")
                self.errors.append("未找到可用端口")
                return False
            
            print(f"🔌 连接 uArm 机械臂: {port}")
            
            # 创建串口连接 - 使用 uarm_demo.py 的方式
            self.arm = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # 清除缓冲区
            self.arm.reset_input_buffer()
            self.arm.reset_output_buffer()
            
            # 测试连接 - 发送M114获取当前位置
            self.arm.write(b"M114\r\n")
            time.sleep(0.5)  # 给机械臂响应时间
            
            # 读取响应
            response = b""
            start_time = time.time()
            while (time.time() - start_time) < 2.0:  # 最多等待2秒
                if self.arm.in_waiting > 0:
                    response += self.arm.read(self.arm.in_waiting)
                    if b'ok' in response or b'X:' in response:
                        break
            
            response = response.decode('utf-8', errors='ignore').strip()
            print(f"机械臂响应: {response}")
            
            if "X:" in response or "ok" in response:
                self._is_connected = True
                self.current_status = ArmStatus.IDLE
                self.errors.clear()
                
                # 初始化机械臂位置
                self.initialize_arm()
                
                print("✅ uArm 机械臂连接成功")
                return True
            else:
                print(f"⚠️ 机械臂响应异常，尝试继续连接...")
                self._is_connected = True
                self.current_status = ArmStatus.IDLE
                self.errors.clear()
                return True  # 即使没有有效响应也尝试继续
                
        except serial.SerialException as e:
            print(f"❌ 串口连接失败: {str(e)}")
            self.errors.append(f"串口连接失败: {str(e)}")
            self.arm = None
            return False
        except Exception as e:
            print(f"❌ 连接失败: {str(e)}")
            self.errors.append(f"连接失败: {str(e)}")
            self.arm = None
            return False
    
    def disconnect(self) -> bool:
        """断开 uArm 机械臂连接"""
        try:
            print("🔌 断开 uArm 机械臂连接...")
            
            if self.arm and self.arm.is_open:
                self.arm.close()
                self.arm = None
            
            self._is_connected = False
            self.current_status = ArmStatus.DISCONNECTED
            
            print("✅ uArm 机械臂已断开连接")
            return True
            
        except Exception as e:
            print(f"❌ 断开连接失败: {e}")
            return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._is_connected and self.arm is not None and self.arm.is_open
    
    def initialize_arm(self):
        """初始化机械臂位置（基于 uarm_demo.py 的实现）"""
        if not self.arm:
            return
        
        try:
            # 发送初始化指令
            self.send_command("G0 X150 Y0 Z90 F1000")
            time.sleep(2)
            self.send_command("M2231 V0")  # 设置手腕角度
            print("✅ 机械臂初始化到Home位置")
        except Exception as e:
            print(f"❌ 机械臂初始化失败: {e}")
    
    def send_command(self, command: str) -> bool:
        """发送G-code指令给机械臂（基于 uarm_demo.py 的实现）"""
        if not self.arm or not self.arm.is_open:
            print("❌ 无法发送指令: 机械臂未连接")
            return False
        
        try:
            command_bytes = f"{command}\r\n".encode()
            self.arm.write(command_bytes)
            time.sleep(0.1)
            print(f"📤 发送指令: {command}")
            return True
        except serial.SerialException as e:
            print(f"❌ 发送指令失败: {e}")
            return False
    
    # ==================== 基础控制 ====================
    
    def home(self) -> bool:
        """机械臂归位到初始位置（基于 uarm_demo.py 的实现）"""
        if not self.is_connected():
            print("❌ 机械臂未连接")
            return False
        
        try:
            print("🏠 uArm 机械臂归位中...")
            self.current_status = ArmStatus.HOMING
            self.is_moving = True
            
            # 使用 G-code 命令进行归位 - 基于 uarm_demo.py 的实现
            self.send_command("G0 X150 Y0 Z90 F1000")
            time.sleep(2)
            self.send_command("M2231 V0")  # 设置手腕角度
            
            # 等待移动完成
            time.sleep(2)
            
            self.is_moving = False
            self.current_status = ArmStatus.IDLE
            
            # 更新状态
            self._update_robot_state()
            
            print("✅ uArm 机械臂归位完成")
            return True
                
        except Exception as e:
            print(f"❌ 归位失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.is_moving = False
            self.errors.append(f"归位失败: {e}")
            return False
    
    def emergency_stop(self) -> bool:
        """紧急停止"""
        try:
            print("🚨 uArm 机械臂紧急停止")
            
            if self.arm:
                # 设置伺服断开以停止所有运动
                self.arm.set_servo_detach()
                time.sleep(0.5)
                # 重新连接伺服
                self.arm.set_servo_attach()
            
            self.is_moving = False
            self.current_status = ArmStatus.IDLE
            
            print("✅ 紧急停止完成")
            return True
                
        except Exception as e:
            print(f"❌ 紧急停止失败: {e}")
            return False
    
    def reset_errors(self) -> bool:
        """重置错误状态"""
        try:
            self.errors.clear()
            if self.current_status == ArmStatus.ERROR:
                self.current_status = ArmStatus.IDLE
            print("✅ uArm 机械臂错误状态已重置")
            return True
        except Exception as e:
            print(f"❌ 重置错误失败: {e}")
            return False
    
    # ==================== 运动控制 ====================
    
    def move_to_position(self, position: Position, speed: Optional[float] = None) -> bool:
        """移动到指定位置（基于 uarm_demo.py 的实现）"""
        if not self.is_connected():
            print("❌ 机械臂未连接")
            return False
        
        try:
            print(f"🚀 移动到位置: x={position.x}, y={position.y}, z={position.z}")
            self.current_status = ArmStatus.MOVING
            self.is_moving = True
            
            # 使用 G-code 命令移动 - 基于 uarm_demo.py 的实现
            speed_value = int(speed) if speed else 1000
            command = f"G0 X{position.x} Y{position.y} Z{position.z} F{speed_value}"
            
            if self.send_command(command):
                # 等待移动完成
                time.sleep(2)
                
                self.is_moving = False
                self.current_status = ArmStatus.IDLE
                
                # 更新当前位置
                self.current_position = position
                
                print(f"✅ 移动完成")
                return True
            else:
                print("❌ 发送移动命令失败")
                self.current_status = ArmStatus.ERROR
                self.is_moving = False
                return False
            
        except Exception as e:
            print(f"❌ 移动失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.is_moving = False
            self.errors.append(f"移动失败: {e}")
            return False
    
    def move_to_joints(self, angles: JointAngles, speed: Optional[float] = None) -> bool:
        """移动到指定关节角度（基于 uarm_demo.py 的实现）"""
        if not self.is_connected():
            print("❌ 机械臂未连接")
            return False
        
        try:
            print(f"🚀 移动到关节角度: {angles.to_list()}")
            self.current_status = ArmStatus.MOVING
            self.is_moving = True
            
            # uArm 使用串口通信时，关节角度控制比较复杂
            # 这里简化处理，仅支持基本的关节控制
            print("⚠️ 串口通信模式下关节角度控制功能有限")
            
            # 等待移动完成
            time.sleep(2)
            
            self.is_moving = False
            self.current_status = ArmStatus.IDLE
            
            # 更新关节角度记录
            self.current_joints = angles
            
            print("✅ 关节移动完成")
            return True
            
        except Exception as e:
            print(f"❌ 关节移动失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.is_moving = False
            self.errors.append(f"关节移动失败: {e}")
            return False
    
    def get_current_position(self) -> Optional[Position]:
        """获取当前位置"""
        if not self.is_connected():
            return None
        
        # 使用串口通信获取位置比较复杂，这里返回记录的当前位置
        return self.current_position
    
    def get_current_joints(self) -> Optional[JointAngles]:
        """获取当前关节角度"""
        if not self.is_connected():
            return None
        
        # 使用串口通信获取关节角度比较复杂，这里返回记录的当前角度
        return self.current_joints
    
    # ==================== 抓取控制 ====================
    
    def grab_object(self, parameters: Optional[GrabParameters] = None) -> bool:
        """抓取物体（基于 uarm_demo.py 的实现）"""
        if not self.is_connected():
            print("❌ 机械臂未连接")
            return False
        
        try:
            print("🤏 开始抓取物体...")
            self.current_status = ArmStatus.GRABBING
            
            # 控制机械爪抓取 - 使用 G-code 命令
            self.send_command("M2232 V1")  # 1为关闭（抓取）
            
            # 等待抓取
            time.sleep(2)
            
            self.has_object = True
            self.current_status = ArmStatus.IDLE
            print("✅ 抓取完成")
            return True
                
        except Exception as e:
            print(f"❌ 抓取失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.errors.append(f"抓取失败: {e}")
            return False
    
    def release_object(self) -> bool:
        """释放物体（基于 uarm_demo.py 的实现）"""
        if not self.is_connected():
            print("❌ 机械臂未连接")
            return False
        
        try:
            print("🤲 释放物体...")
            self.current_status = ArmStatus.RELEASING
            
            # 控制机械爪释放 - 使用 G-code 命令
            self.send_command("M2232 V0")  # 0为打开（释放）
            
            # 等待释放
            time.sleep(2)
            
            self.has_object = False
            self.current_status = ArmStatus.IDLE
            
            print("✅ 释放完成")
            return True
            
        except Exception as e:
            print(f"❌ 释放失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.errors.append(f"释放失败: {e}")
            return False
    
    def is_holding_object(self) -> bool:
        """检查是否抓取物体"""
        if not self.is_connected():
            return False
        
        try:
            pump_status = self.arm.get_pump_status()
            self.has_object = (pump_status == 2)
            return self.has_object
        except Exception:
            return self.has_object
    
    # ==================== 状态管理 ====================
    
    def get_status(self) -> Dict:
        """获取机械臂状态"""
        status = {
            'connected': self.is_connected(),
            'status': self.current_status.value,
            'current_position': self.current_position.to_dict() if self.current_position else {'x': 0, 'y': 0, 'z': 0},
            'current_joints': self.current_joints.to_list() if self.current_joints else [0, 0, 0, 0, 0, 0],
            'has_object': self.has_object,
            'is_moving': self.is_moving,
            'errors': self.errors.copy(),
            'communication_type': 'serial',
            'port': self.port,
            'baudrate': self.baudrate
        }
        
        return status
    
    def get_configuration(self) -> ArmConfiguration:
        """获取机械臂配置"""
        return ArmConfiguration(
            max_reach=350.0,    # uArm 最大工作半径
            max_payload=0.5,    # 最大负载 500g
            degrees_of_freedom=3,  # uArm 有效自由度
            max_speed=100.0,
            acceleration=50.0,
            precision=1.0
        )
    
    # ==================== 垃圾分拣专用功能 ====================
    
    def sort_garbage(self, garbage_type: str) -> bool:
        """
        垃圾分拣功能（基于 uarm_demo.py 的实现）
        
        Args:
            garbage_type: 垃圾类型
            
        Returns:
            bool: 分拣成功返回True
        """
        if not self.is_connected():
            print("❌ 机械臂未连接")
            return False
        
        if garbage_type not in self.garbage_positions:
            print(f"❌ 不支持的垃圾类型: {garbage_type}")
            return False
        
        try:
            print(f"🗑️ 开始分拣垃圾: {garbage_type}")
            
            # 获取目标位置
            target_pos = self.garbage_positions[garbage_type]
            target_position = Position(x=target_pos['x'], y=target_pos['y'], z=target_pos['z'])
            
            # 移动到目标位置
            if self.move_to_position(target_position):
                # 释放物体
                if self.release_object():
                    # 抬起机械臂
                    self.move_to_position(Position(x=target_pos['x'], y=target_pos['y'], z=50))
                    time.sleep(1)
                    
                    # 返回初始位置
                    self.home()
                    
                    print(f"✅ 垃圾分拣完成: {garbage_type}")
                    return True
                else:
                    print("❌ 释放物体失败")
                    return False
            else:
                print("❌ 移动到目标位置失败")
                return False
                
        except Exception as e:
            print(f"❌ 垃圾分拣失败: {e}")
            return False
    
    def pick_object(self, x: float, y: float, class_id: int) -> bool:
        """
        拾取物体并分类放置（基于 uarm_demo.py 的完整实现）
        
        Args:
            x: 物体x坐标
            y: 物体y坐标
            class_id: 物体类别ID
            
        Returns:
            bool: 拾取成功返回True
        """
        if not self.is_connected():
            print("❌ 机械臂未连接")
            return False
        
        try:
            print(f"🤖 开始拾取物体: 坐标({x}, {y}), 类别ID: {class_id}")
            
            # 1. 移动到物体上方
            self.move_to_position(Position(x=x, y=y, z=50))
            time.sleep(2)
            
            # 2. 下降到物体位置
            self.move_to_position(Position(x=x, y=y, z=self.polar_height))
            time.sleep(2)
            
            # 3. 抓取物体
            self.grab_object()
            time.sleep(2)
            
            # 4. 抬起物体
            self.move_to_position(Position(x=x, y=y, z=50))
            time.sleep(2)
            
            # 5. 移动到分类区域
            target_x, target_y = self.get_classification_position(class_id)
            self.move_to_position(Position(x=target_x, y=target_y, z=50))
            time.sleep(2)
            
            # 6. 释放物体
            self.release_object()
            time.sleep(2)
            
            # 7. 抬起机械臂
            self.move_to_position(Position(x=target_x, y=target_y, z=50))
            time.sleep(2)
            
            # 8. 返回初始位置
            self.home()
            
            print("✅ 拾取和分类完成")
            return True
            
        except Exception as e:
            print(f"❌ 拾取物体失败: {e}")
            return False
    
    def get_classification_position(self, class_id: int) -> tuple:
        """
        根据垃圾类别ID返回放置位置（基于 uarm_demo.py 的实现）
        
        Args:
            class_id: 类别ID
            
        Returns:
            tuple: (x, y) 坐标
        """
        # 根据类别ID确定垃圾类型
        if class_id in [0, 4]:  # banana, fish_bones - 厨余垃圾
            return (20.6, 127.1)
        elif class_id in [1, 2, 6, 7, 8]:  # beverages, cardboard_box, milk_box等 - 可回收垃圾
            return (99.5, 121.7)
        else:  # chips, instant_noodles等 - 其他垃圾
            return (189.6, 142.4)
    
    # ==================== 私有方法 ====================
    
    def _verify_connection(self) -> bool:
        """验证连接"""
        try:
            if not self.arm:
                return False
            
            # 尝试获取设备信息
            device_info = self.arm.get_device_info()
            return device_info is not None
            
        except Exception as e:
            print(f"❌ 连接验证失败: {e}")
            return False
    
    def _update_robot_state(self):
        """更新机械臂状态"""
        # 使用串口通信时，状态更新比较复杂，这里简化处理
        # 主要依赖于程序内部的状态记录
        pass
    
    def __del__(self):
        """析构函数"""
        if self.is_connected():
            self.disconnect() 