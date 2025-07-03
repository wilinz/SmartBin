#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Web应用主文件
垃圾分拣系统的Web界面
"""

# ===== 修复PyTorch 2.6权重加载问题 =====
import os
os.environ['TORCH_WEIGHTS_ONLY'] = 'False'

import torch
# 全局修复torch.load函数
if not hasattr(torch, '_original_load'):
    torch._original_load = torch.load
    
    def patched_torch_load(*args, **kwargs):
        # 移除weights_only参数并强制设为False
        kwargs.pop('weights_only', None)
        return torch._original_load(*args, weights_only=False, **kwargs)
    
    torch.load = patched_torch_load

# 添加安全全局变量
if hasattr(torch, 'serialization'):
    try:
        torch.serialization.add_safe_globals([
            'ultralytics.nn.tasks.DetectionModel',
            'ultralytics.nn.modules.block.C2f',
            'ultralytics.nn.modules.block.SPPF', 
            'ultralytics.nn.modules.conv.Conv',
            'ultralytics.nn.modules.head.Detect'
        ])
    except Exception:
        pass

print("🔧 PyTorch权重加载修复已应用到Flask应用")
# ===== 修复结束 =====

import sys
import logging
from pathlib import Path
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import cv2
import numpy as np
import base64
import threading
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ..utils.config_loader import config_loader
from ..models.detector import GarbageDetector
from ..models.trainer import ModelTrainer
from ..hardware.camera import CameraController
from ..system.controller import SystemController


class WebApp:
    """Web应用类"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_config()
        self.setup_cors()
        self.setup_logging()
        
        # 初始化组件
        self.detector = None
        self.trainer = None
        self.camera = None
        self.robot_arm = None
        self.system_controller = None
        
        # 状态变量
        self.detection_active = False
        self.training_active = False
        
        # 初始化虚拟机械臂
        self.setup_robot_arm()
        
        # 设置路由
        self.setup_routes()
    
    def setup_config(self):
        """设置应用配置"""
        web_config = config_loader.get_web_server_config()
        
        self.app.config['SECRET_KEY'] = 'smartbin_garbage_sorting_system'
        self.app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
        self.app.config['UPLOAD_FOLDER'] = 'uploads'
        
        # 创建上传目录
        upload_dir = Path(self.app.config['UPLOAD_FOLDER'])
        upload_dir.mkdir(exist_ok=True)
    
    def setup_cors(self):
        """设置跨域访问 - 前后端分离模式"""
        CORS(self.app, 
             origins=["*"],  # 开发环境允许所有域名
             methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
             supports_credentials=False)  # 设为False避免某些浏览器限制
    
    def setup_logging(self):
        """设置日志"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'web_app.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_robot_arm(self):
        """初始化机械臂控制系统"""
        try:
            from ..hardware.robot_arm import create_robot_arm_controller, get_arm_type_info
            
            # 获取配置的机械臂类型（默认使用虚拟机械臂）
            arm_type = 'virtual'
            arm_config = {}
            
            # 创建机械臂控制器实例
            self.robot_arm = create_robot_arm_controller(arm_type, arm_config)
            
            # 获取机械臂类型信息
            arm_info = get_arm_type_info(arm_type)
            self.logger.info(f"🤖 机械臂类型: {arm_info['name']}")
            self.logger.info(f"📋 功能特性: {', '.join(arm_info['features'])}")
            
            # 自动连接机械臂
            if self.robot_arm.connect():
                self.logger.info("🦾 机械臂初始化成功并已连接")
                
                # 自动归位
                if self.robot_arm.home():
                    self.logger.info("🏠 机械臂已归位")
                
                # 获取机械臂配置信息
                config = self.robot_arm.get_configuration()
                if config:
                    self.logger.info(f"⚙️ 机械臂配置: 最大半径 {config.max_reach}mm, 最大负载 {config.max_payload}kg")
                
                # 如果是虚拟机械臂，打印垃圾桶配置信息
                if arm_type == 'virtual':
                    bins_info = self.robot_arm.get_garbage_bins_info()
                    self.logger.info(f"🗑️ 已配置 {len(bins_info)} 个垃圾桶:")
                    for name, info in bins_info.items():
                        pos = info['position']
                        self.logger.info(f"  • {info['name']}: ({pos['x']:.1f}, {pos['y']:.1f}, {pos['z']:.1f})")
            else:
                self.logger.error("❌ 机械臂连接失败")
                
        except Exception as e:
            self.logger.error(f"❌ 机械臂初始化失败: {e}")
            self.robot_arm = None
    
    def setup_routes(self):
        """设置路由"""
        
        # API根路径
        @self.app.route('/')
        def api_root():
            """API根路径 - 返回系统信息"""
            return jsonify({
                'name': 'SmartBin 垃圾分拣系统 API',
                'version': '1.0.0',
                'description': '智能垃圾分拣系统后端API',
                'status': 'running',
                'endpoints': {
                    'status': '/api/status',
                    'detection': '/api/detect_image',
                    'video_feed': '/video_feed',
                    'model_load': '/api/load_model',
                    'training': '/api/start_training',
                    'start_detection': '/api/start_detection',
                    'stop_detection': '/api/stop_detection',
                    'robot_arm': {
                        'grab': '/api/robot_arm/grab',
                        'status': '/api/robot_arm/status',
                        'home': '/api/robot_arm/home',
                        'emergency_stop': '/api/robot_arm/emergency_stop',
                        'statistics': '/api/robot_arm/statistics',
                        'reset_stats': '/api/robot_arm/reset_stats',
                        'test_sort': '/api/robot_arm/test_sort/<garbage_type>'
                    }
                },
                'frontend_url': 'http://localhost:3000'
            })
        
        # API路由
        @self.app.route('/api/status')
        def api_status():
            """获取系统状态"""
            import traceback
            try:
                status = {
                    'detector_loaded': self.detector is not None and self.detector.model is not None,
                    'training_active': self.training_active,
                }
                
                # 安全地获取机械臂连接状态
                try:
                    if self.robot_arm is not None:
                        status['robot_arm_connected'] = self.robot_arm.is_connected
                    else:
                        status['robot_arm_connected'] = False
                except Exception as arm_conn_e:
                    self.logger.error(f"获取机械臂连接状态失败: {arm_conn_e}")
                    self.logger.error(f"详细错误: {traceback.format_exc()}")
                    status['robot_arm_connected'] = False
                
                status['system_ready'] = True
                
                # 安全地添加机械臂详细状态
                try:
                    if self.robot_arm is not None:
                        arm_status = self.robot_arm.get_status()
                        status['robot_arm_status'] = arm_status
                except Exception as arm_status_e:
                    self.logger.error(f"获取机械臂状态失败: {arm_status_e}")
                    self.logger.error(f"详细错误: {traceback.format_exc()}")
                    status['robot_arm_status'] = {'error': str(arm_status_e)}
                
                return jsonify(status)
            except Exception as e:
                self.logger.error(f"获取状态失败: {e}")
                self.logger.error(f"完整错误堆栈: {traceback.format_exc()}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/load_model', methods=['POST'])
        def api_load_model():
            """加载检测模型"""
            try:
                data = request.get_json()
                model_path = data.get('model_path')
                
                if not model_path or not Path(model_path).exists():
                    return jsonify({'error': '模型文件不存在'}), 400
                
                self.detector = GarbageDetector(model_path)
                
                return jsonify({
                    'success': True,
                    'message': f'模型 {model_path} 加载成功'
                })
                
            except Exception as e:
                self.logger.error(f"加载模型失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/detect_image', methods=['POST'])
        def api_detect_image():
            """检测上传的图像"""
            try:
                if 'image' not in request.files:
                    return jsonify({'error': '没有上传图像'}), 400
                
                if self.detector is None:
                    return jsonify({'error': '检测模型未加载'}), 400
                
                file = request.files['image']
                if file.filename == '':
                    return jsonify({'error': '文件名为空'}), 400
                
                # 读取图像
                file_bytes = np.frombuffer(file.read(), np.uint8)
                image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                
                if image is None:
                    return jsonify({'error': '无法解码图像'}), 400
                
                # 执行检测
                result_image, detection_results = self.detector.detect_and_draw(image)
                
                # 转换为base64
                _, buffer = cv2.imencode('.jpg', result_image)
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # 转换检测结果格式以匹配前端期望
                formatted_results = []
                if 'detections' in detection_results:
                    for detection in detection_results['detections']:
                        formatted_results.append({
                            'class': detection['class_name'],
                            'confidence': detection['confidence'],
                            'bbox': [
                                detection['bbox']['x1'],
                                detection['bbox']['y1'], 
                                detection['bbox']['x2'],
                                detection['bbox']['y2']
                            ],
                            'category': detection['category']
                        })
                
                return jsonify({
                    'success': True,
                    'image': f'data:image/jpeg;base64,{img_base64}',
                    'results': formatted_results,
                    'total_detections': detection_results.get('total_detections', 0),
                    'category_counts': detection_results.get('category_counts', {})
                })
                
            except Exception as e:
                self.logger.error(f"图像检测失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/start_detection')
        def api_start_detection():
            """开始实时检测"""
            try:
                if self.detector is None:
                    return jsonify({'error': '检测模型未加载'}), 400
                
                if self.camera is None:
                    self.camera = CameraController()
                
                if not self.camera.start():
                    return jsonify({'error': '摄像头启动失败'}), 500
                
                self.detection_active = True
                
                return jsonify({
                    'success': True,
                    'message': '实时检测已开始'
                })
                
            except Exception as e:
                self.logger.error(f"开始检测失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stop_detection')
        def api_stop_detection():
            """停止实时检测"""
            try:
                self.detection_active = False
                
                if self.camera:
                    self.camera.stop()
                
                return jsonify({
                    'success': True,
                    'message': '实时检测已停止'
                })
                
            except Exception as e:
                self.logger.error(f"停止检测失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/detection_stats')
        def api_detection_stats():
            """获取检测统计信息"""
            try:
                if self.detector is None:
                    return jsonify({'error': '检测模型未加载'}), 400
                
                stats = self.detector.get_detection_statistics()
                return jsonify(stats)
                
            except Exception as e:
                self.logger.error(f"获取统计信息失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/start_training', methods=['POST'])
        def api_start_training():
            """开始模型训练"""
            try:
                if self.training_active:
                    return jsonify({'error': '训练已在进行中'}), 400
                
                data = request.get_json()
                dataset_path = data.get('dataset_path', 'dataset/dataset.yaml')
                
                if not Path(dataset_path).exists():
                    return jsonify({'error': '数据集配置文件不存在'}), 400
                
                # 在后台线程中启动训练
                def train_model():
                    try:
                        self.training_active = True
                        self.trainer = ModelTrainer()
                        results = self.trainer.train(dataset_path)
                        self.logger.info(f"训练完成: {results}")
                    except Exception as e:
                        self.logger.error(f"训练失败: {e}")
                    finally:
                        self.training_active = False
                
                training_thread = threading.Thread(target=train_model)
                training_thread.daemon = True
                training_thread.start()
                
                return jsonify({
                    'success': True,
                    'message': '模型训练已开始'
                })
                
            except Exception as e:
                self.logger.error(f"开始训练失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/training_progress')
        def api_training_progress():
            """获取训练进度"""
            try:
                if self.trainer is None:
                    return jsonify({'status': '未开始训练'})
                
                progress = self.trainer.get_training_progress()
                progress['active'] = self.training_active
                
                return jsonify(progress)
                
            except Exception as e:
                self.logger.error(f"获取训练进度失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/grab', methods=['POST'])
        def api_robot_arm_grab():
            """机械臂抓取指令"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                if not self.robot_arm.is_connected:
                    return jsonify({'error': '机械臂未连接'}), 400
                
                # 检查机械臂状态，确保不在执行其他操作
                status = self.robot_arm.get_status()
                current_status = status.get('status', 'unknown')
                
                if current_status != 'idle':
                    return jsonify({
                        'error': f'机械臂正在执行操作，当前状态: {current_status}',
                        'current_status': current_status,
                        'message': '请等待当前操作完成后再试'
                    }), 409  # 409 Conflict
                
                data = request.get_json()
                target = data.get('target')
                
                if not target:
                    return jsonify({'error': '缺少目标信息'}), 400
                
                self.logger.info(f"🎯 接收到抓取指令: {target}")
                
                # 执行抓取动作
                success = self.robot_arm.grab_object(
                    target_class=target['class'],
                    confidence=target['confidence'],
                    position=target['center'],
                    bbox=target['bbox']
                )
                
                if success:
                    # 获取最新统计信息
                    stats = self.robot_arm.get_statistics()
                    return jsonify({
                        'success': True,
                        'message': f'机械臂成功抓取 {target["class"]}',
                        'target': target,
                        'statistics': stats
                    })
                else:
                    return jsonify({'error': '机械臂执行失败'}), 500
                
            except Exception as e:
                self.logger.error(f"机械臂控制失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/status')
        def api_robot_arm_status():
            """获取机械臂状态"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                status = self.robot_arm.get_status()
                statistics = self.robot_arm.get_statistics()
                bins_info = self.robot_arm.get_garbage_bins_info()
                
                return jsonify({
                    'status': status,
                    'statistics': statistics,
                    'garbage_bins': bins_info,
                    'is_ready': self.robot_arm.is_connected and status['status'] == 'idle'
                })
                
            except Exception as e:
                self.logger.error(f"获取机械臂状态失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/home', methods=['POST'])
        def api_robot_arm_home():
            """机械臂归位"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                if not self.robot_arm.is_connected:
                    return jsonify({'error': '机械臂未连接'}), 400
                
                # 检查机械臂状态（归位操作可以在大部分状态下执行，除了正在移动时）
                status = self.robot_arm.get_status()
                current_status = status.get('status', 'unknown')
                
                if current_status == 'moving':
                    return jsonify({
                        'error': '机械臂正在移动中，无法执行归位操作',
                        'current_status': current_status,
                        'message': '请等待当前移动完成后再试'
                    }), 409
                
                success = self.robot_arm.home()
                if success:
                    return jsonify({
                        'success': True,
                        'message': '机械臂已归位'
                    })
                else:
                    return jsonify({'error': '归位失败'}), 500
                    
            except Exception as e:
                self.logger.error(f"机械臂归位失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/emergency_stop', methods=['POST'])
        def api_robot_arm_emergency_stop():
            """机械臂紧急停止"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                success = self.robot_arm.emergency_stop()
                if success:
                    return jsonify({
                        'success': True,
                        'message': '🚨 紧急停止已执行'
                    })
                else:
                    return jsonify({'error': '紧急停止失败'}), 500
                    
            except Exception as e:
                self.logger.error(f"紧急停止失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/statistics')
        def api_robot_arm_statistics():
            """获取机械臂统计信息"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                stats = self.robot_arm.get_statistics()
                history = self.robot_arm.get_operation_history(20)  # 最近20次操作
                
                return jsonify({
                    'statistics': stats,
                    'operation_history': history
                })
                
            except Exception as e:
                self.logger.error(f"获取统计信息失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/reset_stats', methods=['POST'])
        def api_robot_arm_reset_stats():
            """重置机械臂统计信息"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                success = self.robot_arm.reset_statistics()
                if success:
                    return jsonify({
                        'success': True,
                        'message': '统计信息已重置'
                    })
                else:
                    return jsonify({'error': '重置失败'}), 500
                    
            except Exception as e:
                self.logger.error(f"重置统计信息失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/test_sort/<garbage_type>', methods=['POST'])
        def api_robot_arm_test_sort(garbage_type):
            """测试垃圾分拣（调试用）"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                if not self.robot_arm.is_connected:
                    return jsonify({'error': '机械臂未连接'}), 400
                
                # 检查机械臂状态，确保不在执行其他操作
                status = self.robot_arm.get_status()
                current_status = status.get('status', 'unknown')
                
                if current_status != 'idle':
                    return jsonify({
                        'error': f'机械臂正在执行操作，当前状态: {current_status}',
                        'current_status': current_status,
                        'message': '请等待当前操作完成后再试'
                    }), 409
                
                self.logger.info(f"🧪 测试分拣垃圾类型: {garbage_type}")
                
                success = self.robot_arm.sort_garbage(garbage_type)
                if success:
                    stats = self.robot_arm.get_statistics()
                    return jsonify({
                        'success': True,
                        'message': f'测试分拣 {garbage_type} 成功',
                        'statistics': stats
                    })
                else:
                    return jsonify({'error': f'分拣 {garbage_type} 失败'}), 500
                    
            except Exception as e:
                self.logger.error(f"测试分拣失败: {e}")
                return jsonify({'error': str(e)}), 500

        # ==================== 机械臂管理接口 ====================
        
        @self.app.route('/api/robot_arm/types')
        def api_robot_arm_types():
            """获取支持的机械臂类型列表"""
            try:
                from ..hardware.robot_arm import get_supported_arm_types, get_arm_type_info
                
                arm_types = get_supported_arm_types()
                types_info = []
                
                for arm_type in arm_types:
                    info = get_arm_type_info(arm_type)
                    types_info.append({
                        'type': arm_type,
                        'name': info['name'],
                        'description': info['description'],
                        'features': info['features'],
                        'config_required': info['config_required'],
                        'config_fields': info.get('config_fields', []),
                        'available': self._check_arm_type_availability(arm_type)
                    })
                
                return jsonify({
                    'success': True,
                    'types': types_info,
                    'current_type': self.robot_arm.arm_type if self.robot_arm else None
                })
                
            except Exception as e:
                self.logger.error(f"获取机械臂类型失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/current_config')
        def api_robot_arm_current_config():
            """获取当前机械臂配置"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                from ..hardware.robot_arm import get_arm_type_info
                
                arm_info = get_arm_type_info(self.robot_arm.arm_type)
                config = self.robot_arm.get_configuration()
                status = self.robot_arm.get_status()
                
                return jsonify({
                    'success': True,
                    'current_type': self.robot_arm.arm_type,
                    'type_info': arm_info,
                    'configuration': {
                        'max_reach': config.max_reach if config else 0,
                        'max_payload': config.max_payload if config else 0,
                        'degrees_of_freedom': config.degrees_of_freedom if config else 0,
                        'max_speed': config.max_speed if config else 0,
                        'acceleration': config.acceleration if config else 0,
                        'precision': config.precision if config else 0
                    } if config else {},
                    'status': status,
                    'connection_config': self.robot_arm.config
                })
                
            except Exception as e:
                self.logger.error(f"获取机械臂配置失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/switch_type', methods=['POST'])
        def api_robot_arm_switch_type():
            """切换机械臂类型"""
            try:
                data = request.get_json()
                new_arm_type = data.get('arm_type')
                new_config = data.get('config', {})
                
                if not new_arm_type:
                    return jsonify({'error': '请指定机械臂类型'}), 400
                
                self.logger.info(f"🔄 切换机械臂类型: {new_arm_type}")
                
                # 检查新类型的可用性
                if not self._check_arm_type_availability(new_arm_type):
                    return jsonify({'error': f'机械臂类型 {new_arm_type} 不可用'}), 400
                
                # 如果有现有机械臂，先断开连接
                if self.robot_arm and hasattr(self.robot_arm, 'disconnect'):
                    self.robot_arm.disconnect()
                
                # 创建新的机械臂实例
                from ..hardware.robot_arm import create_robot_arm_controller
                new_config['arm_type'] = new_arm_type
                
                try:
                    new_robot_arm = create_robot_arm_controller(new_arm_type, new_config)
                    
                    # 尝试连接新机械臂
                    if new_robot_arm.connect():
                        # 成功连接，替换当前机械臂
                        self.robot_arm = new_robot_arm
                        
                        # 尝试归位
                        if hasattr(self.robot_arm, 'home'):
                            self.robot_arm.home()
                        
                        self.logger.info(f"✅ 机械臂切换成功: {new_arm_type}")
                        
                        return jsonify({
                            'success': True,
                            'message': f'机械臂已切换到 {new_arm_type}',
                            'new_type': new_arm_type,
                            'status': self.robot_arm.get_status()
                        })
                    else:
                        return jsonify({'error': f'无法连接到 {new_arm_type} 机械臂'}), 500
                        
                except Exception as create_error:
                    self.logger.error(f"创建机械臂实例失败: {create_error}")
                    return jsonify({'error': f'创建机械臂实例失败: {str(create_error)}'}), 500
                
            except Exception as e:
                self.logger.error(f"切换机械臂类型失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/connect', methods=['POST'])
        def api_robot_arm_connect():
            """连接机械臂"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                if self.robot_arm.is_connected:
                    return jsonify({'message': '机械臂已连接'})
                
                if self.robot_arm.connect():
                    # 连接成功后尝试归位
                    if hasattr(self.robot_arm, 'home'):
                        self.robot_arm.home()
                    
                    return jsonify({
                        'success': True,
                        'message': '机械臂连接成功',
                        'status': self.robot_arm.get_status()
                    })
                else:
                    return jsonify({'error': '机械臂连接失败'}), 500
                
            except Exception as e:
                self.logger.error(f"连接机械臂失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/robot_arm/disconnect', methods=['POST'])
        def api_robot_arm_disconnect():
            """断开机械臂连接"""
            try:
                if self.robot_arm is None:
                    return jsonify({'error': '机械臂未初始化'}), 400
                
                if not self.robot_arm.is_connected:
                    return jsonify({'message': '机械臂已断开连接'})
                
                if self.robot_arm.disconnect():
                    return jsonify({
                        'success': True,
                        'message': '机械臂已断开连接',
                        'status': self.robot_arm.get_status()
                    })
                else:
                    return jsonify({'error': '断开连接失败'}), 500
                
            except Exception as e:
                self.logger.error(f"断开机械臂连接失败: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/video_feed')
        def video_feed():
            """视频流"""
            return Response(self.generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def _check_arm_type_availability(self, arm_type: str) -> bool:
        """检查机械臂类型的可用性"""
        try:
            from ..hardware.robot_arm_interface import create_robot_arm
            # 尝试创建实例来检查可用性
            test_instance = create_robot_arm(arm_type, {'test_mode': True})
            return test_instance is not None
        except Exception:
            return False

    def generate_frames(self):
        """生成视频帧"""
        while True:
            try:
                if not self.detection_active or self.camera is None or self.detector is None:
                    time.sleep(0.1)
                    continue
                
                # 获取摄像头帧
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # 执行检测并绘制结果
                result_frame, _ = self.detector.detect_and_draw(frame)
                
                # 编码为JPEG
                _, buffer = cv2.imencode('.jpg', result_frame)
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
            except Exception as e:
                self.logger.error(f"视频流生成失败: {e}")
                time.sleep(1)
    
    def get_app(self):
        """获取Flask应用实例"""
        return self.app


def create_app():
    """创建Flask应用"""
    web_app = WebApp()
    return web_app.get_app()


# 用于直接运行
if __name__ == '__main__':
    app = create_app()
    
    # 获取配置
    web_config = config_loader.get_web_server_config()
    host = web_config.get('host', '0.0.0.0')
    port = web_config.get('port', 5000)
    debug = web_config.get('debug', True)
    
    print(f"启动Web服务器: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True) 