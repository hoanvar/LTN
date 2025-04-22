import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
import joblib
from django.conf import settings
from .models import SleepSession, SleepData

def prepare_training_data():
    """
    Chuẩn bị dữ liệu training từ database theo giờ
    """
    # Lấy tất cả các phiên ngủ đã có đánh giá chất lượng
    sessions = SleepSession.objects.exclude(quality__isnull=True)
    
    features = []
    labels = []
    
    for session in sessions:
        # Lấy tất cả data points của phiên ngủ
        data_points = session.data_points.all()
        
        if not data_points:
            continue
        
        # Nhóm dữ liệu theo giờ
        hourly_data = {}
        for dp in data_points:
            hour = dp.timestamp.hour
            if hour not in hourly_data:
                hourly_data[hour] = {
                    'heart_rate': [],
                    'spo2': [],
                    'temperature': [],
                    'acceleration': []
                }
            
            hourly_data[hour]['heart_rate'].append(dp.heart_rate)
            hourly_data[hour]['spo2'].append(dp.spo2)
            hourly_data[hour]['temperature'].append(dp.temperature)
            hourly_data[hour]['acceleration'].append(dp.acceleration)
        
        # Tính toán đặc trưng cho mỗi giờ
        for hour, data in hourly_data.items():
            if not data['heart_rate']:
                continue
                
            # Tính toán các đặc trưng từ data points
            heart_rates = data['heart_rate']
            spo2_values = data['spo2']
            temperatures = data['temperature']
            accelerations = data['acceleration']
            
            # Tính toán độ chênh lệch của gia tốc so với 1
            acceleration_deviations = [abs(acc - 1) for acc in accelerations]
            
            # Tính các thống kê cơ bản
            hour_features = [
                np.mean(heart_rates),
                np.std(heart_rates),
                np.mean(spo2_values),
                np.std(spo2_values),
                np.mean(temperatures),
                np.std(temperatures),
                np.mean(accelerations),
                np.std(accelerations),
                np.mean(acceleration_deviations),  # Độ chênh lệch trung bình so với 1
                np.max(acceleration_deviations),   # Độ chênh lệch lớn nhất so với 1
                np.percentile(heart_rates, 75) - np.percentile(heart_rates, 25),  # IQR của nhịp tim
            ]
            
            features.append(hour_features)
            
            # Sử dụng chất lượng thực tế từ database
            if session.quality == 'GOOD':
                labels.append(3)
            elif session.quality == 'MEDIUM':
                labels.append(2)
            else:  # BAD
                labels.append(1)
    
    return np.array(features), np.array(labels)

def train_model():
    """
    Train model AI với dữ liệu từ database
    """
    # Chuẩn bị dữ liệu
    X, y = prepare_training_data()
    
    if len(X) == 0:
        print("Không có đủ dữ liệu để train model!")
        return False
    
    # Chia dữ liệu thành tập train và test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Chuẩn hóa dữ liệu
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Tính toán class weights để cân bằng dữ liệu
    # Mục tiêu: 40% GOOD, 40% MEDIUM, 20% BAD
    target_distribution = {1: 0.2, 2: 0.4, 3: 0.4}  # BAD: 20%, MEDIUM: 40%, GOOD: 40%
    class_weights = compute_class_weight(
        class_weight='balanced',
        classes=np.unique(y_train),
        y=y_train
    )
    
    # Điều chỉnh class weights để đạt được phân bố mong muốn
    class_weight_dict = {1: class_weights[0], 2: class_weights[1], 3: class_weights[2]}
    
    # Train model với class weights
    model = RandomForestClassifier(
        n_estimators=200,  # Tăng số lượng cây
        max_depth=10,      # Giới hạn độ sâu để tránh overfitting
        min_samples_split=5,  # Tăng số lượng mẫu tối thiểu để split
        min_samples_leaf=3,   # Tăng số lượng mẫu tối thiểu ở leaf
        class_weight=class_weight_dict,
        random_state=42
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Đánh giá model
    train_score = model.score(X_train_scaled, y_train)
    test_score = model.score(X_test_scaled, y_test)
    
    # Tính phân bố dự đoán trên tập test
    y_pred = model.predict(X_test_scaled)
    unique, counts = np.unique(y_pred, return_counts=True)
    pred_distribution = dict(zip(unique, counts / len(y_pred)))
    
    print(f"Train accuracy: {train_score:.2f}")
    print(f"Test accuracy: {test_score:.2f}")
    print("\nPhân bố dự đoán trên tập test:")
    print(f"GOOD (3): {pred_distribution.get(3, 0)*100:.1f}%")
    print(f"MEDIUM (2): {pred_distribution.get(2, 0)*100:.1f}%")
    print(f"BAD (1): {pred_distribution.get(1, 0)*100:.1f}%")
    
    # Lưu model và scaler
    models_dir = os.path.join(settings.BASE_DIR, 'AIPredict', 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    joblib.dump(model, os.path.join(models_dir, 'sleep_model.joblib'))
    joblib.dump(scaler, os.path.join(models_dir, 'scaler.joblib'))
    
    print("\nModel đã được train và lưu thành công!")
    return True

if __name__ == '__main__':
    train_model() 