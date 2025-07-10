import cv2
import numpy as np
import time
from ultralytics import YOLO
from embedded.ArmIK.Transform import Trans
from embedded.auto_move import ArmController
from utils.vision_utils import putText
from tools.config import Config


def undistort_fisheye(frame, K, D, DIM):
    h, w = frame.shape[:2]
    if (w, h) != DIM:
        frame = cv2.resize(frame, DIM)

    map1, map2 = cv2.fisheye.initUndistortRectifyMap(
        K, D, np.eye(3), K, DIM, cv2.CV_16SC2
    )
    undistorted = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR)
    return undistorted


class GarbageSortingApp:
    def __init__(self):
        # 加载模型
        self.model = YOLO(Config.MODEL_PATH)

        # 加载鱼眼参数（与 undistort_stream.py 完全一致）
        param_path = "/home/bkrc/Desktop/chenning_project/zhengji/camera_fisheye_params.npz"  # ✅ 用你验证过的路径
        data = np.load(param_path)
        self.K = data["K"]
        self.D = data["D"]
        self.DIM = tuple(data["img_shape"])

        # 初始化机械臂与坐标映射
        self.arm = ArmController()
        self.transform = Trans(Config.MAP_PARAM_PATH)

        # 打开摄像头
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.DIM[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.DIM[1])
        if not self.cap.isOpened():
            raise RuntimeError("❌ 无法打开摄像头")

        self.stable_count = 0
        self.stable_threshold = 10
        self.window_name = Config.WINDOW_NAME

        print("✅ 系统初始化完成，等待识别垃圾...")

    def run(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("❌ 图像读取失败")
                continue

            # ✅ 使用测试通过的去畸变函数
            frame = undistort_fisheye(frame, self.K, self.D, self.DIM)

            h, w = frame.shape[:2]
            roi = frame[h//4:h*3//4, w//4:w*3//4]

            results = self.model(roi, verbose=False)

            if results[0].boxes and len(results[0].boxes) > 0:
                box = results[0].boxes[0]
                score = float(box.conf[0])
                cls_id = int(box.cls[0])
                cx = int((box.xyxy[0][0] + box.xyxy[0][2]) / 2)
                cy = int((box.xyxy[0][1] + box.xyxy[0][3]) / 2)
                label = Config.GARBAGE_LABELS[cls_id] if cls_id < len(Config.GARBAGE_LABELS) else "unknown"

                if score > 0.5:
                    self.stable_count += 1
                else:
                    self.stable_count = 0

                if self.stable_count >= self.stable_threshold:
                    self.stable_count = 0
                    print(f"✅ 稳定识别为：{label}")

                    global_cx = cx + w // 4
                    global_cy = cy + h // 4
                    obj_x, obj_y, angle = self.transform.getCoordinate(frame, global_cx, global_cy)

                    if obj_x is not None:
                        print(f"📍 投影坐标=({obj_x}, {obj_y})，角度={angle}")
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        gray = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                        gray = putText(gray, f"识别为：{label}", (20, 40), color=(0, 255, 0))
                        cv2.imshow(self.window_name, gray)

                        self.arm.execute_sorting_by_name((obj_x, obj_y), label)
                        time.sleep(2)
                    else:
                        print("⚠️ 坐标转换失败")

            # 绘制所有框
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = Config.GARBAGE_LABELS[cls_id] if cls_id < len(Config.GARBAGE_LABELS) else "unknown"

                cv2.rectangle(roi, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(roi, f"{label} {conf:.2f}", (x1, max(y1-10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

            cv2.imshow(self.window_name, frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

        self.cap.release()
        cv2.destroyAllWindows()