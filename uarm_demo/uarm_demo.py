import numpy as np
import cv2
import time
import os
import yaml
import serial
from serial.tools import list_ports
import platform
import math
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

# 类别定义
CLASS_NAMES = [
    "banana", "beverages", "cardboard_box", "chips", "fish_bones",
    "instant_noodles", "milk_box_type1", "milk_box_type2", "plastic"
]

# TensorRT 推理引擎类
class YOLOv8TRT:
    def __init__(self, engine_path, conf_thres=0.5, iou_thres=0.5):
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        
        # 加载TensorRT引擎
        self.logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f, trt.Runtime(self.logger) as runtime:
            self.engine = runtime.deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()
        
        # 获取输入输出绑定信息
        self.input_binding = self.engine[0]
        self.output_binding = self.engine[1]
        self.input_shape = self.engine.get_binding_shape(0)
        print(f"Input shape: {self.input_shape}")
        
        # 分配输入输出缓冲区
        self.inputs, self.outputs, self.bindings, self.stream = self.allocate_buffers()
        
    def allocate_buffers(self):
        inputs = []
        outputs = []
        bindings = []
        stream = cuda.Stream()
        
        # 输入缓冲区
        input_size = trt.volume(self.engine.get_binding_shape(0)) * self.engine.max_batch_size
        input_dtype = trt.nptype(self.engine.get_binding_dtype(0))
        input_host = cuda.pagelocked_empty(input_size, input_dtype)
        input_device = cuda.mem_alloc(input_host.nbytes)
        bindings.append(int(input_device))
        inputs.append({'host': input_host, 'device': input_device})
        
        # 输出缓冲区
        output_size = trt.volume(self.engine.get_binding_shape(1)) * self.engine.max_batch_size
        output_dtype = trt.nptype(self.engine.get_binding_dtype(1))
        output_host = cuda.pagelocked_empty(output_size, output_dtype)
        output_device = cuda.mem_alloc(output_host.nbytes)
        bindings.append(int(output_device))
        outputs.append({'host': output_host, 'device': output_device})
        
        return inputs, outputs, bindings, stream
    
    def preprocess_image(self, image):
        """预处理图像，转换为模型输入格式"""
        # 调整大小并填充保持宽高比
        h, w, _ = image.shape
        scale = min(self.input_shape[2] / h, self.input_shape[3] / w)  # CHW格式
        new_h, new_w = int(h * scale), int(w * scale)
        resized = cv2.resize(image, (new_w, new_h))
        
        # 创建画布并填充
        canvas = np.full((self.input_shape[2], self.input_shape[3], 3), 114, dtype=np.uint8)
        top = (self.input_shape[2] - new_h) // 2
        left = (self.input_shape[3] - new_w) // 2
        canvas[top:top+new_h, left:left+new_w] = resized
        
        # 转换格式并归一化
        canvas = canvas.astype(np.float32) / 255.0
        canvas = np.transpose(canvas, (2, 0, 1))  # HWC to CHW
        return np.ascontiguousarray(canvas), scale, (left, top)
    
    def postprocess(self, outputs, scale, padding, img_shape):
        """后处理检测结果 - 修复版"""
        # 输出形状通常是 [1, 84, 8400] 对于YOLOv8
        output = outputs[0].reshape(1, 4 + len(CLASS_NAMES), -1)  # [1, 13, 8400]
        output = output[0].transpose()  # 转置为 [8400, 13]
        
        # 分离边界框坐标和类别分数
        boxes = output[:, :4]
        scores = output[:, 4:4+len(CLASS_NAMES)]
        
        # 获取最大类别分数和ID
        class_ids = np.argmax(scores, axis=1)
        max_scores = np.max(scores, axis=1)
        
        # 应用置信度阈值
        mask = max_scores > self.conf_thres
        boxes = boxes[mask]
        max_scores = max_scores[mask]
        class_ids = class_ids[mask]
        
        if len(boxes) == 0:
            return []
        
        # 将中心点宽高转换为左上右下坐标
        boxes = self.xywh2xyxy(boxes)
        
        # 调整框坐标到原始图像
        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - padding[0]) / scale
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - padding[1]) / scale
        
        # 裁剪坐标到图像范围内
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, img_shape[1])
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, img_shape[0])
        
        # 应用NMS
        indices = self.nms(boxes, max_scores, self.iou_thres)
        
        # 返回检测结果
        results = []
        for i in indices:
            x1, y1, x2, y2 = boxes[i]
            class_id = class_ids[i]
            score = max_scores[i]
            results.append({
                'box': [x1, y1, x2, y2],
                'class_id': int(class_id),
                'confidence': float(score),
                'class_name': CLASS_NAMES[int(class_id)]
            })
        
        return results
    
    def xywh2xyxy(self, x):
        """将中心点宽高转换为左上右下坐标"""
        y = np.zeros_like(x)
        y[:, 0] = x[:, 0] - x[:, 2] / 2  # 左上x
        y[:, 1] = x[:, 1] - x[:, 3] / 2  # 左上y
        y[:, 2] = x[:, 0] + x[:, 2] / 2  # 右下x
        y[:, 3] = x[:, 1] + x[:, 3] / 2  # 右下y
        return y
    
    def nms(self, boxes, scores, iou_threshold):
        """非极大值抑制 - 使用OpenCV实现"""
        # 转换为OpenCV需要的格式
        boxes_ = boxes.astype(np.float32)
        scores_ = scores.astype(np.float32)
        
        # 使用OpenCV的NMSBoxes
        indices = cv2.dnn.NMSBoxes(boxes_, scores_, self.conf_thres, iou_threshold)
        
        return indices.flatten() if len(indices) > 0 else []
    
    def detect(self, image):
        """执行目标检测"""
        # 预处理
        preprocessed, scale, padding = self.preprocess_image(image)
        img_h, img_w = image.shape[:2]
        
        # 将输入数据复制到GPU
        np.copyto(self.inputs[0]['host'], preprocessed.ravel())
        cuda.memcpy_htod_async(self.inputs[0]['device'], self.inputs[0]['host'], self.stream)
        
        # 执行推理
        self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
        
        # 将输出从GPU复制回主机
        cuda.memcpy_dtoh_async(self.outputs[0]['host'], self.outputs[0]['device'], self.stream)
        self.stream.synchronize()
        
        # 后处理
        output_data = [output['host'] for output in self.outputs]
        results = self.postprocess(output_data, scale, padding, (img_h, img_w))
        
        return results

class TransForm:
    def __init__(self, camera_coordinates=None, robot_coordinates=None):
        """
        初始化坐标转换器
        :param camera_coordinates: 图像四个角点的坐标 (左上, 右上, 右下, 左下)
        :param robot_coordinates: 机械臂对应四个点的坐标 (左上, 右上, 右下, 左下)
        """
        # 默认使用您提供的坐标点
        self.camera_points = np.array([
            [0, 0],     # 左上
            [640, 0],   # 右上
            [640, 480], # 右下
            [0, 480]    # 左下
        ], dtype=np.float32) if camera_coordinates is None else np.array(camera_coordinates, dtype=np.float32)
        
        self.robot_points = np.array([
            #[85.4, -83.6],  # 左上
            #[84.9, 50.2],   # 右上
            #[192.3, 58.0],  # 右下
            #[194.4, -98.6]  # 左下
            [91.3, -99.5],
            [88.4, 35.5],
            [205.7, 40.9],
            [211.5, -120.2]
        ], dtype=np.float32) if robot_coordinates is None else np.array(robot_coordinates, dtype=np.float32)
        
        # 计算单应性矩阵
        self.H, _ = cv2.findHomography(self.camera_points, self.robot_points)
        print(f"Homography matrix:\n{self.H}")
        
        # 计算图像中心在机械臂坐标系中的位置
        self.center_point = self.convertCoordinate(320, 240)
        print(f"Image center in robot coordinates: {self.center_point}")
    
    def convertCoordinate(self, x, y):
        """
        将图像坐标转换为机械臂坐标
        :param x: 图像x坐标
        :param y: 图像y坐标
        :return: (机械臂x坐标, 机械臂y坐标)
        """
        # 使用单应性矩阵转换坐标
        point = np.array([[x, y]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point.reshape(1, -1, 2), self.H)
        
        # 返回转换后的坐标
        return transformed[0][0][0], transformed[0][0][1]
    
    def getCoordinate(self, img, x, y):
        """
        从图像和图像中的点获取机械臂坐标
        :param img: 图像（用于获取尺寸信息，但这里我们直接使用坐标点）
        :param x: 图像x坐标
        :param y: 图像y坐标
        :return: (机械臂x坐标, 机械臂y坐标)
        """
        return self.convertCoordinate(x, y)

# 机械臂控制类
class ArmServo:
    def __init__(self, port=None, baudrate=115200, yaml_path='./resource/arm_polar.yaml'):
        self.port = self.checkport(port)
        self.baudrate = baudrate
        self.arm = self.connect_to_arm()
        
        # 添加load_yaml_data方法调用
        self.arm_polar_val = self.load_yaml_data(yaml_path) if hasattr(self, 'load_yaml_data') else {}
        
        self.polar_height = -8
        self.x_weight = 5.0
        if self.arm:
            self.initialize_arm()
    
    # 添加缺失的load_yaml_data方法
    def load_yaml_data(self, yaml_path):
        """加载YAML配置文件"""
        if not os.path.exists(yaml_path):
            print(f"YAML file not found: {yaml_path}")
            return {}
        
        try:
            with open(yaml_path, 'r') as file:
                data = yaml.safe_load(file)
                print(f"Loaded YAML data from {yaml_path}")
                return data
        except Exception as e:
            print(f"Error loading YAML file: {e}")
            return {}
    
    def checkport(self, COM):
        print('Checking Device...... \n')
        port = None
        if platform.system() == 'Windows':
            plist = list(serial.tools.list_ports.comports())
            if len(plist) <= 0:
                print ("The Serial port can't find!")
            else:
                plist_0 = list(plist[0])
                port = plist_0[0]
                print('Current device: ' + port + '\n')
        else:
            try:
                # 获取机械臂端口信息
                ret = os.popen("ls /dev/serial/by-id").read()
                port = "/dev/serial/by-id/" + ret.split('\n')[0].split('/')[-1]
                # 打印检测到的机械臂端口
                print('Current device: ' + port + '\n')
            except:
                print ("The Serial port can't find!")

        if port is not None:
            return port
        else:   
            return COM
    
    def connect_to_arm(self):
        """连接机械臂 - 使用检测到的端口"""
        if not self.port:
            print("⚠️ No serial port available! Check connections.")
            return None
        
        try:
            print(f"Connecting to {self.port} at {self.baudrate}...")
            ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # 清除缓冲区
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # 测试连接 - 发送M114获取当前位置
            ser.write(b"M114\r\n")
            time.sleep(0.5)  # 给机械臂更多响应时间
            
            # 读取响应
            response = b""
            start_time = time.time()
            while (time.time() - start_time) < 2.0:  # 最多等待2秒
                if ser.in_waiting > 0:
                    response += ser.read(ser.in_waiting)
                    if b'ok' in response or b'X:' in response:
                        break
            
            response = response.decode('utf-8', errors='ignore').strip()
            print(f"Arm response: {response}")
            
            if "X:" in response:
                print(f"✅ Arm connected at {self.port}")
                return ser
            else:
                print(f"⚠️ Invalid response from arm. Trying to connect anyway...")
                return ser  # 即使没有有效响应也尝试继续
                
        except serial.SerialException as e:
            print(f"❌ Connection failed: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return None
    
    # ... 其他方法保持不变 ...
    
    def initialize_arm(self):
        """初始化机械臂位置"""
        if not self.arm:
            return
        
        # 发送初始化指令
        self.send_command("G0 X150 Y0 Z90 F1000")
        time.sleep(2)
        self.send_command("M2231 V0")  # 设置手腕角度
        print("Arm initialized to home position")
    
    def send_command(self, command):
        """发送指令给机械臂"""
        if not self.arm:
            print("Cannot send command: arm not connected")
            return False
        
        try:
            self.arm.write(f"{command}\r\n".encode())
            time.sleep(0.1)
            return True
        except serial.SerialException as e:
            print(f"Error sending command: {e}")
            return False
    
    def move_to_position(self, x, y, z, speed=1000):
        """移动机械臂到指定位置"""
        command = f"G0 X{x} Y{y} Z{z} F{speed}"
        return self.send_command(command)
    
    def set_gripper(self, state):
        """控制机械爪"""
        # 假设M2231控制机械爪，0为打开，1为关闭
        state_code = 1 if state else 0
        command = f"M2232 V{state_code}"
        return self.send_command(command)
    
    def pick_object(self, x, y, class_id):
        """拾取物体并分类放置"""
        if not self.arm:
            return False
        
        # 移动到物体上方
        self.move_to_position(x, y, 50)
        time.sleep(2)
        
        # 下降到物体位置
        self.move_to_position(x, y, self.polar_height)
        time.sleep(2)
        
        # 抓取物体
        self.set_gripper(1)
        time.sleep(2)
        
        # 抬起物体
        self.move_to_position(x, y, 50)
        time.sleep(2)
        
        # 移动到分类区域 (根据类别决定位置)
        target_x, target_y = self.get_classification_position(class_id)
        self.move_to_position(target_x, target_y, 50)
        time.sleep(2)
        
        # 下降到放置高度
        #self.move_to_position(target_x, target_y, self.polar_height)
        #time.sleep(2)
        
        # 释放物体
        self.set_gripper(0)
        time.sleep(2)
        
        # 抬起机械臂
        self.move_to_position(target_x, target_y, 50)
        time.sleep(2)
        
        # 返回初始位置
        self.initialize_arm()
        
        return True
    
    def get_classification_position(self, class_id):
        """根据垃圾类别返回放置位置"""
        # 简化版：根据类别ID映射到不同区域
        positions = [
            (20.6, 127.1),    # 厨余垃圾
            (99.5, 121.7),   # 可回收垃圾
            (189.6, 142.4),   # 有害垃圾
            (189.6, 142.4)   # 其他垃圾
        ]
        
        # 根据类别ID确定垃圾类型
        if class_id in [0, 1, 2]:  # 食物类
            return positions[0]
        elif class_id in [3, 4, 5]:  # 可回收类
            return positions[1]
        elif class_id in [6, 7]:  # 有害垃圾
            return positions[2]
        else:  # 其他垃圾
            return positions[3]

# 主应用类
class GarbageSortingSystem:
    def __init__(self, trt_engine_path, map_param_path, arm_config_path):
        # 初始化目标检测模型
        self.detector = YOLOv8TRT(trt_engine_path, conf_thres=0.5, iou_thres=0.5)
        
        # 初始化坐标转换器
        # 初始化坐标转换器 - 使用新的单应性矩阵方法
        self.transformer = TransForm()
        
        # 初始化机械臂控制器
        self.arm_controller = ArmServo(yaml_path=arm_config_path)
        
        # 状态变量
        self.stable_count = 0
        self.STABLE_THRESHOLD = 15  # 连续检测到物体30帧视为稳定
        
    def visualize_results(self, image, results):
        """在图像上可视化检测结果"""
        display_img = image.copy()
        
        for result in results:
            x1, y1, x2, y2 = result['box']
            class_id = result['class_id']
            class_name = result['class_name']
            confidence = result['confidence']
            
            # 绘制边界框
            color = (0, 255, 0)  # 绿色
            cv2.rectangle(display_img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            
            # 绘制类别标签
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(display_img, label, (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # 计算中心点
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            cv2.circle(display_img, (center_x, center_y), 5, (0, 0, 255), -1)
            
            # 计算机械臂坐标系坐标
            arm_x, arm_y = self.transformer.getCoordinate(image, center_x, center_y)
            coord_text = f"({arm_x:.1f}, {arm_y:.1f})"
            cv2.putText(display_img, coord_text, (center_x + 10, center_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        # 显示稳定计数
        cv2.putText(display_img, f"Stable: {self.stable_count}/{self.STABLE_THRESHOLD}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        return display_img
    
    def process_frame(self, frame):
        """处理单帧图像"""
        # 裁剪图像区域 (根据实际摄像头安装位置调整)
        h, w = frame.shape[:2]
        cropped = frame[int(h/4.6):int(h - h/2.7), int(w/3.4):int(w - w/4.5)]
        resized = cv2.resize(cropped, (640, 480))
        
        # 执行目标检测
        results = self.detector.detect(resized)

            # 新增：打印每个检测到的物体的坐标
        if results:
            print("\n===== 检测到的物体坐标 =====")
            for i, result in enumerate(results, 1):
                # 1. 计算摄像头像素坐标（基于处理后的 640x480 图像）
                x1, y1, x2, y2 = result['box']  # 物体边界框（左上、右下坐标）
                center_x = (x1 + x2) / 2  # 中心点 x 坐标（摄像头像素）
                center_y = (y1 + y2) / 2  # 中心点 y 坐标（摄像头像素）
            
                # 2. 转换为机械臂坐标
                arm_x, arm_y = self.transformer.getCoordinate(resized, center_x, center_y)
            
                # 3. 打印结果（包含物体类别、摄像头坐标、机械臂坐标）
                print(f"物体 {i}: {result['class_name']}")
                print(f"  摄像头像素坐标: ({center_x:.2f}, {center_y:.2f}) 像素")
                print(f"  机械臂坐标: ({arm_x:.2f}, {arm_y:.2f})")
            print("==========================\n")
        
        # 可视化结果
        display_img = self.visualize_results(resized, results)
        
        # 检查稳定状态
        if results:
            # 只处理第一个检测到的物体
            main_obj = results[0]
            
            # 计算中心点
            x1, y1, x2, y2 = main_obj['box']
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            
            # 转换为机械臂坐标
            arm_x, arm_y = self.transformer.getCoordinate(resized, center_x, center_y)
            
            # 检查位置是否稳定
            if self.stable_count > 0 and abs(arm_x - self.last_x) < 1.0 and abs(arm_y - self.last_y) < 1.0:
                self.stable_count += 1
            else:
                self.stable_count = 1
            
            # 保存当前位置
            self.last_x, self.last_y = arm_x, arm_y
            
            # 如果物体稳定存在，执行分拣
            if self.stable_count >= self.STABLE_THRESHOLD:
                print(f"Object stabilized at ({arm_x:.1f}, {arm_y:.1f}), class: {main_obj['class_name']}")
                self.stable_count = 0
                
                # 控制机械臂拾取物体
                self.arm_controller.pick_object(arm_x, arm_y, main_obj['class_id'])
        else:
            self.stable_count = 0
        
        return display_img
    
    def run_from_camera(self, camera_index=0):
        """从摄像头捕获并处理视频流"""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        
        print("Starting garbage sorting system. Press 'q' to exit.")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Error: Failed to capture frame")
                    break
                
                # 处理帧
                processed_frame = self.process_frame(frame)
                
                # 显示结果
                cv2.imshow("Garbage Sorting System", processed_frame)
                
                # 检查退出键
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("System stopped")

# 主程序
if __name__ == "__main__":
    # 配置文件路径
    TRT_ENGINE_PATH = "best0.engine"  # TensorRT引擎文件
    MAP_PARAM_PATH = "map_param.npz"     # 相机标定参数文件
    ARM_CONFIG_PATH = "arm_config.yaml"  # 机械臂配置文件
    
    # 创建并运行系统
    sorting_system = GarbageSortingSystem(
        trt_engine_path=TRT_ENGINE_PATH,
        map_param_path=MAP_PARAM_PATH,
        arm_config_path=ARM_CONFIG_PATH
    )
    
    # 从摄像头运行
    sorting_system.run_from_camera(camera_index=0)