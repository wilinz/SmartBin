#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三方机械臂实现示例
演示如何继承RobotArmInterface来实现具体的机械臂驱动

示例厂商：Universal Robots (UR5)
"""

import time
import socket
import struct
from typing import Dict, List, Optional

from .robot_arm_interface import (
    RobotArmInterface,
    ArmStatus,
    Position,
    JointAngles,
    GrabParameters,
    ArmConfiguration
)


class URRobotArm(RobotArmInterface):
    """
    Universal Robots 机械臂实现示例
    
    注意：这是一个示例实现，展示如何继承抽象接口
    实际使用时需要根据具体的机械臂协议和SDK进行实现
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化UR机械臂
        
        Args:
            config: 配置参数，包含：
                - host: 机械臂IP地址
                - port: 通信端口（默认30003）
                - timeout: 通信超时时间
        """
        super().__init__(config)
        
        # 连接配置
        self.host = self.config.get('host', '192.168.1.100')
        self.port = self.config.get('port', 30003)
        self.timeout = self.config.get('timeout', 5.0)
        
        # 通信连接
        self.socket = None
        
        # 状态变量
        self.current_position = Position(0.0, 0.0, 0.0)
        self.current_joints = JointAngles(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.has_object = False
        self.is_moving = False
        self.errors = []
        
        self.logger.info(f"🤖 UR机械臂已初始化 - {self.host}:{self.port}")
    
    # ==================== 连接管理 ====================
    
    def connect(self) -> bool:
        """连接UR机械臂"""
        try:
            self.logger.info(f"🔌 连接UR机械臂: {self.host}:{self.port}")
            
            # 创建TCP socket连接
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            # 验证连接
            if self._verify_connection():
                self.is_connected = True
                self.current_status = ArmStatus.IDLE
                self.errors.clear()
                
                # 读取初始状态
                self._update_robot_state()
                
                self.logger.info("✅ UR机械臂连接成功")
                return True
            else:
                self.logger.error("❌ UR机械臂连接验证失败")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ UR机械臂连接失败: {e}")
            self.errors.append(f"连接失败: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def disconnect(self) -> bool:
        """断开UR机械臂连接"""
        try:
            self.logger.info("🔌 断开UR机械臂连接...")
            
            if self.socket:
                self.socket.close()
                self.socket = None
            
            self.is_connected = False
            self.current_status = ArmStatus.DISCONNECTED
            
            self.logger.info("✅ UR机械臂已断开连接")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 断开连接失败: {e}")
            return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.is_connected and self.socket is not None
    
    # ==================== 基础控制 ====================
    
    def home(self) -> bool:
        """归位到初始位置"""
        if not self.is_connected():
            self.logger.error("机械臂未连接")
            return False
        
        try:
            self.logger.info("🏠 UR机械臂归位中...")
            self.current_status = ArmStatus.HOMING
            self.is_moving = True
            
            # 发送归位命令（示例UR脚本命令）
            home_script = """
            def home_program():
                home_joints = [0, -1.57, 1.57, -1.57, -1.57, 0]
                movej(home_joints, a=1.0, v=0.5)
            end
            home_program()
            """
            
            if self._send_script(home_script):
                # 等待移动完成
                self._wait_for_movement_complete()
                
                self.is_moving = False
                self.current_status = ArmStatus.IDLE
                
                # 更新状态
                self._update_robot_state()
                
                self.logger.info("✅ UR机械臂归位完成")
                return True
            else:
                self.current_status = ArmStatus.ERROR
                self.is_moving = False
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 归位失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.is_moving = False
            self.errors.append(f"归位失败: {e}")
            return False
    
    def emergency_stop(self) -> bool:
        """紧急停止"""
        try:
            self.logger.warning("🚨 UR机械臂紧急停止")
            
            # 发送停止命令
            stop_script = "stopj(2.0)\n"  # 2.0为减速度
            
            if self._send_script(stop_script):
                self.is_moving = False
                self.current_status = ArmStatus.IDLE
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 紧急停止失败: {e}")
            return False
    
    def reset_errors(self) -> bool:
        """重置错误状态"""
        try:
            self.errors.clear()
            if self.current_status == ArmStatus.ERROR:
                self.current_status = ArmStatus.IDLE
            self.logger.info("✅ UR机械臂错误状态已重置")
            return True
        except Exception as e:
            self.logger.error(f"❌ 重置错误失败: {e}")
            return False
    
    # ==================== 运动控制 ====================
    
    def move_to_position(self, position: Position, speed: Optional[float] = None) -> bool:
        """移动到指定位置"""
        if not self.is_connected():
            self.logger.error("机械臂未连接")
            return False
        
        try:
            velocity = (speed or 50.0) / 100.0 * 0.5  # 转换为UR速度单位
            acceleration = 1.0
            
            self.logger.info(f"📍 UR机械臂移动到位置: {position}")
            self.current_status = ArmStatus.MOVING
            self.is_moving = True
            
            # 构建UR脚本命令（位置单位：米）
            move_script = f"""
            def move_program():
                target_pose = p[{position.x/1000:.6f}, {position.y/1000:.6f}, {position.z/1000:.6f}, 0, 3.14159, 0]
                movel(target_pose, a={acceleration}, v={velocity})
            end
            move_program()
            """
            
            if self._send_script(move_script):
                # 等待移动完成
                self._wait_for_movement_complete()
                
                self.is_moving = False
                self.current_status = ArmStatus.IDLE
                
                # 更新当前位置
                self.current_position = Position(position.x, position.y, position.z)
                
                self.logger.info("✅ UR机械臂移动完成")
                return True
            else:
                self.current_status = ArmStatus.ERROR
                self.is_moving = False
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 移动失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.is_moving = False
            self.errors.append(f"移动失败: {e}")
            return False
    
    def move_to_joints(self, angles: JointAngles, speed: Optional[float] = None) -> bool:
        """移动到指定关节角度"""
        if not self.is_connected():
            self.logger.error("机械臂未连接")
            return False
        
        try:
            velocity = (speed or 50.0) / 100.0 * 1.0  # 转换为UR角速度单位
            acceleration = 1.0
            
            self.logger.info(f"🦾 UR机械臂关节移动: {angles.to_list()}")
            self.current_status = ArmStatus.MOVING
            self.is_moving = True
            
            # 构建UR脚本命令（角度单位：弧度）
            joint_angles = [angle * 3.14159 / 180.0 for angle in angles.to_list()]  # 转换为弧度
            move_script = f"""
            def joint_move_program():
                target_joints = {joint_angles}
                movej(target_joints, a={acceleration}, v={velocity})
            end
            joint_move_program()
            """
            
            if self._send_script(move_script):
                # 等待移动完成
                self._wait_for_movement_complete()
                
                self.is_moving = False
                self.current_status = ArmStatus.IDLE
                
                # 更新关节角度
                self.current_joints = JointAngles(*angles.to_list())
                
                self.logger.info("✅ UR机械臂关节移动完成")
                return True
            else:
                self.current_status = ArmStatus.ERROR
                self.is_moving = False
                return False
                
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
            self._update_robot_state()
            return Position(self.current_position.x, self.current_position.y, self.current_position.z)
        except Exception as e:
            self.logger.error(f"获取位置失败: {e}")
            return None
    
    def get_current_joints(self) -> Optional[JointAngles]:
        """获取当前关节角度"""
        if not self.is_connected():
            return None
        
        try:
            self._update_robot_state()
            return JointAngles(*self.current_joints.to_list())
        except Exception as e:
            self.logger.error(f"获取关节角度失败: {e}")
            return None
    
    # ==================== 抓取控制 ====================
    
    def grab_object(self, parameters: Optional[GrabParameters] = None) -> bool:
        """抓取物体（通过数字IO控制气动夹爪）"""
        if not self.is_connected():
            self.logger.error("机械臂未连接")
            return False
        
        try:
            params = parameters or GrabParameters()
            self.logger.info(f"🤏 UR机械臂抓取物体，力度: {params.force}")
            
            self.current_status = ArmStatus.GRABBING
            
            # 发送数字输出信号控制夹爪
            grab_script = """
            def grab_program():
                set_digital_out(0, True)  # 夹爪闭合信号
                sleep(1.0)                # 等待夹爪动作完成
            end
            grab_program()
            """
            
            if self._send_script(grab_script):
                time.sleep(1.0)  # 等待夹爪动作
                
                # 检查是否抓取成功（可以通过传感器反馈）
                self.has_object = self._check_gripper_sensor()
                self.current_status = ArmStatus.IDLE
                
                if self.has_object:
                    self.logger.info("✅ UR机械臂抓取成功")
                    return True
                else:
                    self.logger.warning("⚠️ UR机械臂抓取失败 - 未检测到物体")
                    return False
            else:
                self.current_status = ArmStatus.ERROR
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 抓取失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.errors.append(f"抓取失败: {e}")
            return False
    
    def release_object(self) -> bool:
        """释放物体"""
        if not self.is_connected():
            self.logger.error("机械臂未连接")
            return False
        
        try:
            self.logger.info("📤 UR机械臂释放物体...")
            self.current_status = ArmStatus.RELEASING
            
            # 发送数字输出信号控制夹爪
            release_script = """
            def release_program():
                set_digital_out(0, False)  # 夹爪打开信号
                sleep(0.5)                 # 等待夹爪动作完成
            end
            release_program()
            """
            
            if self._send_script(release_script):
                time.sleep(0.5)  # 等待夹爪动作
                
                self.has_object = False
                self.current_status = ArmStatus.IDLE
                
                self.logger.info("✅ UR机械臂物体释放成功")
                return True
            else:
                self.current_status = ArmStatus.ERROR
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 释放失败: {e}")
            self.current_status = ArmStatus.ERROR
            self.errors.append(f"释放失败: {e}")
            return False
    
    def is_holding_object(self) -> bool:
        """检查是否正在抓取物体"""
        return self.has_object
    
    # ==================== 状态查询 ====================
    
    def get_status(self) -> Dict:
        """获取机械臂详细状态"""
        self._update_robot_state()
        
        return {
            'connected': self.is_connected(),
            'status': self.current_status.value,
            'current_position': self.current_position.to_dict(),
            'current_joints': self.current_joints.to_list(),
            'is_moving': self.is_moving,
            'has_object': self.has_object,
            'errors': self.errors.copy(),
            'temperature': self._get_robot_temperature(),
            'load': self._get_robot_load()
        }
    
    def get_configuration(self) -> ArmConfiguration:
        """获取UR5机械臂配置"""
        return ArmConfiguration(
            max_reach=850.0,    # UR5最大工作半径
            max_payload=5.0,    # UR5最大负载
            degrees_of_freedom=6,
            max_speed=250.0,    # 最大末端速度 mm/s
            acceleration=750.0,  # 最大加速度 mm/s²
            precision=0.03      # 重复定位精度 mm
        )
    
    # ==================== 私有辅助方法 ====================
    
    def _verify_connection(self) -> bool:
        """验证连接是否有效"""
        try:
            # 发送简单的状态查询命令
            test_script = "get_actual_tcp_pose()\n"
            return self._send_script(test_script)
        except Exception:
            return False
    
    def _send_script(self, script: str) -> bool:
        """发送UR脚本命令"""
        try:
            if not self.socket:
                return False
            
            # 发送脚本内容
            self.socket.send(script.encode('utf-8'))
            return True
            
        except Exception as e:
            self.logger.error(f"发送脚本失败: {e}")
            return False
    
    def _update_robot_state(self):
        """更新机械臂状态"""
        try:
            if not self.socket:
                return
            
            # 这里应该读取机械臂的实时状态数据
            # UR机械臂通过30001端口提供实时状态数据
            # 实际实现需要解析UR的数据包格式
            
            # 示例：模拟状态更新
            pass
            
        except Exception as e:
            self.logger.error(f"更新状态失败: {e}")
    
    def _wait_for_movement_complete(self):
        """等待移动完成"""
        try:
            # 实际实现中应该检查机械臂的运动状态
            # 这里简化为等待固定时间
            time.sleep(2.0)
        except Exception as e:
            self.logger.error(f"等待移动完成失败: {e}")
    
    def _check_gripper_sensor(self) -> bool:
        """检查夹爪传感器（检测是否抓取物体）"""
        try:
            # 实际实现中应该读取数字输入信号
            # 这里简化为随机结果
            import random
            return random.random() > 0.2  # 80%成功率
        except Exception:
            return False
    
    def _get_robot_temperature(self) -> Dict:
        """获取机械臂温度信息"""
        # 实际实现应该从机械臂读取温度数据
        return {
            'joint_1': 25.0,
            'joint_2': 28.0,
            'joint_3': 24.0,
            'joint_4': 26.0,
            'joint_5': 23.0,
            'joint_6': 25.0,
            'controller': 35.0
        }
    
    def _get_robot_load(self) -> Dict:
        """获取机械臂负载信息"""
        # 实际实现应该从机械臂读取负载数据
        base_load = 1.0 if self.has_object else 0.1
        return {
            'current_load': base_load,
            'max_load': 5.0,
            'percentage': (base_load / 5.0) * 100
        }
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'is_connected') and self.is_connected():
            self.disconnect()


# ==================== 其他厂商示例 ====================

class KukaRobotArm(RobotArmInterface):
    """
    KUKA机械臂实现示例
    
    注意：这是一个框架示例，具体实现需要根据KUKA的API
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.logger.info("🤖 KUKA机械臂已初始化")
        # 具体初始化代码...
    
    def connect(self) -> bool:
        """连接KUKA机械臂"""
        # 实现KUKA特定的连接逻辑
        self.logger.info("🔌 连接KUKA机械臂...")
        return True
    
    def disconnect(self) -> bool:
        """断开KUKA机械臂连接"""
        self.logger.info("🔌 断开KUKA机械臂连接...")
        return True
    
    def is_connected(self) -> bool:
        return self.is_connected
    
    # 其他方法的实现...
    # 由于篇幅限制，这里只展示接口框架
    
    def home(self) -> bool:
        return True
    
    def emergency_stop(self) -> bool:
        return True
    
    def reset_errors(self) -> bool:
        return True
    
    def move_to_position(self, position: Position, speed: Optional[float] = None) -> bool:
        return True
    
    def move_to_joints(self, angles: JointAngles, speed: Optional[float] = None) -> bool:
        return True
    
    def get_current_position(self) -> Optional[Position]:
        return Position(0, 0, 0)
    
    def get_current_joints(self) -> Optional[JointAngles]:
        return JointAngles(0, 0, 0, 0, 0, 0)
    
    def grab_object(self, parameters: Optional[GrabParameters] = None) -> bool:
        return True
    
    def release_object(self) -> bool:
        return True
    
    def is_holding_object(self) -> bool:
        return False
    
    def get_status(self) -> Dict:
        return {'status': 'kuka_placeholder'}
    
    def get_configuration(self) -> ArmConfiguration:
        return ArmConfiguration()


# ==================== 导出 ====================

__all__ = [
    'URRobotArm',
    'KukaRobotArm'
] 