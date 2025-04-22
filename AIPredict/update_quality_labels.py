import os
import numpy as np
import joblib
from django.conf import settings
from .models import SleepSession, SleepData
from .views import calculate_sleep_quality

def update_session_qualities():
    """
    Cập nhật lại nhãn chất lượng cho tất cả các phiên ngủ dựa trên mô hình AI hiện tại
    """
    print("Bắt đầu cập nhật nhãn chất lượng...")
    
    # Load AI model và scaler
    model = None
    scaler = None
    try:
        model_path = os.path.join(settings.BASE_DIR, 'AIPredict', 'models', 'sleep_model.joblib')
        scaler_path = os.path.join(settings.BASE_DIR, 'AIPredict', 'models', 'scaler.joblib')
        
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            print("Đã tải mô hình AI thành công")
        else:
            print("Không tìm thấy file mô hình AI, sẽ sử dụng phương pháp heuristic")
    except Exception as e:
        print(f"Lỗi khi tải mô hình AI: {e}")
        print("Sẽ sử dụng phương pháp heuristic")
    
    # Lấy tất cả các phiên ngủ
    sessions = SleepSession.objects.all()
    total_sessions = sessions.count()
    print(f"Tìm thấy {total_sessions} phiên ngủ cần cập nhật")
    
    # Đếm số lượng phiên theo chất lượng
    quality_counts = {'GOOD': 0, 'MEDIUM': 0, 'BAD': 0}
    
    # Cập nhật từng phiên
    for i, session in enumerate(sessions, 1):
        # Lấy dữ liệu ngủ của phiên
        sleep_data = SleepData.objects.filter(session=session).order_by('timestamp')
        
        if not sleep_data.exists():
            print(f"Phiên {session.id} không có dữ liệu, bỏ qua")
            continue
        
        # Tính toán các chỉ số trung bình
        heart_rates = [data.heart_rate for data in sleep_data]
        spo2_values = [data.spo2 for data in sleep_data]
        temperatures = [data.temperature for data in sleep_data]
        accelerations = [data.acceleration for data in sleep_data]
        
        # Tính các thống kê
        hr_mean = float(np.mean(heart_rates))
        hr_std = float(np.std(heart_rates))
        spo2_mean = float(np.mean(spo2_values))
        spo2_std = float(np.std(spo2_values))
        temp_mean = float(np.mean(temperatures))
        temp_std = float(np.std(temperatures))
        acc_mean = float(np.mean(accelerations))
        acc_std = float(np.std(accelerations))
        
        # Tính độ lệch gia tốc
        acceleration_deviations = [abs(acc - 1) for acc in accelerations]
        acc_dev_mean = float(np.mean(acceleration_deviations))
        acc_dev_max = float(np.max(acceleration_deviations))
        
        # Tính IQR của nhịp tim
        hr_q75 = float(np.percentile(heart_rates, 75))
        hr_q25 = float(np.percentile(heart_rates, 25))
        hr_iqr = float(hr_q75 - hr_q25)
        
        # Sử dụng mô hình AI nếu có
        if model and scaler:
            # Chuẩn bị vector đặc trưng
            features = np.array([[
                hr_mean, hr_std, spo2_mean, spo2_std,
                temp_mean, temp_std, acc_mean, acc_std,
                acc_dev_mean, acc_dev_max, hr_iqr
            ]])
            
            # Chuẩn hóa đặc trưng
            features_scaled = scaler.transform(features)
            
            # Dự đoán chất lượng
            quality_score = float(model.predict(features_scaled)[0])
        else:
            # Sử dụng phương pháp heuristic
            quality_score = calculate_sleep_quality(
                hr_mean, spo2_mean, temp_mean, acc_mean
            )
        
        # Chuyển đổi điểm số thành nhãn chất lượng
        if abs(quality_score - 3) <= abs(quality_score - 2) and abs(quality_score - 3) <= abs(quality_score - 1):
            new_quality = 'GOOD'
        elif abs(quality_score - 2) <= abs(quality_score - 3) and abs(quality_score - 2) <= abs(quality_score - 1):
            new_quality = 'MEDIUM'
        else:
            new_quality = 'BAD'
        
        # Cập nhật nhãn mới
        old_quality = session.quality
        session.quality = new_quality
        session.save()
        
        # Cập nhật đếm số lượng
        quality_counts[new_quality] += 1
        
        # In tiến trình
        if i % 10 == 0 or i == total_sessions:
            print(f"Đã cập nhật {i}/{total_sessions} phiên")
            print(f"Phiên {session.id}: {old_quality} -> {new_quality}")
    
    # In thống kê cuối cùng
    print("\nThống kê chất lượng giấc ngủ:")
    print(f"Tốt (GOOD): {quality_counts['GOOD']} phiên ({quality_counts['GOOD']/total_sessions*100:.1f}%)")
    print(f"Trung bình (MEDIUM): {quality_counts['MEDIUM']} phiên ({quality_counts['MEDIUM']/total_sessions*100:.1f}%)")
    print(f"Kém (BAD): {quality_counts['BAD']} phiên ({quality_counts['BAD']/total_sessions*100:.1f}%)")
    print("\nHoàn thành cập nhật nhãn chất lượng!")

if __name__ == '__main__':
    update_session_qualities() 