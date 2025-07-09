#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uArm 机械臂实现
基于 uarm_demo 的实现，继承 RobotArmInterface 接口
"""

import time
import platform
import os
import serial.tools.list_ports
from typing import Dict, List, Optional
import sys

from .robot_arm_interface import (
    RobotArmInterface,
    ArmStatus,
    Position,
    JointAngles,
    GrabParameters,
    ArmConfiguration
)

# 尝试导入 uarm 库
try:
    # 添加 uarm_demo 路径到 sys.path
    uarm_demo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uarm_demo')
    if uarm_demo_path not in sys.path:
        sys.path.insert(0, uarm_demo_path)
    
    from uarm.wrapper import SwiftAPI
    UARM_AVAILABLE = True
except ImportError:
    UARM_AVAILABLE = False
    SwiftAPI = None


class UarmRobotArm(RobotArmInterface):
    """
    uArm 机械臂实现
    
    基于 uarm_demo 的实现，提供完整的 uArm 机械臂控制功能
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化 uArm 机械臂
        
        Args:
            config: 配置参数，包含：
                - port: 串口端口（可选，自动检测）
                - baudrate: 波特率（默认115200）
                - speed_factor: 速度系数（默认100）
        """
        super().__init__(config)
        
        if not UARM_AVAILABLE:
            self.logger.error("❌ uArm 库未安装或导入失败")
            raise ImportError("uArm 库未安装，请检查 uarm_demo 目录")
        
        # 配置参数
        self.port = self.config.get('port', None)
        self.baudrate = self.config.get('baudrate', 115200)
        self.speed_factor = self.config.get('speed_factor', 100)
        
        # uArm 实例
        self.arm = None
        
        # 状态变量
        self._is_connected = False
        self.current_position = Position(0.0, 0.0, 0.0)
        self.current_joints = JointAngles(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.has_object = False
        self.is_moving = False
        self.errors = []
        
        # 垃圾分类位置定义
        self.garbage_positions = {
            'banana': {'x': 200, 'y': 50, 'z': 50},      # 香蕉皮 - 厨余垃圾
            'beverages': {'x': 200, 'y': -50, 'z': 50},  # 饮料瓶 - 可回收垃圾
            'cardboard_box': {'x': 150, 'y': 50, 'z': 50}, # 纸盒 - 可回收垃圾
            'chips': {'x': 150, 'y': -50, 'z': 50},     # 薯片袋 - 其他垃圾
            'fish_bones': {'x': 250, 'y': 50, 'z': 50}, # 鱼骨 - 厨余垃圾
            'instant_noodles': {'x': 250, 'y': -50, 'z': 50}, # 泡面盒 - 其他垃圾
            'milk_box_type1': {'x': 180, 'y': 30, 'z': 50},   # 牛奶盒1 - 可回收垃圾
            'milk_box_type2': {'x': 180, 'y': -30, 'z': 50},  # 牛奶盒2 - 可回收垃圾
            'plastic': {'x': 220, 'y': 0, 'z': 50}      # 塑料 - 可回收垃圾
        }
        
        self.logger.info("🤖 uArm 机械臂已初始化")
    
    def _check_port(self, port: Optional[str] = None) -> Optional[str]:
        """检测并返回 uArm 机械臂端口"""
        self.logger.info('🔍 检测 uArm 设备...')
        
        if port:
            self.logger.info(f'使用指定端口: {port}')
            return port
        
        detected_port = None
        
        if platform.system() == 'Windows':
            # Windows 系统端口检测
            plist = list(serial.tools.list_ports.comports())
            if len(plist) <= 0:
                self.logger.error("❌ 未找到串口设备")
            else:
                plist_0 = list(plist[0])
                detected_port = plist_0[0]
                self.logger.info(f'✅ 检测到设备: {detected_port}')
        else:
            # Linux/macOS 系统端口检测
            try:
                ret = os.popen("ls /dev/serial/by-id").read()
                if ret.strip():
                    detected_port = "/dev/serial/by-id/" + ret.split('\n')[0].split('/')[-1]
                    self.logger.info(f'✅ 检测到设备: {detected_port}')
                else:
                    # 尝试常见的端口
                    common_ports = ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyACM1', '/dev/ttyUSB1']
                    for test_port in common_ports:
                        if os.path.exists(test_port):
                            detected_port = test_port
                            self.logger.info(f'✅ 使用端口: {detected_port}')
                            break
            except Exception as e:
                self.logger.error(f"❌ 端口检测失败: {e}")
        
        if not detected_port:
            self.logger.error("❌ 未找到 uArm 设备端口")
        
        return detected_port
    
    # ==================== 连接管理 ====================
    
    def connect(self) -> bool:
        """连接 uArm 机械臂"""
        try:
            # 检测端口
            port = self._check_port(self.port)
            if not port:
                self.logger.error("❌ 未找到可用端口")
                return False
            
            self.logger.info(f"🔌 连接 uArm 机械臂: {port}")
            
            # 创建 SwiftAPI 实例
            self.arm = SwiftAPI(port=port, baudrate=self.baudrate)
            
            # 等待连接稳定
            time.sleep(2)
            
            # 设置速度系数
            self.arm.set_speed_factor(self.speed_factor)
            
            # 验证连接
            if self._verify_connection():
                self._is_connected = True
                self.current_status = ArmStatus.IDLE
                self.errors.clear()
                
                # 读取初始状态
                self._update_robot_state()
                
                self.logger.info("✅ uArm 机械臂连接成功")
                return True
            else:
                self.logger.error("❌ uArm 机械臂连接验证失败")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ uArm 机械臂连接失败: {e}")
            self.errors.append(f"连接失败: {e}")
            self.arm = None
            return False
    
    def disconnect(self) -> bool:
        """断开 uArm 机械臂连接"""
        try:
            self.logger.info("🔌 断开 uArm 机械臂连接...")
            
            if self.arm:
                # 设置伺服断开
                self.arm.set_servo_detach()
                self.arm = None
            
            self._is_connected = False
            self.current_status = ArmStatus.DISCONNECTED
            
            self.logger.info("✅ uArm 机械臂已断开连接")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 断开连接失败: {e}")
            return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._is_connected and self.arm is not None
    
    # ==================== 基础控制 ====================
    
    def home(self) -> bool:
        """机械臂归位到初始位置"""
        if not self.is_connected():
            self.logger.error("❌ 机械臂未连接")
            return False
        
        try:
            self.logger.info("🏠 uArm 机械臂归位中...")
            self.current_status = ArmStatus.HOMING
            self.is_moving = True
            
            # 复位机械臂
            self.arm.reset(speed=1000)
            
            # 等待复位完成
            time.sleep(3)
            
            # 移动到待抓取位置
            self.arm.set_position(x=115, y=-3, z=45)
            
            # 等待移动完成
            time.sleep(2)
            
            self.is_moving = False
            self.current_status = ArmStatus.IDLE
            
            # 更新状态
            self._update_robot_state()
            
            self.logger.info("✅ uArm 机械臂归位完成")
            return True
                
        except Exception as e:
            self.logger.error(f"❌ 归位失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.is_moving = False
            self.errors.append(f"归位失败: {e}")
            return False
    
    def emergency_stop(self) -> bool:
        """紧急停止"""
        try:
            self.logger.warning("🚨 uArm 机械臂紧急停止")
            
            if self.arm:
                # 设置伺服断开以停止所有运动
                self.arm.set_servo_detach()
                time.sleep(0.5)
                # 重新连接伺服
                self.arm.set_servo_attach()
            
            self.is_moving = False
            self.current_status = ArmStatus.IDLE
            
            self.logger.info("✅ 紧急停止完成")
            return True
                
        except Exception as e:
            self.logger.error(f"❌ 紧急停止失败: {e}")
            return False
    
    def reset_errors(self) -> bool:
        """重置错误状态"""
        try:
            self.errors.clear()
            if self.current_status == ArmStatus.ERROR:
                self.current_status = ArmStatus.IDLE
            self.logger.info("✅ uArm 机械臂错误状态已重置")
            return True
        except Exception as e:
            self.logger.error(f"❌ 重置错误失败: {e}")
            return False
    
    # ==================== 运动控制 ====================
    
    def move_to_position(self, position: Position, speed: Optional[float] = None) -> bool:
        """移动到指定位置"""
        if not self.is_connected():
            self.logger.error("❌ 机械臂未连接")
            return False
        
        try:
            self.logger.info(f"🚀 移动到位置: {position}")
            self.current_status = ArmStatus.MOVING
            self.is_moving = True
            
            # 设置速度
            if speed:
                self.arm.set_speed_factor(min(max(speed, 1), 100))
            
            # 移动到目标位置
            self.arm.set_position(x=position.x, y=position.y, z=position.z)
            
            # 等待移动完成
            time.sleep(2)
            
            self.is_moving = False
            self.current_status = ArmStatus.IDLE
            
            # 更新当前位置
            self._update_robot_state()
            
            self.logger.info("✅ 移动完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 移动失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.is_moving = False
            self.errors.append(f"移动失败: {e}")
            return False
    
    def move_to_joints(self, angles: JointAngles, speed: Optional[float] = None) -> bool:
        """移动到指定关节角度"""
        if not self.is_connected():
            self.logger.error("❌ 机械臂未连接")
            return False
        
        try:
            self.logger.info(f"🚀 移动到关节角度: {angles.to_list()}")
            self.current_status = ArmStatus.MOVING
            self.is_moving = True
            
            # 设置速度
            if speed:
                self.arm.set_speed_factor(min(max(speed, 1), 100))
            
            # 设置关节角度（uArm 主要使用前3个关节）
            self.arm.set_servo_angle(servo_id=0, angle=angles.j1)  # 底座
            time.sleep(0.5)
            self.arm.set_servo_angle(servo_id=1, angle=angles.j2)  # 大臂
            time.sleep(0.5)
            self.arm.set_servo_angle(servo_id=2, angle=angles.j3)  # 小臂
            
            # 等待移动完成
            time.sleep(2)
            
            self.is_moving = False
            self.current_status = ArmStatus.IDLE
            
            # 更新状态
            self._update_robot_state()
            
            self.logger.info("✅ 关节移动完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 关节移动失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.is_moving = False
            self.errors.append(f"关节移动失败: {e}")
            return False
    
    def get_current_position(self) -> Optional[Position]:
        """获取当前位置"""
        if not self.is_connected():
            return None
        
        try:
            pos = self.arm.get_position()
            if pos:
                position = Position(x=pos[0], y=pos[1], z=pos[2])
                self.current_position = position
                return position
        except Exception as e:
            self.logger.error(f"❌ 获取位置失败: {e}")
        
        return self.current_position
    
    def get_current_joints(self) -> Optional[JointAngles]:
        """获取当前关节角度"""
        if not self.is_connected():
            return None
        
        try:
            angles = self.arm.get_servo_angle()
            if angles and len(angles) >= 3:
                joints = JointAngles(
                    j1=angles[0],
                    j2=angles[1], 
                    j3=angles[2],
                    j4=0.0,  # uArm 没有这些关节
                    j5=0.0,
                    j6=0.0
                )
                self.current_joints = joints
                return joints
        except Exception as e:
            self.logger.error(f"❌ 获取关节角度失败: {e}")
        
        return self.current_joints
    
    # ==================== 抓取控制 ====================
    
    def grab_object(self, parameters: Optional[GrabParameters] = None) -> bool:
        """抓取物体"""
        if not self.is_connected():
            self.logger.error("❌ 机械臂未连接")
            return False
        
        try:
            self.logger.info("🤏 开始抓取物体...")
            self.current_status = ArmStatus.GRABBING
            
            # 控制吸盘打开
            self.arm.set_pump(on=True)
            
            # 等待抓取
            time.sleep(1)
            
            # 检查是否抓取成功
            pump_status = self.arm.get_pump_status()
            if pump_status == 2:  # 2表示抓取到物体
                self.has_object = True
                self.current_status = ArmStatus.IDLE
                self.logger.info("✅ 抓取成功")
                return True
            else:
                self.arm.set_pump(on=False)
                self.current_status = ArmStatus.IDLE
                self.logger.warning("⚠️ 抓取失败，未检测到物体")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 抓取失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.errors.append(f"抓取失败: {e}")
            return False
    
    def release_object(self) -> bool:
        """释放物体"""
        if not self.is_connected():
            self.logger.error("❌ 机械臂未连接")
            return False
        
        try:
            self.logger.info("🤲 释放物体...")
            self.current_status = ArmStatus.RELEASING
            
            # 控制吸盘关闭
            self.arm.set_pump(on=False)
            
            # 等待释放
            time.sleep(1)
            
            self.has_object = False
            self.current_status = ArmStatus.IDLE
            
            self.logger.info("✅ 释放完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 释放失败: {e}")
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
            'errors': self.errors.copy()
        }
        
        if self.is_connected():
            try:
                # 获取额外的 uArm 状态信息
                status.update({
                    'power_status': self.arm.get_power_status(),
                    'device_info': self.arm.get_device_info(),
                    'pump_status': self.arm.get_pump_status(),
                    'mode': self.arm.get_mode()
                })
            except Exception as e:
                self.logger.warning(f"获取扩展状态失败: {e}")
        
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
        垃圾分拣功能
        
        Args:
            garbage_type: 垃圾类型
            
        Returns:
            bool: 分拣成功返回True
        """
        if not self.is_connected():
            self.logger.error("❌ 机械臂未连接")
            return False
        
        if garbage_type not in self.garbage_positions:
            self.logger.error(f"❌ 不支持的垃圾类型: {garbage_type}")
            return False
        
        try:
            self.logger.info(f"🗑️ 开始分拣垃圾: {garbage_type}")
            
            # 获取目标位置
            target_pos = self.garbage_positions[garbage_type]
            target_position = Position(x=target_pos['x'], y=target_pos['y'], z=target_pos['z'])
            
            # 移动到目标位置
            if self.move_to_position(target_position):
                # 释放物体
                if self.release_object():
                    self.logger.info(f"✅ 垃圾分拣完成: {garbage_type}")
                    return True
                else:
                    self.logger.error("❌ 释放物体失败")
                    return False
            else:
                self.logger.error("❌ 移动到目标位置失败")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 垃圾分拣失败: {e}")
            return False
    
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
            self.logger.error(f"连接验证失败: {e}")
            return False
    
    def _update_robot_state(self):
        """更新机械臂状态"""
        try:
            # 更新位置
            self.get_current_position()
            # 更新关节角度
            self.get_current_joints()
            # 更新物体状态
            self.is_holding_object()
        except Exception as e:
            self.logger.warning(f"状态更新失败: {e}")
    
    def __del__(self):
        """析构函数"""
        if self.is_connected():
            self.disconnect() 