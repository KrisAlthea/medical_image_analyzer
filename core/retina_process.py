import os
import cv2
import torch
import numpy as np
import matplotlib

matplotlib.use('Qt5Agg')  # 设置为 Qt5Agg 后端
import matplotlib.pyplot as plt
from scipy.spatial import distance

from .unet_retina import UNet


class RetinaProcess:
    """
    Retina图像处理管道类
    本类封装了对输入B-scan图像进行语义分割、BM层点集生成、最佳拟合圆搜索
    及结果可视化和保存的完整流程。
    """

    def __init__(self, model_path="../models/retina.pth"):
        """
        初始化RetinaProcess类时：
          1. 构造UNet网络，并将其加载到指定设备上；
          2. 根据预设的模型文件路径加载训练好的权重参数。
        """
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.net = UNet(n_channels=1, n_classes=3).to(self.device)

        print("Model found. Loading weights...")
        # if os.path.exists(model_path):
        #     print("Model file found. Loading weights...")
        #     module_weight = torch.load(model_path, map_location=self.device, weights_only=True)
        #     self.net.load_state_dict(module_weight)
        # else:
        #     print("Model file not found at", model_path)
        module_weight = torch.load(model_path, map_location=self.device, weights_only=True)
        self.net.load_state_dict(module_weight)

    @torch.no_grad()
    def test_bscan(self, img_path):
        """
        读取B-scan图像并利用U-Net进行推理，返回一维结果数组 (1, W)。
        """
        print("start testing bscan...")
        oct_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if oct_img is None:
            raise FileNotFoundError(f"Cannot read image from {img_path}")

        oct_tensor = torch.from_numpy(oct_img).unsqueeze(0).unsqueeze(0).float().to(self.device)
        logits = self.net(oct_tensor)
        pred_class = torch.argmax(logits, dim=1)
        pred_one_hot = torch.nn.functional.one_hot(pred_class, 3).permute(0, 3, 1, 2).float()
        pred_map = pred_one_hot[0]
        surface = pred_map.sum(dim=1)

        result = np.zeros((1, surface.shape[1]), dtype=np.int64)
        for cc in range(surface.shape[1]):
            result[0, cc] = int(surface[0, cc])
        return result

    @staticmethod
    def generate_circles(radius_range, center_x_range, center_y_range, step):
        """
        生成候选圆集合。
        """
        circles = []
        for r in radius_range:
            for cx in range(center_x_range[0], center_x_range[1], step):
                for cy in range(center_y_range[0], center_y_range[1], step):
                    circles.append((cx, cy, r))
        return circles

    @staticmethod
    def compute_fitting_score(bm_layer, circle):
        """
        计算候选圆与BM层点集的拟合得分。
        """
        cx, cy, r = circle
        circle_points = np.array([
            (cx + r * np.cos(theta), cy + r * np.sin(theta))
            for theta in np.linspace(0, 2 * np.pi, 100)
        ])

        if bm_layer.shape[1] != 2:
            raise ValueError("bm_layer should have shape (N, 2)")

        distances = distance.cdist(bm_layer, circle_points, 'euclidean')
        min_distances = np.min(distances, axis=1)
        score = np.mean(min_distances)
        return score

    @staticmethod
    def find_best_fitting_circle(bm_layer, circles):
        """
        搜索最佳拟合圆。
        """
        best_circle = None
        best_score = float('inf')
        for c in circles:
            score = RetinaProcess.compute_fitting_score(bm_layer, c)
            if score < best_score:
                best_score = score
                best_circle = c
        return best_circle

    def process_retina(self, bscan_image_path, circle_params, save_dir):
        """
        完整处理流程，并将结果保存到指定目录。

        :param bscan_image_path: B-scan图像路径
        :param circle_params: 候选圆参数配置字典
        :param save_dir: 保存目录，默认为 "output/retina"
        :return: 保存的图像路径
        """
        # 1. 推理
        result = self.test_bscan(bscan_image_path)
        # 2. 生成BM层点集
        bm_layer = np.array([(x, y) for x, y in enumerate(result[0])])
        print("bm_layer shape:", bm_layer.shape)

        # 3. 加载原始B-scan图像
        bscan_image = cv2.imread(bscan_image_path, cv2.IMREAD_GRAYSCALE)

        # 4. 生成候选圆集合
        circles = RetinaProcess.generate_circles(circle_params["radius_range"],
                                                 circle_params["center_x_range"],
                                                 circle_params["center_y_range"],
                                                 circle_params["step"])

        # 5. 搜索最佳拟合圆并保存图像
        best_circle = RetinaProcess.find_best_fitting_circle(bm_layer, circles)
        save_path = None

        if best_circle:
            print(f"Best Circle: Center=({best_circle[0]}, {best_circle[1]}), Radius={best_circle[2]}")
            # 获取原文件名（不含路径）
            filename = os.path.basename(bscan_image_path)
            # 分离文件名和扩展名
            name, ext = os.path.splitext(filename)
            # 生成新的文件名，例如 "1-1-output.jpg"
            new_filename = f"{name}-output.jpg"
            # 组合保存路径
            save_path = os.path.join(save_dir, new_filename)
            print(f"Saving to: {save_path}")

            """
                    可视化BM层和最佳拟合圆，并保存到指定路径。

                    :param bm_layer: BM层点集，形状为 (N, 2)
                    :param bscan_image: 原始B-scan灰度图
                    :param best_circle: 最佳拟合圆参数 (cx, cy, r)
                    :param save_path: 保存图像的路径
                    """
            # 确保保存目录存在
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            plt.figure(figsize=(10, 6))
            plt.imshow(bscan_image, cmap='gray')
            plt.plot(bm_layer[:, 0], bm_layer[:, 1], color='r', label='BM Layer')
            cx, cy, r = best_circle
            circle = plt.Circle((cx, cy), r, color='b', fill=False, label=f'Best Fit Circle (r={r / 10}mm)')
            plt.gca().add_patch(circle)
            plt.scatter(cx, cy, color='b', s=50)
            plt.legend()
            plt.axis('off')
            plt.title('BM Layer and Best Fit Circle')
            plt.savefig(save_path, bbox_inches='tight')
            plt.close()  # 关闭图像，防止显示
        else:
            print("No fitting circle found.")

        # 计算实际直径（毫米）和边界测量值
        diameter_mm = best_circle[2] * 2 / 10 if best_circle else None  # 半径转换为直径（mm）

        # 从BM层计算一些统计数据
        bm_avg_y = np.mean(bm_layer[:, 1]) if bm_layer.shape[0] > 0 else None
        bm_max_y = np.max(bm_layer[:, 1]) if bm_layer.shape[0] > 0 else None
        bm_min_y = np.min(bm_layer[:, 1]) if bm_layer.shape[0] > 0 else None
        bm_variation = bm_max_y - bm_min_y if bm_max_y is not None and bm_min_y is not None else None

        # 返回处理结果数据（原始数据 + 格式化的显示信息）
        result_data = {
            'bm_layer': bm_layer,
            'best_circle': best_circle,
            'result_image_path': save_path,
            # 添加用于界面显示的格式化数据
            'display_data': {
                'circle_center': f"({best_circle[0]}, {best_circle[1]})" if best_circle else "未找到",
                'circle_radius': f"{best_circle[2]}像素 ({best_circle[2]/10:.2f}mm)" if best_circle else "未找到",
                'diameter': f"{diameter_mm:.2f}mm" if diameter_mm else "未找到",
                'bm_points_count': f"{bm_layer.shape[0]}个点" if bm_layer.shape[0] > 0 else "0",
                'bm_depth_avg': f"{bm_avg_y:.2f}像素" if bm_avg_y is not None else "未知",
                'bm_variation': f"{bm_variation:.2f}像素" if bm_variation is not None else "未知",
                'status': "分析成功" if best_circle else "未找到合适的拟合圆"
            }
        }
        return result_data


if __name__ == '__main__':
    bscan_image_path = r"D:\Code\PyCharm_ws\medical_image_analyzer\data\retina\30.bmp"
    circle_params = {
        "radius_range": range(200, 350, 5),
        "center_x_range": (0, 400),
        "center_y_range": (0, 640),
        "step": 20
    }
    retina_processor = RetinaProcess()
    # 指定结果保存目录
    save_dir = r"D:\Code\PyCharm_ws\medical_image_analyzer\output\retina"
    retina_processor.process_retina(bscan_image_path, circle_params, save_dir)
