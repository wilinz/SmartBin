#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头控制模块
负责摄像头的初始化、图像采集和参数设置
支持真实摄像头和虚拟摄像头模式
"""

import cv2
import numpy as np
import time
import logging
import threading
import os
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

from ..utils.config_loader import config_loader


class CameraController:
    """摄像头控制器（支持虚拟模式）"""
    
    def __init__(self, device_id: Optional[int] = None, virtual_mode: bool = None):
        self.config = config_loader.get_camera_config()
        self.device_id = device_id or self.config.get('device_id', 0)
        
        # 自动检测虚拟模式
        if virtual_mode is None:
            self.virtual_mode = self.config.get('virtual_mode', self._should_use_virtual_mode())
        else:
            self.virtual_mode = virtual_mode
        
        self.cap = None
        self.is_running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.capture_thread = None
        
        # 摄像头参数
        self.width = self.config.get('width', 640)
        self.height = self.config.get('height', 480)
        self.fps = self.config.get('fps', 30)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 统计信息
        self.frame_count = 0
        self.last_frame_time = 0
        self.actual_fps = 0
        
        # 虚拟摄像头相关
        self.virtual_images = []
        self.virtual_image_index = 0
        self._load_virtual_images()
    
    def start(self) -> bool:
        """
        启动摄像头
        
        Returns:
            是否启动成功
        """
        try:
            if self.virtual_mode:
                # 虚拟摄像头模式
                self.logger.info("启动虚拟摄像头模式")
                self.is_running = True
                self.capture_thread = threading.Thread(target=self._virtual_capture_loop, daemon=True)
                self.capture_thread.start()
                self.logger.info("虚拟摄像头启动成功")
                return True
            else:
                # 真实摄像头模式
                self.cap = cv2.VideoCapture(self.device_id)
                
                if not self.cap.isOpened():
                    self.logger.warning(f"无法打开摄像头设备 {self.device_id}，切换到虚拟模式")
                    self.virtual_mode = True
                    return self.start()  # 递归调用启动虚拟模式
                
                # 设置摄像头参数
                self._setup_camera_properties()
                
                # 启动采集线程
                self.is_running = True
                self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
                self.capture_thread.start()
                
                self.logger.info(f"摄像头 {self.device_id} 启动成功")
                return True
            
        except Exception as e:
            self.logger.error(f"摄像头启动失败: {e}")
            # 尝试切换到虚拟模式
            if not self.virtual_mode:
                self.logger.info("尝试切换到虚拟摄像头模式")
                self.virtual_mode = True
                return self.start()
            return False
    
    def stop(self):
        """停止摄像头"""
        try:
            self.is_running = False
            
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=2.0)
            
            if self.cap and self.cap.isOpened():
                self.cap.release()
            
            self.logger.info("摄像头已停止")
            
        except Exception as e:
            self.logger.error(f"停止摄像头失败: {e}")
    
    def _setup_camera_properties(self):
        """设置摄像头属性"""
        try:
            # 设置分辨率
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # 设置帧率
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # 设置其他属性
            if 'auto_exposure' in self.config:
                auto_exposure = 1 if self.config['auto_exposure'] else 0
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, auto_exposure)
            
            if 'exposure' in self.config and not self.config.get('auto_exposure', True):
                self.cap.set(cv2.CAP_PROP_EXPOSURE, self.config['exposure'])
            
            if 'gain' in self.config:
                self.cap.set(cv2.CAP_PROP_GAIN, self.config['gain'])
            
            if 'white_balance' in self.config:
                self.cap.set(cv2.CAP_PROP_WB_TEMPERATURE, self.config['white_balance'])
            
            # 验证设置
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"摄像头参数: {actual_width}x{actual_height} @ {actual_fps:.1f}fps")
            
        except Exception as e:
            self.logger.warning(f"设置摄像头属性失败: {e}")
    
    def _capture_loop(self):
        """摄像头采集循环"""
        while self.is_running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                    
                    # 更新统计信息
                    self.frame_count += 1
                    current_time = time.time()
                    
                    if self.last_frame_time > 0:
                        time_diff = current_time - self.last_frame_time
                        if time_diff > 0:
                            self.actual_fps = 1.0 / time_diff
                    
                    self.last_frame_time = current_time
                else:
                    self.logger.warning("摄像头读取帧失败")
                    time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"摄像头采集错误: {e}")
                time.sleep(0.1)
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        获取当前帧
        
        Returns:
            当前帧图像，如果没有可用帧则返回None
        """
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def capture_single_frame(self) -> Optional[np.ndarray]:
        """
        单次拍照模式
        
        Returns:
            拍摄的图像
        """
        if not self.is_connected():
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return frame
            return None
        except Exception as e:
            self.logger.error(f"单次拍照失败: {e}")
            return None
    
    def is_connected(self) -> bool:
        """检查摄像头是否连接"""
        if self.virtual_mode:
            return True  # 虚拟摄像头始终可用
        return self.cap is not None and self.cap.isOpened()
    
    def is_running_capture(self) -> bool:
        """检查是否正在采集"""
        return self.is_running
    
    def get_camera_info(self) -> Dict[str, Any]:
        """获取摄像头信息"""
        if not self.is_connected():
            return {"status": "未连接"}
        
        try:
            info = {
                "device_id": self.device_id,
                "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": self.cap.get(cv2.CAP_PROP_FPS),
                "actual_fps": round(self.actual_fps, 2),
                "frame_count": self.frame_count,
                "is_running": self.is_running,
                "backend": self.cap.getBackendName() if hasattr(self.cap, 'getBackendName') else 'Unknown'
            }
            
            # 获取其他属性
            try:
                info["brightness"] = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
                info["contrast"] = self.cap.get(cv2.CAP_PROP_CONTRAST)
                info["saturation"] = self.cap.get(cv2.CAP_PROP_SATURATION)
                info["exposure"] = self.cap.get(cv2.CAP_PROP_EXPOSURE)
                info["gain"] = self.cap.get(cv2.CAP_PROP_GAIN)
            except:
                pass
            
            return info
            
        except Exception as e:
            self.logger.error(f"获取摄像头信息失败: {e}")
            return {"status": "错误", "error": str(e)}
    
    def set_resolution(self, width: int, height: int) -> bool:
        """
        设置分辨率
        
        Args:
            width: 宽度
            height: 高度
        
        Returns:
            设置是否成功
        """
        if not self.is_connected():
            return False
        
        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # 验证设置
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if actual_width == width and actual_height == height:
                self.width = width
                self.height = height
                self.logger.info(f"分辨率设置为: {width}x{height}")
                return True
            else:
                self.logger.warning(f"分辨率设置失败，实际: {actual_width}x{actual_height}")
                return False
                
        except Exception as e:
            self.logger.error(f"设置分辨率失败: {e}")
            return False
    
    def adjust_exposure(self, exposure_value: float) -> bool:
        """
        调整曝光值
        
        Args:
            exposure_value: 曝光值
        
        Returns:
            调整是否成功
        """
        if not self.is_connected():
            return False
        
        try:
            # 关闭自动曝光
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
            # 设置曝光值
            self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure_value)
            
            self.logger.info(f"曝光值设置为: {exposure_value}")
            return True
            
        except Exception as e:
            self.logger.error(f"调整曝光失败: {e}")
            return False
    
    def reset_to_auto(self):
        """重置为自动模式"""
        if not self.is_connected():
            return
        
        try:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            self.logger.info("已重置为自动曝光模式")
        except Exception as e:
            self.logger.error(f"重置自动模式失败: {e}")
    
    def _should_use_virtual_mode(self) -> bool:
        """检测是否应该使用虚拟模式"""
        # 检查是否有摄像头设备
        try:
            cap = cv2.VideoCapture(self.device_id)
            if cap.isOpened():
                cap.release()
                return False
            else:
                return True
        except:
            return True
    
    def _load_virtual_images(self):
        """加载虚拟图像"""
        if not self.virtual_mode:
            return
        
        # 从数据集中加载示例图像
        data_dir = Path(__file__).parent.parent.parent / "data"
        image_paths = []
        
        # 遍历所有垃圾类别目录
        for category_dir in data_dir.glob("*/"):
            if category_dir.is_dir():
                # 获取每个类别的前几张图片
                for img_path in list(category_dir.glob("*.jpg"))[:3]:
                    image_paths.append(img_path)
        
        # 加载图像
        for img_path in image_paths:
            try:
                img = cv2.imread(str(img_path))
                if img is not None:
                    # 调整图像大小
                    img = cv2.resize(img, (self.width, self.height))
                    self.virtual_images.append(img)
            except Exception as e:
                self.logger.warning(f"加载虚拟图像失败: {img_path}, {e}")
        
        # 如果没有找到图像，生成测试图像
        if not self.virtual_images:
            self._generate_test_images()
        
        self.logger.info(f"加载了 {len(self.virtual_images)} 张虚拟图像")
    
    def _generate_test_images(self):
        """生成测试图像"""
        # 生成不同颜色的测试图像
        colors = [
            (255, 0, 0),    # 蓝色
            (0, 255, 0),    # 绿色
            (0, 0, 255),    # 红色
            (255, 255, 0),  # 青色
            (255, 0, 255),  # 品红
            (0, 255, 255),  # 黄色
        ]
        
        for i, color in enumerate(colors):
            img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            img[:] = color
            
            # 添加文字
            text = f"Virtual Camera {i+1}"
            cv2.putText(img, text, (50, self.height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # 添加时间戳区域
            cv2.rectangle(img, (10, 10), (300, 50), (0, 0, 0), -1)
            
            self.virtual_images.append(img)
    
    def _virtual_capture_loop(self):
        """虚拟摄像头采集循环"""
        while self.is_running:
            try:
                # 生成虚拟帧
                frame = self._generate_virtual_frame()
                
                if frame is not None:
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                    
                    # 更新统计信息
                    self.frame_count += 1
                    current_time = time.time()
                    
                    if self.last_frame_time > 0:
                        time_diff = current_time - self.last_frame_time
                        if time_diff > 0:
                            self.actual_fps = 1.0 / time_diff
                    
                    self.last_frame_time = current_time
                
                # 控制帧率
                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                self.logger.error(f"虚拟摄像头采集错误: {e}")
                time.sleep(0.1)
    
    def _generate_virtual_frame(self) -> Optional[np.ndarray]:
        """生成虚拟帧"""
        if not self.virtual_images:
            return None
        
        # 循环使用虚拟图像
        frame = self.virtual_images[self.virtual_image_index].copy()
        self.virtual_image_index = (self.virtual_image_index + 1) % len(self.virtual_images)
        
        # 添加时间戳
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (15, 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 添加帧计数
        frame_text = f"Frame: {self.frame_count}"
        cv2.putText(frame, frame_text, (15, self.height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 添加虚拟模式标识
        cv2.putText(frame, "VIRTUAL CAMERA", (self.width - 200, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        return frame
    
    def is_virtual_mode(self) -> bool:
        """检查是否为虚拟模式"""
        return self.virtual_mode
    
    def switch_to_virtual_mode(self):
        """切换到虚拟模式"""
        if not self.virtual_mode:
            self.stop()
            self.virtual_mode = True
            self._load_virtual_images()
            self.logger.info("已切换到虚拟摄像头模式")
    
    def __del__(self):
        """析构函数"""
        self.stop() 