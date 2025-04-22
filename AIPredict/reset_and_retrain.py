import os
from django.conf import settings
from .models import SleepSession, SleepData
from .create_mock_data import create_mock_sessions
from .train_model import train_model

def reset_and_retrain(num_sessions=150):
    """
    Reset database, create new mock data with correct distribution, and retrain AI model
    """
    print("Bắt đầu quá trình reset và huấn luyện lại...")
    
    # Xóa tất cả dữ liệu hiện tại
    print("Xóa dữ liệu cũ...")
    SleepData.objects.all().delete()
    SleepSession.objects.all().delete()
    
    # Tạo dữ liệu mẫu mới
    print(f"Tạo {num_sessions} phiên ngủ mẫu mới...")
    create_mock_sessions(num_sessions)
    
    # Huấn luyện lại mô hình AI
    print("Huấn luyện lại mô hình AI...")
    train_model()
    
    # Kiểm tra phân bố nhãn
    sessions = SleepSession.objects.all()
    total = sessions.count()
    
    good_count = sessions.filter(quality='GOOD').count()
    medium_count = sessions.filter(quality='MEDIUM').count()
    bad_count = sessions.filter(quality='BAD').count()
    
    print("\nPhân bố nhãn sau khi tạo dữ liệu mẫu:")
    print(f"GOOD: {good_count} phiên ({good_count/total*100:.1f}%)")
    print(f"MEDIUM: {medium_count} phiên ({medium_count/total*100:.1f}%)")
    print(f"BAD: {bad_count} phiên ({bad_count/total*100:.1f}%)")
    
    print("\nHoàn thành quá trình reset và huấn luyện lại!")

if __name__ == '__main__':
    reset_and_retrain() 