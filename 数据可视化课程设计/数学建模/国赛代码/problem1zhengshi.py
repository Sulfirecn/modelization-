import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV, learning_curve
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.multioutput import MultiOutputRegressor
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats


def main():
    # 1. 读取数据文件
    data = load_data('BMI_Y染色体浓度_分段平均值和标准差.xlsx')

    # 2. 数据探索和预处理
    explore_data(data)
    data = preprocess_data(data)

    # 3. 提取特征和目标变量
    X = data[['区间中点BMI']]
    y = data[['平均Y染色体浓度', 'Y染色体浓度标准差']]

    # 4. 数据标准化
    X_scaled, y_scaled, scaler_X, scaler_y = scale_data(X, y)

    # 5. 划分数据集
    X_train, X_test, y_train, y_test = split_data(X_scaled, y_scaled)

    # 6. 参数调优
    best_model, best_params, best_score = tune_hyperparameters(X_train, y_train)
    print(f"最佳参数: {best_params}")
    print(f"最佳交叉验证分数: {best_score:.4f}")

    # 7. 模型预测
    y_pred, y_test_orig = make_predictions(best_model, X_test, X_train, y_train, y_test, scaler_y)

    # 8. 模型评估
    evaluate_model(y_test_orig, y_pred, best_model, X_train, y_train, scaler_y)

    # 9. 可视化分析
    create_visualizations(y_test_orig, y_pred, best_model, X.columns, X_scaled, y_scaled)

    # 10. 误差分析
    analyze_errors(y_test_orig, y_pred)

    # 11. 显著性检验
    perform_statistical_tests(y_test_orig, y_pred)


def load_data(file_path):
    data = pd.read_excel(file_path)
    return data


def explore_data(data):
    print("数据基本信息:")
    print(data.info())
    print("\n数据描述性统计:")
    print(data[['区间中点BMI', '平均Y染色体浓度', 'Y染色体浓度标准差']].describe())
    print("\n缺失值检查:")
    print(data[['区间中点BMI', '平均Y染色体浓度', 'Y染色体浓度标准差']].isnull().sum())


def preprocess_data(data):
    # 处理缺失值 - 使用中位数填充
    imputer = SimpleImputer(strategy='median')
    data[['区间中点BMI', '平均Y染色体浓度', 'Y染色体浓度标准差']] = imputer.fit_transform(
        data[['区间中点BMI', '平均Y染色体浓度', 'Y染色体浓度标准差']])

    # 检查并处理异常值
    data = handle_outliers_advanced(data, '区间中点BMI')
    data = handle_outliers_advanced(data, '平均Y染色体浓度')
    data = handle_outliers_advanced(data, 'Y染色体浓度标准差')

    return data


def handle_outliers_advanced(df, column):
    """
    使用IQR方法识别异常值，并用该列的中位数替换它们
    """
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # 标识异常值
    outlier_mask = (df[column] < lower_bound) | (df[column] > upper_bound)
    outlier_count = outlier_mask.sum()

    if outlier_count > 0:
        print(f"在列 '{column}' 中发现 {outlier_count} 个异常值")
        # 用中位数替换异常值
        median_val = df[column].median()
        df.loc[outlier_mask, column] = median_val
    else:
        print(f"在列 '{column}' 中未发现异常值")

    return df


def scale_data(X, y):
    """数据标准化"""
    scaler_X = StandardScaler()
    scaler_y = StandardScaler()

    X_scaled = scaler_X.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y)

    X_scaled = pd.DataFrame(X_scaled, columns=X.columns)
    y_scaled = pd.DataFrame(y_scaled, columns=y.columns)

    return X_scaled, y_scaled, scaler_X, scaler_y


def split_data(X_scaled, y_scaled):
    """划分训练集和测试集"""
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_scaled, test_size=0.2, random_state=42, shuffle=True)

    return X_train, X_test, y_train, y_test


def tune_hyperparameters(X_train, y_train):
    """超参数调优"""
    param_grid = {
        'estimator__n_estimators': [50, 100],
        'estimator__max_depth': [3, 5, 7],
        'estimator__min_samples_split': [5, 10, 15],
        'estimator__min_samples_leaf': [3, 5, 7],
        'estimator__max_features': ['sqrt']
    }

    base_rf = RandomForestRegressor(random_state=42, bootstrap=True)
    multi_output_rf = MultiOutputRegressor(base_rf)

    grid_search = GridSearchCV(
        estimator=multi_output_rf,
        param_grid=param_grid,
        cv=5,
        scoring='r2',
        n_jobs=-1,
        verbose=1
    )

    print("开始网格搜索...")
    grid_search.fit(X_train, y_train)

    return grid_search.best_estimator_, grid_search.best_params_, grid_search.best_score_


def make_predictions(best_model, X_test, X_train, y_train, y_test, scaler_y):
    # 测试集预测
    y_pred_scaled = best_model.predict(X_test)
    y_pred = scaler_y.inverse_transform(y_pred_scaled)
    y_test_orig = scaler_y.inverse_transform(y_test)

    # 训练集预测（用于检测过拟合）
    y_train_pred_scaled = best_model.predict(X_train)
    y_train_pred = scaler_y.inverse_transform(y_train_pred_scaled)
    y_train_orig = scaler_y.inverse_transform(y_train)

    return y_pred, y_test_orig


def evaluate_model(y_test_orig, y_pred, best_model, X_train, y_train, scaler_y):
    """评估模型性能"""
    # 目标变量1: 平均Y染色体浓度
    mse_target1 = mean_squared_error(y_test_orig[:, 0], y_pred[:, 0])
    mae_target1 = mean_absolute_error(y_test_orig[:, 0], y_pred[:, 0])
    r2_target1 = r2_score(y_test_orig[:, 0], y_pred[:, 0])

    # 目标变量2: Y染色体浓度标准差
    mse_target2 = mean_squared_error(y_test_orig[:, 1], y_pred[:, 1])
    mae_target2 = mean_absolute_error(y_test_orig[:, 1], y_pred[:, 1])
    r2_target2 = r2_score(y_test_orig[:, 1], y_pred[:, 1])

    print(f"\n模型性能评估 - 平均Y染色体浓度:")
    print(f"均方误差 (MSE): {mse_target1:.4f}")
    print(f"平均绝对误差 (MAE): {mae_target1:.4f}")
    print(f"决定系数 (R²): {r2_target1:.4f}")

    print(f"\n模型性能评估 - Y染色体浓度标准差:")
    print(f"均方误差 (MSE): {mse_target2:.4f}")
    print(f"平均绝对误差 (MAE): {mae_target2:.4f}")
    print(f"决定系数 (R²): {r2_target2:.4f}")

    # 评估训练集性能以检测过拟合
    y_train_pred_scaled = best_model.predict(X_train)
    y_train_pred = scaler_y.inverse_transform(y_train_pred_scaled)
    y_train_orig = scaler_y.inverse_transform(y_train)

    r2_train_target1 = r2_score(y_train_orig[:, 0], y_train_pred[:, 0])
    r2_train_target2 = r2_score(y_train_orig[:, 1], y_train_pred[:, 1])

    print(f"\n训练集性能 - 平均Y染色体浓度 R²: {r2_train_target1:.4f}")
    print(f"训练集性能 - Y染色体浓度标准差 R²: {r2_train_target2:.4f}")

    # 计算过拟合程度
    overfit_target1 = r2_train_target1 - r2_target1
    overfit_target2 = r2_train_target2 - r2_target2

    print(f"\n过拟合程度 - 平均Y染色体浓度: {overfit_target1:.4f}")
    print(f"过拟合程度 - Y染色体浓度标准差: {overfit_target2:.4f}")


def create_visualizations(y_test_orig, y_pred, best_model, feature_names, X_scaled, y_scaled):
    """创建可视化图表"""
    plt.figure(figsize=(18, 10))

    # 第一个目标变量：平均Y染色体浓度的实际值 vs 预测值散点图
    plt.subplot(2, 3, 1)
    plt.scatter(y_test_orig[:, 0], y_pred[:, 0], alpha=0.6)
    min_val = min(y_test_orig[:, 0].min(), y_pred[:, 0].min())
    max_val = max(y_test_orig[:, 0].max(), y_pred[:, 0].max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2)
    plt.xlabel('实际值')
    plt.ylabel('预测值')
    plt.title('平均Y染色体浓度: 实际值 vs 预测值')
    plt.grid(True, alpha=0.3)

    # 第一个目标变量的残差图
    plt.subplot(2, 3, 2)
    residuals_target1 = y_test_orig[:, 0] - y_pred[:, 0]
    plt.scatter(y_pred[:, 0], residuals_target1, alpha=0.6)
    plt.axhline(y=0, color='r', linestyle='--')
    plt.xlabel('预测值')
    plt.ylabel('残差')
    plt.title('平均Y染色体浓度: 残差图')
    plt.grid(True, alpha=0.3)

    # 第二个目标变量：Y染色体浓度标准的实际值 vs 预测值散点图
    plt.subplot(2, 3, 4)
    plt.scatter(y_test_orig[:, 1], y_pred[:, 1], alpha=0.6)
    min_val = min(y_test_orig[:, 1].min(), y_pred[:, 1].min())
    max_val = max(y_test_orig[:, 1].max(), y_pred[:, 1].max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2)
    plt.xlabel('实际值')
    plt.ylabel('预测值')
    plt.title('Y染色体浓度标准差: 实际值 vs 预测值')
    plt.grid(True, alpha=0.3)

    # 第二个目标变量的残差图
    plt.subplot(2, 3, 5)
    residuals_target2 = y_test_orig[:, 1] - y_pred[:, 1]
    plt.scatter(y_pred[:, 1], residuals_target2, alpha=0.6)
    plt.axhline(y=0, color='r', linestyle='--')
    plt.xlabel('预测值')
    plt.ylabel('残差')
    plt.title('Y染色体浓度标准差: 残差图')
    plt.grid(True, alpha=0.3)

    # 特征重要性
    plt.subplot(2, 3, 3)
    features = feature_names
    feature_importance_target1 = best_model.estimators_[0].feature_importances_
    feature_importance_target2 = best_model.estimators_[1].feature_importances_

    importance_df = pd.DataFrame({
        '特征': features,
        '重要性_平均浓度': feature_importance_target1,
        '重要性_标准差': feature_importance_target2
    })

    print("\n特征重要性:")
    print(importance_df)

    plt.barh([0], feature_importance_target1, alpha=0.6, label='平均浓度')
    plt.barh([0.5], feature_importance_target2, alpha=0.6, label='标准差')
    plt.yticks([0, 0.5], ['平均浓度', '标准差'])
    plt.xlabel('重要性')
    plt.title('特征 (区间中点BMI) 对两个目标的重要性')
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 学习曲线分析
    print("绘制平均Y染色体浓度的学习曲线...")
    plot_learning_curve(best_model, X_scaled, y_scaled, '平均Y染色体浓度', 0)

    print("绘制Y染色体浓度标准差的学习曲线...")
    plot_learning_curve(best_model, X_scaled, y_scaled, 'Y染色体浓度标准差', 1)


def plot_learning_curve(estimator, X, y, title, target_index=0):
    """绘制学习曲线"""
    if hasattr(estimator, 'estimators_'):
        estimator = estimator.estimators_[target_index]
        y = y.iloc[:, target_index] if hasattr(y, 'iloc') else y[:, target_index]

    train_sizes, train_scores, test_scores = learning_curve(
        estimator, X, y, cv=5, n_jobs=-1,
        train_sizes=np.linspace(0.1, 1.0, 10), scoring='r2'
    )

    plt.figure(figsize=(10, 6))
    plt.plot(train_sizes, np.mean(train_scores, axis=1), 'o-', color="r", label='训练得分')
    plt.plot(train_sizes, np.mean(test_scores, axis=1), 'o-', color="g", label='交叉验证得分')
    plt.xlabel('训练样本数')
    plt.ylabel('R²得分')
    plt.title(f'学习曲线 - {title}')
    plt.legend(loc="best")
    plt.grid(True, alpha=0.3)
    plt.show()

    return train_sizes, np.mean(train_scores, axis=1), np.mean(test_scores, axis=1)


def analyze_errors(y_test_orig, y_pred):
    """分析预测误差较大的样本"""
    error_analysis = pd.DataFrame({
        '实际_平均浓度': y_test_orig[:, 0],
        '预测_平均浓度': y_pred[:, 0],
        '绝对误差_平均浓度': np.abs(y_test_orig[:, 0] - y_pred[:, 0]),
        '实际_标准差': y_test_orig[:, 1],
        '预测_标准差': y_pred[:, 1],
        '绝对误差_标准差': np.abs(y_test_orig[:, 1] - y_pred[:, 1])
    })

    print("\n平均Y染色体浓度误差最大的10个样本:")
    print(error_analysis.nlargest(10, '绝对误差_平均浓度')[['实际_平均浓度', '预测_平均浓度', '绝对误差_平均浓度']])

    print("\nY染色体浓度标准差误差最大的10个样本:")
    print(error_analysis.nlargest(10, '绝对误差_标准差')[['实际_标准差', '预测_标准差', '绝对误差_标准差']])


def perform_statistical_tests(y_test_orig, y_pred):
    """
    执行统计显著性检验
    """
    print("\n=== 改进后的显著性检验 ===")

    def perform_normality_test(data, name):
        """执行正态性检验并返回结果"""
        stat, p_value = stats.shapiro(data)
        print(f"{name} - Shapiro-Wilk正态性检验: 统计量={stat:.4f}, p值={p_value:.4e}")
        return p_value > 0.05  # 如果p>0.05，则认为正态

    # 目标1：平均Y染色体浓度的差异的正态性检验
    diff_target1 = y_test_orig[:, 0] - y_pred[:, 0]
    is_normal_target1 = perform_normality_test(diff_target1, '平均Y染色体浓度差异')

    # 目标2：Y染色体浓度标准差的差异的正态性检验
    diff_target2 = y_test_orig[:, 1] - y_pred[:, 1]
    is_normal_target2 = perform_normality_test(diff_target2, 'Y染色体浓度标准差差异')

    # 根据正态性检验结果选择适当的检验方法
    # 目标1：平均Y染色体浓度
    print("\n平均Y染色体浓度 - 统计检验:")
    if is_normal_target1:
        # 使用配对t检验
        t_stat_target1, p_value_target1 = stats.ttest_rel(y_test_orig[:, 0], y_pred[:, 0])
        print(f"使用配对t检验: t统计量={t_stat_target1:.4f}, p值={p_value_target1:.4e}")
    else:
        # 使用Wilcoxon符号秩检验
        stat_target1, p_value_target1 = stats.wilcoxon(y_test_orig[:, 0], y_pred[:, 0])
        print(f"使用Wilcoxon符号秩检验: 统计量={stat_target1:.4f}, p值={p_value_target1:.4e}")

    if p_value_target1 < 0.05:
        print("结论：预测值与实际值存在显著差异 (p < 0.05)")
    else:
        print("结论：预测值与实际值无显著差异 (p ≥ 0.05)")

    # 目标2：Y染色体浓度标准差
    print("\nY染色体浓度标准差 - 统计检验:")
    if is_normal_target2:
        # 使用配对t检验
        t_stat_target2, p_value_target2 = stats.ttest_rel(y_test_orig[:, 1], y_pred[:, 1])
        print(f"使用配对t检验: t统计量={t_stat_target2:.4f}, p值={p_value_target2:.4e}")
    else:
        # 使用Wilcoxon符号秩检验
        stat_target2, p_value_target2 = stats.wilcoxon(y_test_orig[:, 1], y_pred[:, 1])
        print(f"使用Wilcoxon符号秩检验: 统计量={stat_target2:.4f}, p值={p_value_target2:.4e}")

    if p_value_target2 < 0.05:
        print("结论：预测值与实际值存在显著差异 (p < 0.05)")
    else:
        print("结论：预测值与实际值无显著差异 (p ≥ 0.05)")


if __name__ == "__main__":
    main()