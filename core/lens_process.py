import os
import torch
import cv2
import numpy as np
from sklearn.cluster import DBSCAN
from unet_lens import UNet


class LensProcess:
    """
    基于UNet的镜片图像处理管道，包含以下步骤：
    1. 语义分割
    2. 边界点提取
    3. 噪声点去除
    4. 二次曲线拟合
    5. 圆拟合与曲率计算
    6. 可视化并保存结果
    """

    def __init__(self):
        """
        初始化方法：
        - 确定计算设备
        - 加载UNet模型权重
        - 切换模型至评估模式
        """
        # 判断是否有可用GPU
        has_cuda = torch.cuda.is_available()
        if has_cuda:
            self.device = torch.device('cuda')
        else:
            self.device = torch.device('cpu')

        # 初始化UNet网络结构，输入通道为3，输出类别数为2，基础通道数为96
        self.net = UNet(in_channels=3, n_classes=2, channels=96)

        # 将模型移动到指定设备
        self.net = self.net.to(self.device)

        # 构造模型权重文件路径
        base_dir = os.path.dirname(__file__)
        model_file = os.path.join(base_dir, '..', 'models', 'lens.pth')

        # 加载权重（仅权重部分）
        state = torch.load(model_file, map_location=self.device, weights_only=True)
        self.net.load_state_dict(state)

        # 设置模型为评估模式，关闭Dropout和BatchNorm等训练行为
        self.net.eval()

    def unet_seg(self, image: np.ndarray) -> np.ndarray:
        """
        使用UNet对输入图像执行语义分割，返回二值掩码
        :param image: 原始BGR图像，形状HxWx3
        :return: 分割掩码，形状HxW，值为0或1
        """
        # 将图像从HWC转为CHW顺序，并转换为浮点型
        chw = image.transpose(2, 0, 1).astype(np.float32)

        # 创建批次维度
        batch = np.expand_dims(chw, axis=0)

        # 转换为PyTorch张量，并送入设备
        tensor = torch.from_numpy(batch).to(self.device)
        tensor = tensor.float()

        # 关闭梯度计算，加速推理
        with torch.no_grad():
            logits = self.net(tensor)

        # 获取类别概率最高的索引，转为NumPy数组并移至CPU
        pred = torch.argmax(logits, dim=1).cpu().numpy()[0]

        # 返回二值化分割结果
        return pred

    @staticmethod
    def get_boundaries(pred: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        从二值掩码中提取上下边界点集：
        - 上边界取每列第一个值1的位置
        - 下边界取每列最后一个值1的位置
        坐标y反向处理，方便绘制
        :param pred: 分割掩码，HxW
        :return: (上边界点数组, 下边界点数组)，均为Nx2形式 (x, y)
        """
        height, width = pred.shape
        up_points = []
        down_points = []

        # 遍历每一列，提取边界
        for col_idx in range(width):
            column = pred[:, col_idx]
            indices = np.where(column == 1)[0]

            if indices.size > 0:
                first = indices[0]
                last = indices[-1]

                # 上边界点 (x, y)
                up_points.append([col_idx, -first])
                # 下边界点 (x, y)
                down_points.append([col_idx, -last])

        up_arr = np.array(up_points)
        down_arr = np.array(down_points)
        return up_arr, down_arr

    @staticmethod
    def remove_noise(
            pts: np.ndarray,
            eps: float = None,
            min_samples: int = 2
    ) -> np.ndarray:
        """
        使用DBSCAN算法去除边界点集中的噪声：
        - 若未指定eps，则自动估计一个合适值
        - 之后聚类，保留最大簇
        :param pts: 原始点集，Nx2
        :param eps: 邻域半径
        :param min_samples: 最小样本数
        :return: 去噪后点集，Mx2
        """
        # 如果未传入eps，则进行估计
        if eps is None:
            # 计算所有点之间的距离矩阵
            dist_matrix = np.sqrt(((pts[:, None] - pts) ** 2).sum(axis=2))
            # 取每行第min_samples最近的距离
            k = min_samples
            kth_distances = np.partition(dist_matrix, k, axis=1)[:, k]
            # 选择中位数作为eps
            eps = float(np.median(kth_distances))

        # 创建DBSCAN模型并预测标签
        db = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db.fit_predict(pts)

        # 统计各簇大小，忽略噪声(-1)
        unique_labels, counts = np.unique(labels, return_counts=True)
        label_counts = dict(zip(unique_labels, counts))
        if -1 in label_counts:
            del label_counts[-1]

        # 选取最大簇标签
        main_label = max(label_counts, key=label_counts.get)

        # 返回属于主簇的点
        return pts[labels == main_label]

    @staticmethod
    def fit_quadratic(
            img: np.ndarray,
            pts: np.ndarray
    ) -> tuple[np.poly1d, np.ndarray, np.ndarray]:
        """
        对边界点进行二次多项式拟合，并绘制拟合曲线点
        :param img: 原始图像
        :param pts: 无噪声点集，Nx2
        :return: (拟合多项式, x, y)
        """
        x = pts[:, 0]
        y = pts[:, 1]
        # 多项式拟合
        coefficients = np.polyfit(x, y, 2)
        poly = np.poly1d(coefficients)
        y_fit = poly(x)

        # 在图像上绘制拟合点
        for xi, yi in zip(x, y_fit):
            pt = (int(xi), int(-yi))
            cv2.circle(img, pt, radius=2, color=(0, 255, 0), thickness=-1)

        return poly, x, y_fit

    @staticmethod
    def fit_circle(
            img: np.ndarray,
            x: np.ndarray,
            y: np.ndarray
    ) -> tuple[int, float]:
        """
        基于代数方法拟合圆，并计算曲率：
        - 构造方程组 Ax = b
        - 最小二乘解
        - 提取圆心和半径
        :param img: 原始图像
        :param x: 点集x坐标
        :param y: 点集y坐标（已取反）
        :return: (半径R, 曲率1/R)
        """
        # 恢复实际y坐标
        y_true = -y.astype(float)
        x_true = x.astype(float)
        # 构造矩阵A和向量b
        A = np.vstack([x_true, y_true, np.ones_like(x_true)]).T
        b_vec = -(x_true ** 2 + y_true ** 2)
        # 求解参数D,E,F
        D, E, F = np.linalg.lstsq(A, b_vec, rcond=None)[0]

        # 计算圆心坐标(a,b)和半径R
        a = -D / 2
        b0 = -E / 2
        R = np.sqrt(a * a + b0 * b0 - F)
        curvature = 1.0 / R if R > 0 else 0

        # 绘制圆心和圆轮廓
        center = (int(a), int(b0))
        cv2.circle(img, center, radius=5, color=(255, 0, 0), thickness=-1)
        cv2.circle(img, center, radius=int(R), color=(0, 0, 255), thickness=2)

        return int(R), curvature

    def process(self, path: str) -> dict:
        """
        主流程函数：
        1. 读取图像
        2. 语义分割
        3. 边界提取
        4. 上下边界去噪、拟合与绘制
        5. 保存结果
        :param path: 输入图像文件路径
        :return: 结果字典，包括上下边界半径、曲率和输出图像路径
        """
        # 1. 读取并缩放图像到固定尺寸
        img = cv2.imread(path)
        img = cv2.resize(img, (1440, 1024))

        # 2. 执行分割
        mask = self.unet_seg(img)

        # 3. 提取上下边界点集
        up_pts, down_pts = self.get_boundaries(mask)

        # 4. 上边界去噪、拟合
        up_clean = self.remove_noise(up_pts, min_samples=6)
        poly_up, ux, uy = self.fit_quadratic(img, up_clean)
        up_radius, up_curv = self.fit_circle(img, ux, uy)

        # 5. 下边界去噪、拟合
        down_clean = self.remove_noise(down_pts)
        poly_down, dx, dy = self.fit_quadratic(img, down_clean)
        down_radius, down_curv = self.fit_circle(img, dx, dy)

        # 6. 构造输出目录并保存图像
        output_dir = os.path.join(
            r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\output",
            "lens"
        )
        os.makedirs(output_dir, exist_ok=True)

        filename = os.path.splitext(os.path.basename(path))[0]
        save_path = os.path.join(output_dir, f"{filename}-output.jpg")
        cv2.imwrite(save_path, img)

        # 7. 返回处理结果
        result = {
            'up_radius': up_radius,
            'up_curvature': up_curv,
            'down_radius': down_radius,
            'down_curvature': down_curv,
            'result_image_path': save_path
        }
        return result


if __name__ == "__main__":
    # 示例：实例化并处理单张图片
    base_path = r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\data\lens"
    img_file = os.path.join(base_path, "8-2.jpg")
    processor = LensProcess()
    output = processor.process(img_file)
    print(output)
