import os
import django
import sys
from datetime import datetime
import pytz

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WebLtn.settings')
django.setup()

from AIPredict.models import SleepData
from django.db import connection

def check_latest_sleep_data():
    # Get the 10 most recent sleep data entries
    latest_data = SleepData.objects.order_by('-timestamp')[:10]
    
    if not latest_data:
        print("Không tìm thấy dữ liệu ngủ nào trong cơ sở dữ liệu.")
        return
    
    print("\n=== 10 DỮ LIỆU NGỦ MỚI NHẤT ===")
    print("ID | Thời gian (UTC) | Thời gian (GMT+7) | Phiên | Nhịp tim | SpO2 | Nhiệt độ | Gia tốc")
    print("-" * 120)
    
    tz = pytz.timezone('Asia/Bangkok')
    
    for data in latest_data:
        # Get raw timestamp from database
        with connection.cursor() as cursor:
            cursor.execute("SELECT timestamp FROM aipredict_sleepdata WHERE id = %s", [data.id])
            raw_timestamp = cursor.fetchone()[0]
        
        # Convert to GMT+7
        local_time = raw_timestamp.astimezone(tz)
        
        print(f"{data.id:3d} | {raw_timestamp} | {local_time} | {data.session.id:5d} | {data.heart_rate:8.1f} | {data.spo2:4.1f} | {data.temperature:8.1f} | {data.acceleration:8.1f}")

if __name__ == "__main__":
    check_latest_sleep_data() 