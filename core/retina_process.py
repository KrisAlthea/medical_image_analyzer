import os
import cv2
import torch
import numpy as np

from .unet_retina import UNet


class RetinaProcess:
    """
    Retina B-scan 图像处理管道，包含以下关键步骤：
    1. 检测计算设备（CPU或GPU）并初始化UNet模型
    2. 对单通道B-scan图像执行分割推理，获得BM层位置
    3. 将BM层像素位置转换成一维点集
    4. 使用最小二乘法拟合圆，计算圆心和半径
    5. 在图像上绘制BM层点、拟合圆及圆心，并保存结果
    """

    def __init__(self):
        """
        初始化方法：
        - 检测并设置计算设备（CPU/GPU）
        - 构建UNet模型并加载预训练权重
        """
        # 1. 检测CUDA是否可用，优先使用GPU加速
        has_cuda = torch.cuda.is_available()
        self.device = torch.device('cuda' if has_cuda else 'cpu')

        # 2. 实例化UNet网络，输入通道=1，输出类别数=3
        self.net = UNet(n_channels=1, n_classes=3)
        # 将模型移动到指定设备
        self.net = self.net.to(self.device)

        # 3. 构造权重文件路径并加载模型参数（仅加载权重部分）
        base_dir = os.path.dirname(__file__)
        model_file = os.path.join(base_dir, '..', 'models', 'retina.pth')
        state = torch.load(model_file, map_location=self.device, weights_only=True)
        self.net.load_state_dict(state)

    @torch.no_grad()
    def infer_bscan(self, oct_img):
        """
        对单通道B-scan灰度图像执行UNet前向推理，并提取BM层像素位置。

        :param oct_img: numpy.ndarray, 形状 (H, W)，灰度图像
        :return: numpy.ndarray, 形状 (1, W)，每列为对应BM层的像素行索引
        """
        # 1. 将图像转为Tensor，并添加batch和channel维度
        oct_tensor = torch.from_numpy(oct_img).unsqueeze(0).unsqueeze(0).float().to(self.device)

        # 2. 前向推理，得到logits输出
        logits = self.net(oct_tensor)

        # 3. 选取每个像素的预测类别索引
        pred_class = torch.argmax(logits, dim=1)

        # 4. 将类别索引转换为one-hot编码，得到三个通道的分割mask
        pred_one_hot = torch.nn.functional.one_hot(pred_class, num_classes=3)
        pred_one_hot = pred_one_hot.permute(0, 3, 1, 2).float()

        # 5. 合并对应BM层的mask通道，得到BM层二值图（surface）
        pred_map = pred_one_hot[0]  # shape = (3, H, W)
        surface = pred_map.sum(dim=1)  # shape = (3, W) -> sum over height?

        # 6. 构建结果数组：每列取BM层像素的行索引
        result = np.zeros((1, surface.shape[1]), dtype=np.int64)
        for col in range(surface.shape[1]):
            result[0, col] = int(surface[0, col])
        return result

    @staticmethod
    def fit_circle_least_squares(points):
        """
        使用最小二乘法拟合圆，基于代数方程 x^2 + y^2 + D*x + E*y + F = 0。

        :param points: numpy.ndarray, shape=(N, 2)，点集，每行为(x, y)
        :return: (cx, cy, r)，圆心坐标和半径，均为整数
        """
        # 1. 提取x, y坐标
        x = np.array(points[:, 0], dtype=np.float64)
        y = np.array(points[:, 1], dtype=np.float64)
        N = len(x)

        # 2. 构建线性方程A·p = b，其中p=[D, E, F]
        A = np.vstack([x, y, np.ones(N)]).T  # shape=(N,3)
        b_vec = -(x ** 2 + y ** 2)

        # 3. 求解最小二乘：p = (A^T A)^{-1} A^T b
        D, E, F = np.linalg.lstsq(A, b_vec, rcond=None)[0]

        # 4. 由代数参数恢复圆心和半径：
        cx = -D / 2
        cy = -E / 2
        r = np.sqrt(cx ** 2 + cy ** 2 - F)

        return int(cx), int(cy), int(r)

    def process_retina(self, path):
        """
        完整的Retina图像处理流程：
        - 读取灰度图像并推理BM层位置
        - 在彩图上绘制BM层点集
        - 最小二乘法圆拟合并绘制圆和圆心
        - 自动扩充图像至指定尺寸并保存

        :param path: str，输入B-scan图像文件路径
        :return: dict，包含拟合圆半径、曲率及结果图像路径
        """
        # 1. 读取输入灰度图像
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

        # 2. 推理获取BM层像素索引数组
        result = self.infer_bscan(img)

        # 3. 将灰度图转换为BGR彩色图，便于绘制彩色标记
        img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        # 4. 为后续绘制和适配固定尺寸，计算上下左右的黑色填充（pad）
        target_h, target_w = 1024, 1440
        h, w = img_color.shape[:2]
        pad_h = max(target_h - h, 0)
        pad_w = max(target_w - w, 0)
        top, bottom = pad_h // 2, pad_h - pad_h // 2
        left, right = pad_w // 2, pad_w - pad_w // 2

        # 5. 扩充彩色图像至目标大小，填充值为黑色
        img_pad = cv2.copyMakeBorder(img_color, top, bottom, left, right,
                                     cv2.BORDER_CONSTANT, value=[0, 0, 0])

        # 6. 构造BM层点集，并根据填充偏移后绘制到图像上
        bm_layer = np.array([(x, y) for x, y in enumerate(result[0])])
        bm_layer_shift = bm_layer + np.array([left, top])
        for pt in bm_layer_shift:
            cv2.circle(img_pad, (int(pt[0]), int(pt[1])), 1, (0, 255, 0), -1)

        # 7. 拟合圆并计算圆心与半径，再绘制到图像上
        cx, cy, r = RetinaProcess.fit_circle_least_squares(bm_layer)
        # 考虑图像填充偏移
        cx_shift, cy_shift = cx + left, cy + top
        cv2.circle(img_pad, (cx_shift, cy_shift), 5, (255, 0, 0), -1)  # 标记圆心
        cv2.circle(img_pad, (cx_shift, cy_shift), r, (0, 0, 255), 2)  # 绘制圆形轮廓

        # 8. 构造输出目录并确保存在，然后保存结果图像
        output_dir = os.path.join(
            r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\output",
            "retina"
        )
        os.makedirs(output_dir, exist_ok=True)

        name, ext = os.path.splitext(os.path.basename(path))
        save_path = os.path.join(output_dir, f"{name}-output{ext}")
        cv2.imwrite(save_path, img_pad)
        print("保存结果图像到:", save_path)

        # 9. 计算圆直径（毫米）和曲率，并打包返回
        result_data = {
            'circle_radius': r,
            'circle_curvature': 1.0 / r if r != 0 else None,
            'result_image_path': save_path,
        }
        return result_data


if __name__ == '__main__':
    # 示例用法，指定数据目录和文件名
    base_path = r"D:\Code\PyCharm_ws\medical_image_analyzer\data\retina"
    img_file = os.path.join(base_path, "30.bmp")
    retina_processor = RetinaProcess()
    retina_processor.process_retina(img_file)
