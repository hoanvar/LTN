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
from django.db import connection

def check_raw_timestamps():
    # Get the latest session
    latest_session = SleepSession.objects.order_by('-start_time').first()
    
    if not latest_session:
        print("Không tìm thấy phiên ngủ nào trong cơ sở dữ liệu.")
        return
    
    print("\n=== KIỂM TRA THỜI GIAN GỐC TRONG DATABASE ===")
    print(f"ID phiên: {latest_session.id}")
    
    # Get raw timestamp from database
    with connection.cursor() as cursor:
        cursor.execute("SELECT start_time, end_time FROM aipredict_sleepsession WHERE id = %s", [latest_session.id])
        raw_start, raw_end = cursor.fetchone()
        print(f"Thời gian bắt đầu (gốc): {raw_start}")
        print(f"Thời gian kết thúc (gốc): {raw_end}")
    
    # Get raw sleep data timestamps
    with connection.cursor() as cursor:
        cursor.execute("SELECT timestamp FROM aipredict_sleepdata WHERE session_id = %s ORDER BY timestamp", [latest_session.id])
        raw_timestamps = cursor.fetchall()
        
        print("\n=== THỜI GIAN GỐC CỦA CÁC ĐIỂM DỮ LIỆU ===")
        for ts in raw_timestamps:
            print(f"Timestamp gốc: {ts[0]}")
            
    # Compare with Django ORM values
    print("\n=== SO SÁNH VỚI GIÁ TRỊ TỪ DJANGO ORM ===")
    print(f"Django ORM start_time: {latest_session.start_time}")
    print(f"Django ORM end_time: {latest_session.end_time}")
    
    sleep_data = SleepData.objects.filter(session=latest_session).order_by('timestamp')
    for data in sleep_data:
        print(f"Django ORM timestamp: {data.timestamp}")

if __name__ == "__main__":
    check_raw_timestamps() 