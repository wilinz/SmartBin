#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据预处理模块
负责将Pascal VOC XML格式转换为YOLO格式，并进行数据集划分
支持数据增强以提高模型鲁棒性
"""

import os
import sys
import shutil
import random
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import yaml
from collections import defaultdict, Counter
import cv2
import numpy as np

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.utils.config_loader import ConfigLoader
from src.data_processing.data_augmentor import DataAugmentor


class DataPreprocessor:
    """数据预处理器
    
    主要功能：
    1. Pascal VOC XML格式转换为YOLO TXT格式
    2. 数据集划分（训练/验证/测试）
    3. 数据统计分析
    """
    
    def __init__(self, config_path: str = "config", enable_augmentation: bool = True, augmentation_config: Optional[Dict] = None):
        """初始化数据预处理器
        
        Args:
            config_path: 配置目录路径
            enable_augmentation: 是否启用数据增强
            augmentation_config: 数据增强配置
        """
        self.config_loader = ConfigLoader(config_path)
        self.model_config = self.config_loader.get_model_config()
        self.class_names = self.model_config.get('classes', {}).get('names', [])
        self.class_to_id = {name: idx for idx, name in enumerate(self.class_names)}
        
        # 数据集划分比例
        self.train_ratio = 0.7
        self.val_ratio = 0.2
        self.test_ratio = 0.1
        
        # 数据增强配置
        self.enable_augmentation = enable_augmentation
        if self.enable_augmentation:
            self.augmentor = DataAugmentor(augmentation_config)
            print("✅ 数据增强已启用")
            print(f"📈 每张原图将生成 {self.augmentor.config['augmentation_factor']} 张增强图")
        else:
            self.augmentor = None
            print("⚠️ 数据增强已禁用")
        
        # 统计信息
        self.stats = defaultdict(int)
        
    def parse_xml_annotation(self, xml_path: str) -> List[Dict]:
        """解析Pascal VOC XML标注文件
        
        Args:
            xml_path: XML文件路径
            
        Returns:
            标注信息列表，每个元素包含类别和边界框信息
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 获取图像尺寸
        size = root.find('size')
        img_width = int(size.find('width').text)
        img_height = int(size.find('height').text)
        
        annotations = []
        
        # 解析所有对象
        for obj in root.findall('object'):
            class_name = obj.find('name').text
            
            # 检查类别是否在定义的类别中
            if class_name not in self.class_to_id:
                print(f"警告: 未知类别 '{class_name}' 在文件 {xml_path}")
                continue
                
            class_id = self.class_to_id[class_name]
            
            # 获取边界框坐标
            bbox = obj.find('bndbox')
            xmin = int(bbox.find('xmin').text)
            ymin = int(bbox.find('ymin').text)
            xmax = int(bbox.find('xmax').text)
            ymax = int(bbox.find('ymax').text)
            
            # 转换为YOLO格式 (相对坐标)
            x_center = (xmin + xmax) / 2.0 / img_width
            y_center = (ymin + ymax) / 2.0 / img_height
            width = (xmax - xmin) / img_width
            height = (ymax - ymin) / img_height
            
            annotations.append({
                'class_id': class_id,
                'class_name': class_name,
                'x_center': x_center,
                'y_center': y_center,
                'width': width,
                'height': height
            })
            
            # 更新统计信息
            self.stats['total_objects'] += 1
            self.stats[f'class_{class_name}'] += 1
            
        return annotations
    
    def convert_to_yolo_format(self, data_dir: str, output_dir: str):
        """将Pascal VOC格式转换为YOLO格式
        
        Args:
            data_dir: 原始数据目录
            output_dir: 输出目录
        """
        data_path = Path(data_dir)
        output_path = Path(output_dir)
        
        # 创建输出目录结构
        output_path.mkdir(parents=True, exist_ok=True)
        images_dir = output_path / "images"
        labels_dir = output_path / "labels"
        images_dir.mkdir(exist_ok=True)
        labels_dir.mkdir(exist_ok=True)
        
        print(f"开始转换数据格式...")
        print(f"源目录: {data_path}")
        print(f"输出目录: {output_path}")
        
        # 遍历所有类别文件夹
        converted_count = 0
        error_count = 0
        
        for class_dir in data_path.iterdir():
            if not class_dir.is_dir():
                continue
                
            class_name = class_dir.name
            print(f"处理类别: {class_name}")
            
            # 查找所有XML文件
            xml_files = list(class_dir.glob("*.xml"))
            
            for xml_file in xml_files:
                try:
                    # 查找对应的图像文件
                    img_name = xml_file.stem + ".jpg"
                    img_file = class_dir / img_name
                    
                    if not img_file.exists():
                        print(f"警告: 找不到对应的图像文件: {img_file}")
                        continue
                    
                    # 解析XML标注
                    annotations = self.parse_xml_annotation(str(xml_file))
                    
                    if not annotations:
                        print(f"警告: XML文件中没有有效标注: {xml_file}")
                        continue
                    
                    # 读取图像
                    image = cv2.imread(str(img_file))
                    if image is None:
                        print(f"警告: 无法读取图像文件: {img_file}")
                        continue
                    
                    # 生成唯一的文件名（包含类别信息）
                    base_name = f"{class_name}_{xml_file.stem}"
                    
                    # 如果启用数据增强，生成增强数据
                    if self.enable_augmentation and self.augmentor:
                        try:
                            # 应用数据增强
                            augmented_pairs = self.augmentor.augment_image_with_annotations(image, annotations)
                            
                            # 保存所有增强后的图像和标注
                            for idx, (aug_image, aug_annotations) in enumerate(augmented_pairs):
                                if idx == 0:
                                    # 原始图像
                                    unique_name = base_name
                                else:
                                    # 增强图像
                                    unique_name = f"{base_name}_aug_{idx}"
                                
                                # 保存图像
                                dest_img = images_dir / f"{unique_name}.jpg"
                                cv2.imwrite(str(dest_img), aug_image)
                                
                                # 保存标注
                                label_file = labels_dir / f"{unique_name}.txt"
                                with open(label_file, 'w') as f:
                                    for ann in aug_annotations:
                                        f.write(f"{ann['class_id']} {ann['x_center']:.6f} "
                                               f"{ann['y_center']:.6f} {ann['width']:.6f} "
                                               f"{ann['height']:.6f}\n")
                                
                                converted_count += 1
                        
                        except Exception as e:
                            print(f"数据增强失败，使用原始数据 {xml_file}: {str(e)}")
                            # 降级处理：只保存原始图像
                            dest_img = images_dir / f"{base_name}.jpg"
                            cv2.imwrite(str(dest_img), image)
                            
                            label_file = labels_dir / f"{base_name}.txt"
                            with open(label_file, 'w') as f:
                                for ann in annotations:
                                    f.write(f"{ann['class_id']} {ann['x_center']:.6f} "
                                           f"{ann['y_center']:.6f} {ann['width']:.6f} "
                                           f"{ann['height']:.6f}\n")
                            
                            converted_count += 1
                    else:
                        # 不使用数据增强，直接保存原始图像
                        dest_img = images_dir / f"{base_name}.jpg"
                        cv2.imwrite(str(dest_img), image)
                        
                        label_file = labels_dir / f"{base_name}.txt"
                        with open(label_file, 'w') as f:
                            for ann in annotations:
                                f.write(f"{ann['class_id']} {ann['x_center']:.6f} "
                                       f"{ann['y_center']:.6f} {ann['width']:.6f} "
                                       f"{ann['height']:.6f}\n")
                        
                        converted_count += 1
                    
                except Exception as e:
                    print(f"处理文件时出错 {xml_file}: {str(e)}")
                    error_count += 1
                    continue
        
        print(f"\n转换完成!")
        print(f"成功转换: {converted_count} 个文件")
        print(f"错误数量: {error_count} 个文件")
        
        if self.enable_augmentation:
            original_count = len([f for f in os.listdir(images_dir) if not '_aug_' in f])
            augmented_count = converted_count - original_count
            print(f"原始图像: {original_count} 张")
            print(f"增强图像: {augmented_count} 张")
            print(f"数据增强倍数: {converted_count/original_count:.1f}x" if original_count > 0 else "数据增强倍数: 0x")
        
        self.stats['converted_files'] = converted_count
        self.stats['error_files'] = error_count
    
    def split_dataset(self, dataset_dir: str, output_dir: str):
        """划分数据集为训练/验证/测试集
        
        Args:
            dataset_dir: 转换后的数据集目录
            output_dir: 输出目录
        """
        dataset_path = Path(dataset_dir)
        output_path = Path(output_dir)
        
        images_dir = dataset_path / "images"
        labels_dir = dataset_path / "labels"
        
        # 获取所有图像文件
        image_files = list(images_dir.glob("*.jpg"))
        random.shuffle(image_files)
        
        total_files = len(image_files)
        train_count = int(total_files * self.train_ratio)
        val_count = int(total_files * self.val_ratio)
        
        # 划分数据集
        train_files = image_files[:train_count]
        val_files = image_files[train_count:train_count + val_count]
        test_files = image_files[train_count + val_count:]
        
        print(f"\n数据集划分:")
        print(f"总文件数: {total_files}")
        print(f"训练集: {len(train_files)} ({len(train_files)/total_files*100:.1f}%)")
        print(f"验证集: {len(val_files)} ({len(val_files)/total_files*100:.1f}%)")
        print(f"测试集: {len(test_files)} ({len(test_files)/total_files*100:.1f}%)")
        
        # 创建输出目录结构
        for split in ['train', 'val', 'test']:
            (output_path / split / 'images').mkdir(parents=True, exist_ok=True)
            (output_path / split / 'labels').mkdir(parents=True, exist_ok=True)
        
        # 复制文件到对应目录
        def copy_split_files(files: List[Path], split_name: str):
            split_dir = output_path / split_name
            for img_file in files:
                # 复制图像文件
                dest_img = split_dir / 'images' / img_file.name
                shutil.copy2(img_file, dest_img)
                
                # 复制标签文件
                label_file = labels_dir / (img_file.stem + '.txt')
                if label_file.exists():
                    dest_label = split_dir / 'labels' / (img_file.stem + '.txt')
                    shutil.copy2(label_file, dest_label)
        
        copy_split_files(train_files, 'train')
        copy_split_files(val_files, 'val')
        copy_split_files(test_files, 'test')
        
        # 更新统计信息
        self.stats['train_files'] = len(train_files)
        self.stats['val_files'] = len(val_files)
        self.stats['test_files'] = len(test_files)
        
        # 创建数据集配置文件
        self.create_dataset_yaml(output_path)
    
    def create_dataset_yaml(self, output_dir: Path):
        """创建YOLO数据集配置文件
        
        Args:
            output_dir: 输出目录
        """
        dataset_config = {
            'path': str(output_dir.absolute()),
            'train': 'train/images',
            'val': 'val/images',
            'test': 'test/images',
            'nc': len(self.class_names),
            'names': self.class_names
        }
        
        yaml_file = output_dir / 'dataset.yaml'
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(dataset_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"数据集配置文件已创建: {yaml_file}")
    
    def analyze_dataset(self, dataset_dir: str) -> Dict:
        """分析数据集统计信息
        
        Args:
            dataset_dir: 数据集目录
            
        Returns:
            统计信息字典
        """
        dataset_path = Path(dataset_dir)
        
        # 统计各split的信息
        analysis = {
            'total_images': 0,
            'total_objects': 0,
            'class_distribution': Counter(),
            'splits': {}
        }
        
        for split in ['train', 'val', 'test']:
            split_dir = dataset_path / split
            if not split_dir.exists():
                continue
                
            images_dir = split_dir / 'images'
            labels_dir = split_dir / 'labels'
            
            image_files = list(images_dir.glob('*.jpg'))
            split_info = {
                'image_count': len(image_files),
                'object_count': 0,
                'class_distribution': Counter()
            }
            
            # 统计标签信息
            for img_file in image_files:
                label_file = labels_dir / (img_file.stem + '.txt')
                if label_file.exists():
                    with open(label_file, 'r') as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                class_id = int(parts[0])
                                class_name = self.class_names[class_id]
                                split_info['class_distribution'][class_name] += 1
                                split_info['object_count'] += 1
            
            analysis['splits'][split] = split_info
            analysis['total_images'] += split_info['image_count']
            analysis['total_objects'] += split_info['object_count']
            analysis['class_distribution'].update(split_info['class_distribution'])
        
        return analysis
    
    def print_statistics(self):
        """打印统计信息"""
        print("\n=== 数据预处理统计信息 ===")
        print(f"转换文件数: {self.stats.get('converted_files', 0)}")
        print(f"错误文件数: {self.stats.get('error_files', 0)}")
        print(f"总对象数: {self.stats.get('total_objects', 0)}")
        
        print("\n类别分布:")
        for class_name in self.class_names:
            count = self.stats.get(f'class_{class_name}', 0)
            print(f"  {class_name}: {count}")
        
        if 'train_files' in self.stats:
            print(f"\n数据集划分:")
            print(f"  训练集: {self.stats['train_files']}")
            print(f"  验证集: {self.stats['val_files']}")
            print(f"  测试集: {self.stats['test_files']}")
    
    def process_data(self, source_dir: str, work_dir: str = "datasets"):
        """完整的数据处理流程
        
        Args:
            source_dir: 源数据目录
            work_dir: 工作目录
        """
        work_path = Path(work_dir)
        work_path.mkdir(exist_ok=True)
        
        print("开始数据预处理流程...")
        
        # 步骤1: 格式转换
        converted_dir = work_path / "converted"
        self.convert_to_yolo_format(source_dir, str(converted_dir))
        
        # 步骤2: 数据集划分
        final_dir = work_path / "yolo_dataset"
        self.split_dataset(str(converted_dir), str(final_dir))
        
        # 步骤3: 数据分析
        analysis = self.analyze_dataset(str(final_dir))
        
        # 打印统计信息
        self.print_statistics()
        
        print(f"\n数据预处理完成!")
        print(f"最终数据集位置: {final_dir.absolute()}")
        print(f"数据集配置文件: {final_dir / 'dataset.yaml'}")
        
        return str(final_dir)


if __name__ == "__main__":
    # 测试代码
    preprocessor = DataPreprocessor()
    
    # 处理数据
    source_data_dir = "data"  # 原始数据目录
    final_dataset_dir = preprocessor.process_data(source_data_dir)
    
    print(f"处理完成! 数据集保存在: {final_dataset_dir}") 