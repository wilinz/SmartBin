# undistort_stream.py

import cv2
import numpy as np

def undistort_fisheye(frame, K, D, DIM):
    h, w = frame.shape[:2]
    if (w, h) != DIM:
        frame = cv2.resize(frame, DIM)

    map1, map2 = cv2.fisheye.initUndistortRectifyMap(
        K, D, np.eye(3), K, DIM, cv2.CV_16SC2
    )
    undistorted = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR)
    return undistorted

def main(param_path='/home/bkrc/Desktop/chenning_project/zhengji/camera_fisheye_params.npz'):
    # === 加载标定参数 ===
    try:
        params = np.load(param_path)
        K = params['K']
        D = params['D']
        DIM = tuple(params['img_shape'])  # ✅ 正确键名
    except Exception as e:
        print("❌ 参数文件读取失败：", e)
        return

    print("✅ 相机参数加载成功")
    print("📷 K:\n", K)
    print("🔧 D:", D.ravel())
    print("📐 图像尺寸 DIM:", DIM)

    # === 打开摄像头 ===
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 无法打开摄像头")
        return

    print("🎥 正在运行，按 ESC 键退出")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ 图像读取失败")
            break

        undistorted = undistort_fisheye(frame, K, D, DIM)

        # 显示原始与矫正图像
        display = np.hstack((cv2.resize(frame, DIM), undistorted))
        cv2.imshow("Original (Left) | Undistorted (Right)", display)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC 退出
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
