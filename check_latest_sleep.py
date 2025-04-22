import os
import django
import sys
from datetime import datetime
import pytz

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WebLtn.settings')
django.setup()

from AIPredict.models import SleepSession, SleepData

def check_latest_sleep():
    # Get the latest session
    latest_session = SleepSession.objects.order_by('-start_time').first()
    
    if not latest_session:
        print("Không tìm thấy phiên ngủ nào trong cơ sở dữ liệu.")
        return
    
    # Convert to GMT+7
    tz = pytz.timezone('Asia/Bangkok')
    start_time = latest_session.start_time.astimezone(tz)
    end_time = latest_session.end_time.astimezone(tz)
    
    print("\n=== THÔNG TIN PHIÊN NGỦ MỚI NHẤT ===")
    print(f"ID phiên: {latest_session.id}")
    print(f"Thời gian bắt đầu (GMT+7): {start_time}")
    print(f"Thời gian kết thúc (GMT+7): {end_time}")
    print(f"Chất lượng ngủ: {latest_session.quality}")
    
    # Get sleep data points
    sleep_data = SleepData.objects.filter(session=latest_session).order_by('timestamp')
    print(f"\nSố lượng điểm dữ liệu: {sleep_data.count()}")
    
    if sleep_data.exists():
        print("\n=== DỮ LIỆU CHI TIẾT (GMT+7) ===")
        print("Thời gian | Nhịp tim | SpO2 | Nhiệt độ | Gia tốc")
        print("-" * 65)
        
        for data in sleep_data:
            local_time = data.timestamp.astimezone(tz)
            print(f"{local_time.strftime('%H:%M:%S')} | {data.heart_rate:8.1f} | {data.spo2:4.1f} | {data.temperature:8.1f} | {data.acceleration:8.1f}")

if __name__ == "__main__":
    check_latest_sleep() 