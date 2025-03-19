import os
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import distance

# 如果需要使用PIL，可根据需求导入
# from PIL import Image

from unet_retina import UNet



###################################
# 1. Tester 类：加载并运行 U-Net
###################################
class Tester:
    def __init__(self):
        """
        初始化Tester类时：
        1. 构造UNet网络，并将其加载到指定设备上；
        2. 根据预设的模型文件路径加载训练好的权重参数，
           权重文件路径需根据实际情况修改。
        """
        # 初始化U-Net网络，输入通道数为1，输出类别数为3
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.net = UNet(n_channels=1, n_classes=3)
        self.net = self.net.to(self.device)

        # 设置模型权重文件路径，需根据实际情况修改
        load_model_path = "../models/retina.pth"
        if os.path.exists(load_model_path):
            print("Model file found. Loading weights...")
            # 加载权重参数，此处假设保存方式为只保存 state_dict
            module_weight = torch.load(load_model_path, map_location=self.device,
                                       weights_only=True)
            self.net.load_state_dict(module_weight)
        else:
            print("Model file not found at", load_model_path)

    @torch.no_grad()
    def test_bscan(self, img_path):
        """
        读取单张B-scan图像并利用U-Net进行前向推理，
        最终返回shape为(1, W)的一维结果数组。

        处理流程：
        1. 读取灰度图像（二维数组，shape=(H,W)）；
        2. 转换为张量并扩展维度，构成形状为 [1,1,H,W] 的输入；
        3. 通过网络前向传播得到 logits，形状为 [1,3,H,W]；
        4. 对 logits 在类别维度上进行argmax操作，得到每像素预测类别；
        5. 利用 one_hot 将类别映射为 one-hot 编码，并调整维度；
        6. 计算沿高度方向的和（sum），得到每列的统计结果；
        7. 根据需求选择某一通道（这里取通道0）生成最终结果数组。

        :param img_path: B-scan图像的文件路径
        :return: 一维结果数组，形状为 (1, W)
        """
        # 读入灰度图，oct_img shape=(H,W)
        oct_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if oct_img is None:
            raise FileNotFoundError(f"Cannot read image from {img_path}")

        # 将图像转换为浮点型张量，并扩展batch和channel维度，shape变为 [1,1,H,W]
        oct_tensor = torch.from_numpy(oct_img).unsqueeze(0).unsqueeze(0).float().to(self.device)

        # 前向推理，得到 logits，形状为 [1,3,H,W]
        logits = self.net(oct_tensor)

        # 取每个像素点类别的最大值索引，得到形状 [1,H,W] 的预测类别
        pred_class = torch.argmax(logits, dim=1)
        # 将预测结果转换为 one_hot 编码，shape从 [1,H,W,3] 转换为 [1,3,H,W]
        pred_one_hot = torch.nn.functional.one_hot(pred_class, 3).permute(0, 3, 1, 2).float()

        # 去除batch维度，得到 shape 为 [3,H,W] 的特征图
        pred_map = pred_one_hot[0]

        # 对高度方向求和，得到每个通道在水平方向的统计值，结果 shape 为 [3,W]
        surface = pred_map.sum(dim=1)

        # 根据项目需求，这里取通道0的统计值构造最终结果
        # 初始化一个形状为 (1, W) 的数组，并将 surface[0, :] 的值赋值进去
        result = np.zeros((1, surface.shape[1]), dtype=np.int64)
        for cc in range(surface.shape[1]):
            result[0, cc] = int(surface[0, cc])

        return result


###################################
# 2. 拟合圆相关函数
###################################
def load_bm_layer(file_path):
    """
    加载存储的BM层数据（.npy格式）。

    :param file_path: BM层数据文件路径
    :return: 加载的numpy数组数据
    """
    return np.load(file_path)


def generate_circles(radius_range, center_x_range, center_y_range, step):
    """
    根据给定参数生成候选圆的集合，用于后续拟合搜索。

    生成的每个圆由 (cx, cy, r) 表示，其中：
      - r 来自 radius_range 范围；
      - cx 在 center_x_range 范围内，步长为 step；
      - cy 在 center_y_range 范围内，步长为 step。

    :param radius_range: 半径取值范围（可用range生成）
    :param center_x_range: 圆心x坐标取值范围，如 (xmin, xmax)
    :param center_y_range: 圆心y坐标取值范围，如 (ymin, ymax)
    :param step: 圆心坐标搜索的步长
    :return: 候选圆列表，每个元素为 (cx, cy, r)
    """
    circles = []
    for r in radius_range:
        for cx in range(center_x_range[0], center_x_range[1], step):
            for cy in range(center_y_range[0], center_y_range[1], step):
                circles.append((cx, cy, r))
    return circles


def compute_fitting_score(bm_layer, circle):
    """
    计算给定候选圆与BM层点集之间的拟合得分。

    具体过程：
      1. 根据候选圆参数 (cx, cy, r) 在圆周上生成100个点；
      2. 计算BM层中每个点到圆周上所有点的欧氏距离；
      3. 对每个BM层点取其到圆周上最近点的距离，并计算平均值作为拟合得分。

    得分越低，表示该圆与BM层点集越吻合。

    :param bm_layer: BM层点集，形状应为 (N, 2)，其中每行表示 (x, y)
    :param circle: 候选圆参数，形式为 (cx, cy, r)
    :return: 拟合得分（浮点数）
    """
    cx, cy, r = circle
    # 在圆周上均匀生成100个点
    circle_points = np.array([
        (cx + r * np.cos(theta), cy + r * np.sin(theta))
        for theta in np.linspace(0, 2 * np.pi, 100)
    ])

    # 检查bm_layer形状是否正确，要求每个点为二维坐标
    if bm_layer.shape[1] != 2:
        raise ValueError("bm_layer should have shape (N, 2)")

    # 计算bm_layer中每个点到圆周所有点的欧氏距离
    distances = distance.cdist(bm_layer, circle_points, 'euclidean')
    # 对每个点取最小距离，再计算所有最小距离的平均值作为得分
    min_distances = np.min(distances, axis=1)
    score = np.mean(min_distances)
    return score


def find_best_fitting_circle(bm_layer, circles):
    """
    在候选圆集合中搜索与BM层点集拟合得分最优的圆。

    遍历所有候选圆，计算拟合得分，返回得分最低的圆。

    :param bm_layer: BM层点集，形状为 (N, 2)
    :param circles: 候选圆列表，每个元素为 (cx, cy, r)
    :return: 最佳拟合圆的参数 (cx, cy, r)
    """
    best_circle = None
    best_score = float('inf')
    for c in circles:
        score = compute_fitting_score(bm_layer, c)
        if score < best_score:
            best_score = score
            best_circle = c
    return best_circle


def plot_bm_layer_and_circle(bm_layer, bscan_image, best_circle):
    """
    使用Matplotlib对原始B-scan图像、BM层点集和最佳拟合圆进行可视化，
    并将图像保存到指定路径下。

    可视化内容包括：
      1. 显示灰度B-scan图像；
      2. 在图像上绘制BM层（红色曲线）；
      3. 绘制最佳拟合圆（蓝色圆环）以及圆心。

    :param bm_layer: BM层点集，形状为 (N, 2)，其中列0为x坐标，列1为y坐标
    :param bscan_image: 原始B-scan灰度图
    :param best_circle: 最佳拟合圆参数，形式为 (cx, cy, r)
    """
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 6))
    plt.imshow(bscan_image, cmap='gray')

    # 绘制BM层点集，红色曲线
    plt.plot(bm_layer[:, 0], bm_layer[:, 1], color='r', label='BM Layer')

    # 绘制最佳拟合圆，蓝色圆环及圆心
    cx, cy, r = best_circle
    circle = plt.Circle((cx, cy), r, color='b', fill=False, label=f'Best Fit Circle (r={r / 10}mm)')
    plt.gca().add_patch(circle)
    plt.scatter(cx, cy, color='b', s=50)

    plt.legend()
    plt.axis('off')
    plt.title('BM Layer and Best Fit Circle')

    # 指定保存路径
    save_path = r"D:\Code\PyCharm_ws\medical_image_analyzer\output\retina\BM_layer_circle_plot.png"
    plt.savefig(save_path, bbox_inches='tight')

    plt.show()


###################################
# 3. 主函数：先推理，再拟合
###################################
if __name__ == '__main__':
    """
    主函数执行流程：
      1. 设定输入的B-scan图像路径，并定义输出结果文件（.npy）路径；
      2. 实例化Tester类，调用test_bscan对B-scan图像进行推理，
         并将结果保存为.npy文件；
      3. 读取保存的结果，并将1D数组转换为 (N,2) 的点集，便于后续圆拟合；
      4. 读取原始B-scan图像，便于结果可视化；
      5. 设置候选圆的搜索参数（半径范围、圆心范围及步长）；
      6. 生成候选圆集合，并搜索最佳拟合圆；
      7. 将最佳拟合圆及BM层结果可视化。
    """
    # 1) 设定输入图像路径和输出.npy文件路径
    bscan_image_path = r"D:\Code\PyCharm_ws\medical_image_analyzer\data\retina\30.bmp"
    # output_npy_path = '30.npy'

    # 2) 实例化Tester类并调用test_bscan进行推理
    tester = Tester()
    result = tester.test_bscan(bscan_image_path)
    # np.save(output_npy_path, result)
    # print(f"Saved result to {output_npy_path}")

    # 3) 读取保存的.npy文件，并转换为 (N,2) 的点集
    # 这里通过enumerate将1D数组转换为 (x, y) 点对，x为索引，y为对应值
    # bm_layer = load_bm_layer(output_npy_path)
    bm_layer = np.array([(x, y) for x, y in enumerate(result[0])])
    print("bm_layer shape:", bm_layer.shape)  # 例如 (400, 2)

    # 4) 读取原始B-scan灰度图，用于后续可视化
    bscan_image = cv2.imread(bscan_image_path, cv2.IMREAD_GRAYSCALE)

    # 5) 设置拟合圆的搜索参数（可根据实际情况调整）
    radius_range = range(200, 350, 5)  # 半径范围200到350，步长为5
    center_x_range = (0, 400)  # 圆心x坐标搜索范围
    center_y_range = (0, 640)  # 圆心y坐标搜索范围
    step = 20  # 圆心搜索步长

    # 生成候选圆集合
    circles = generate_circles(radius_range, center_x_range, center_y_range, step)

    # 6) 在候选圆集合中搜索最佳拟合圆
    best_circle = find_best_fitting_circle(bm_layer, circles)
    if best_circle:
        print(f"Best Circle: Center=({best_circle[0]}, {best_circle[1]}), Radius={best_circle[2]}")
        # 7) 可视化BM层和最佳拟合圆
        plot_bm_layer_and_circle(bm_layer, bscan_image, best_circle)
    else:
        print("No fitting circle found.")
