import numpy as np
from django.utils import timezone
from datetime import timedelta
from .models import SleepSession, SleepData
import json

def generate_sleep_data(duration_hours=8, quality='GOOD'):
    """
    Tạo dữ liệu mẫu cho một phiên ngủ
    """
    # Số điểm dữ liệu (1 điểm mỗi phút)
    num_points = int(duration_hours * 60)
    
    # Tạo timestamp cho mỗi điểm dữ liệu
    timestamps = [timezone.now() - timedelta(minutes=i) for i in range(num_points)]
    
    # Tạo dữ liệu dựa trên chất lượng giấc ngủ
    if quality == 'GOOD':
        # Giấc ngủ tốt: đáp ứng 3-4 tiêu chí
        # Nhịp tim ổn định (60-80)
        heart_rates = np.random.normal(65, 5, num_points)
        # SpO2 cao (96-100)
        spo2_values = np.random.normal(98, 0.5, num_points)
        # Nhiệt độ cơ thể (36.5-37.0)
        temperatures = np.random.normal(36.5, 0.2, num_points)
        # Gia tốc gần với 1 (ít chuyển động)
        accelerations = 1 + np.random.normal(0, 0.05, num_points)
    elif quality == 'MEDIUM':
        # Giấc ngủ trung bình: đáp ứng 2 tiêu chí
        # Nhịp tim không ổn định
        heart_rates = np.random.normal(70, 8, num_points)
        # SpO2 trung bình
        spo2_values = np.random.normal(96, 1, num_points)
        # Nhiệt độ cơ thể
        temperatures = np.random.normal(36.7, 0.3, num_points)
        # Gia tốc lệch nhiều hơn so với 1
        accelerations = 1 + np.random.normal(0, 0.15, num_points)
    else:  # BAD
        # Giấc ngủ không tốt: đáp ứng 0-1 tiêu chí
        # Nhịp tim không ổn định
        heart_rates = np.random.normal(75, 10, num_points)
        # SpO2 thấp
        spo2_values = np.random.normal(94, 1.5, num_points)
        # Nhiệt độ cơ thể
        temperatures = np.random.normal(37.0, 0.4, num_points)
        # Gia tốc lệch nhiều so với 1
        accelerations = 1 + np.random.normal(0, 0.3, num_points)
    
    # Đảm bảo các giá trị nằm trong khoảng hợp lệ
    heart_rates = np.clip(heart_rates, 40, 100)
    spo2_values = np.clip(spo2_values, 90, 100)
    temperatures = np.clip(temperatures, 35, 38)
    accelerations = np.clip(accelerations, 0.5, 1.5)  # Giới hạn gia tốc trong khoảng 0.5-1.5
    
    return list(zip(timestamps, heart_rates, spo2_values, temperatures, accelerations))

def create_mock_sessions(num_sessions=150):
    """
    Tạo dữ liệu mẫu cho nhiều phiên ngủ
    """
    # Phân bố chất lượng giấc ngủ
    qualities = ['GOOD', 'MEDIUM', 'BAD']
    quality_weights = [0.4, 0.4, 0.2]  # 40% tốt, 40% trung bình, 20% không tốt
    
    for i in range(num_sessions):
        # Tạo phiên ngủ mới
        duration = np.random.normal(7, 1)  # Thời lượng ngủ trung bình 7 giờ
        quality = np.random.choice(qualities, p=quality_weights)
        
        session = SleepSession.objects.create(
            start_time=timezone.now() - timedelta(days=i),
            end_time=timezone.now() - timedelta(days=i) + timedelta(hours=duration),
            quality=quality
        )
        
        # Tạo dữ liệu cho phiên ngủ
        sleep_data = generate_sleep_data(duration, quality)
        
        # Lưu dữ liệu vào database
        for timestamp, hr, spo2, temp, acc in sleep_data:
            SleepData.objects.create(
                session=session,
                timestamp=timestamp,
                heart_rate=hr,
                spo2=spo2,
                temperature=temp,
                acceleration=acc
            )
        
        if (i + 1) % 10 == 0:  # In thông báo sau mỗi 10 phiên thay vì 100
            print(f"Đã tạo {i + 1} phiên ngủ")

if __name__ == '__main__':
    create_mock_sessions() 