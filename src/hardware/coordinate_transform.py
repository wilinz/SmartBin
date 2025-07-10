#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐标转换模块
基于 uarm_demo/uarm_demo.py 中的 TransForm 类实现
用于将图像坐标转换为机械臂坐标
"""

import numpy as np
import cv2
from typing import Tuple, Optional, List


class CoordinateTransform:
    """
    坐标转换类
    
    使用单应性矩阵（Homography Matrix）进行图像坐标到机械臂坐标的转换
    """
    
    def __init__(self, camera_coordinates=None, robot_coordinates=None):
        """
        初始化坐标转换器
        
        Args:
            camera_coordinates: 图像四个角点的坐标 (左上, 右上, 右下, 左下)
            robot_coordinates: 机械臂对应四个点的坐标 (左上, 右上, 右下, 左下)
        """
        # 默认使用 uarm_demo.py 中的坐标点
        self.camera_points = np.array([
            [0, 0],     # 左上
            [640, 0],   # 右上
            [640, 480], # 右下
            [0, 480]    # 左下
        ], dtype=np.float32) if camera_coordinates is None else np.array(camera_coordinates, dtype=np.float32)
        
        self.robot_points = np.array([
            [91.3, -99.5],   # 左上
            [88.4, 35.5],    # 右上
            [205.7, 40.9],   # 右下
            [211.5, -120.2]  # 左下
        ], dtype=np.float32) if robot_coordinates is None else np.array(robot_coordinates, dtype=np.float32)
        
        # 计算单应性矩阵
        self.H, _ = cv2.findHomography(self.camera_points, self.robot_points)
        print(f"✅ 单应性矩阵计算完成:\n{self.H}")
        
        # 计算图像中心在机械臂坐标系中的位置
        self.center_point = self.convert_coordinate(320, 240)
        print(f"✅ 图像中心在机械臂坐标系中的位置: {self.center_point}")
    
    def convert_coordinate(self, x: float, y: float) -> Tuple[float, float]:
        """
        将图像坐标转换为机械臂坐标
        
        Args:
            x: 图像x坐标
            y: 图像y坐标
            
        Returns:
            tuple: (机械臂x坐标, 机械臂y坐标)
        """
        # 使用单应性矩阵转换坐标
        point = np.array([[x, y]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point.reshape(1, -1, 2), self.H)
        
        # 返回转换后的坐标
        return float(transformed[0][0][0]), float(transformed[0][0][1])
    
    def get_coordinate(self, img, x: float, y: float) -> Tuple[float, float]:
        """
        从图像和图像中的点获取机械臂坐标
        
        Args:
            img: 图像（用于获取尺寸信息，但这里我们直接使用坐标点）
            x: 图像x坐标
            y: 图像y坐标
            
        Returns:
            tuple: (机械臂x坐标, 机械臂y坐标)
        """
        return self.convert_coordinate(x, y)
    
    def convert_multiple_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        批量转换多个坐标点
        
        Args:
            points: 图像坐标点列表 [(x1, y1), (x2, y2), ...]
            
        Returns:
            list: 机械臂坐标点列表 [(x1, y1), (x2, y2), ...]
        """
        if not points:
            return []
        
        # 将点转换为numpy数组
        points_array = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
        
        # 批量转换
        transformed = cv2.perspectiveTransform(points_array, self.H)
        
        # 转换回列表格式
        result = []
        for point in transformed:
            result.append((float(point[0][0]), float(point[0][1])))
        
        return result
    
    def update_calibration(self, camera_points: List[Tuple[float, float]], 
                          robot_points: List[Tuple[float, float]]) -> bool:
        """
        更新标定参数
        
        Args:
            camera_points: 新的图像坐标点
            robot_points: 新的机械臂坐标点
            
        Returns:
            bool: 更新成功返回True
        """
        try:
            self.camera_points = np.array(camera_points, dtype=np.float32)
            self.robot_points = np.array(robot_points, dtype=np.float32)
            
            # 重新计算单应性矩阵
            self.H, _ = cv2.findHomography(self.camera_points, self.robot_points)
            
            # 重新计算图像中心位置
            self.center_point = self.convert_coordinate(320, 240)
            
            print(f"✅ 标定参数更新完成")
            print(f"✅ 新的单应性矩阵:\n{self.H}")
            print(f"✅ 新的图像中心位置: {self.center_point}")
            
            return True
        except Exception as e:
            print(f"❌ 标定参数更新失败: {e}")
            return False
    
    def get_transform_matrix(self) -> np.ndarray:
        """
        获取单应性矩阵
        
        Returns:
            np.ndarray: 单应性矩阵
        """
        return self.H.copy()
    
    def get_calibration_points(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取标定点
        
        Returns:
            tuple: (图像坐标点, 机械臂坐标点)
        """
        return self.camera_points.copy(), self.robot_points.copy()
    
    def validate_transform(self) -> bool:
        """
        验证坐标转换的有效性
        
        Returns:
            bool: 转换有效返回True
        """
        try:
            # 测试转换几个关键点
            test_points = [
                (0, 0),       # 左上角
                (640, 0),     # 右上角
                (640, 480),   # 右下角
                (0, 480),     # 左下角
                (320, 240)    # 中心点
            ]
            
            transformed = self.convert_multiple_points(test_points)
            
            print("🔍 坐标转换验证:")
            for i, (original, transformed_point) in enumerate(zip(test_points, transformed)):
                print(f"  图像坐标 {original} -> 机械臂坐标 {transformed_point}")
            
            return True
        except Exception as e:
            print(f"❌ 坐标转换验证失败: {e}")
            return False
    
    def is_point_in_workspace(self, robot_x: float, robot_y: float, 
                             workspace_bounds: Optional[dict] = None) -> bool:
        """
        检查机械臂坐标是否在工作空间内
        
        Args:
            robot_x: 机械臂x坐标
            robot_y: 机械臂y坐标
            workspace_bounds: 工作空间边界 {'x_min': ?, 'x_max': ?, 'y_min': ?, 'y_max': ?}
            
        Returns:
            bool: 在工作空间内返回True
        """
        if workspace_bounds is None:
            # 默认工作空间边界（基于uArm的工作范围）
            workspace_bounds = {
                'x_min': 0,
                'x_max': 300,
                'y_min': -150,
                'y_max': 150
            }
        
        return (workspace_bounds['x_min'] <= robot_x <= workspace_bounds['x_max'] and
                workspace_bounds['y_min'] <= robot_y <= workspace_bounds['y_max'])
    
    def get_safe_coordinate(self, x: float, y: float) -> Optional[Tuple[float, float]]:
        """
        获取安全的机械臂坐标（确保在工作空间内）
        
        Args:
            x: 图像x坐标
            y: 图像y坐标
            
        Returns:
            tuple: 安全的机械臂坐标，如果超出工作空间则返回None
        """
        robot_x, robot_y = self.convert_coordinate(x, y)
        
        if self.is_point_in_workspace(robot_x, robot_y):
            return robot_x, robot_y
        else:
            print(f"⚠️ 坐标 ({robot_x}, {robot_y}) 超出工作空间")
            return None


def test_coordinate_transform():
    """测试坐标转换功能"""
    print("🧪 测试坐标转换功能")
    print("=" * 30)
    
    # 创建坐标转换器
    transformer = CoordinateTransform()
    
    # 验证转换
    transformer.validate_transform()
    
    # 测试单点转换
    print("\n📍 测试单点转换:")
    test_points = [
        (100, 100),
        (200, 200),
        (300, 300),
        (400, 400)
    ]
    
    for x, y in test_points:
        robot_x, robot_y = transformer.convert_coordinate(x, y)
        safe_coord = transformer.get_safe_coordinate(x, y)
        print(f"  图像坐标 ({x}, {y}) -> 机械臂坐标 ({robot_x:.2f}, {robot_y:.2f})")
        if safe_coord:
            print(f"    ✅ 在工作空间内")
        else:
            print(f"    ❌ 超出工作空间")
    
    # 测试批量转换
    print("\n📍 测试批量转换:")
    batch_points = [(50, 50), (150, 150), (250, 250)]
    transformed_batch = transformer.convert_multiple_points(batch_points)
    
    for original, transformed in zip(batch_points, transformed_batch):
        print(f"  {original} -> ({transformed[0]:.2f}, {transformed[1]:.2f})")
    
    print("\n✅ 坐标转换测试完成")


if __name__ == "__main__":
    test_coordinate_transform() 