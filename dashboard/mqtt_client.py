import paho.mqtt.client as mqtt
import json
from datetime import datetime, timedelta
import pytz
from .models import SensorData, Settings, SleepSession
from django.db.models import Avg
import threading
import time

# Global MQTT client
mqtt_client = None
mqtt_thread = None
mqtt_lock = threading.Lock()  # Khóa để đảm bảo chỉ có một instance MQTT
client_id = f"dashboard_client_{int(time.time())}"  # Client ID cố định

# Biến theo dõi tin nhắn đã xử lý để tránh lặp lại
processed_messages = set()
MAX_PROCESSED_MESSAGES = 100  # Giới hạn kích thước để tránh memory leak

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.is_connected = False
        self.settings = None
        self.sleep_data = {
            'is_sleeping': False,
            'start_time': None,
        }
        self.acceleration_buffer = []
        self.movement_threshold = 0.2  # Ngưỡng phát hiện chuyển động (0.2g)
        self.deep_sleep_threshold = 0.1  # Ngưỡng phát hiện ngủ sâu (0.1g)
        self.buffer_size = 300  # Kích thước buffer cho 5 phút (300 giây)

    def connect(self):
        try:
            # Lấy settings từ database
            self.settings = Settings.objects.first()
            if not self.settings:
                print("No settings found in database")
                return False

            # Thiết lập TLS
            self.client.tls_set()
            self.client.username_pw_set(self.settings.mqtt_username, self.settings.mqtt_password)
            
            # Kết nối tới broker
            self.client.connect(self.settings.mqtt_broker, self.settings.mqtt_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"Error connecting to MQTT broker: {e}")
            return False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT broker")
            self.is_connected = True
            self.client.subscribe(self.settings.mqtt_topic)
            self.client.subscribe("sleep")  # Subscribe to sleep topic
        else:
            print(f"Failed to connect to MQTT broker with code: {rc}")
            self.is_connected = False

    def analyze_sleep(self, acceleration_data):
        """Phân tích dữ liệu giấc ngủ từ buffer acceleration"""
        if not acceleration_data:
            return None, 0, 0, 0, 0

        # Tính toán các thông số
        total_samples = len(acceleration_data)
        deep_sleep_samples = sum(1 for acc in acceleration_data if abs(acc - 1.0) < self.deep_sleep_threshold)
        wake_samples = sum(1 for acc in acceleration_data if abs(acc - 1.0) > self.movement_threshold)
        light_sleep_samples = total_samples - deep_sleep_samples - wake_samples

        # Tính thời lượng (giả sử mỗi sample cách nhau 1 giây)
        deep_sleep_duration = timedelta(seconds=deep_sleep_samples)
        light_sleep_duration = timedelta(seconds=light_sleep_samples)
        wake_duration = timedelta(seconds=wake_samples)
        total_duration = timedelta(seconds=total_samples)

        # Tính điểm chất lượng giấc ngủ
        deep_sleep_score = (deep_sleep_samples / total_samples) * 100
        wake_score = (wake_samples / total_samples) * 100
        movement_count = wake_samples

        # Xác định chất lượng giấc ngủ
        if deep_sleep_score >= 20 and wake_score <= 15:
            quality = 'GOOD'
        elif deep_sleep_score >= 10 and wake_score <= 25:
            quality = 'AVERAGE'
        else:
            quality = 'BAD'

        return quality, total_duration, deep_sleep_duration, light_sleep_duration, wake_duration, movement_count

    def on_message(self, client, userdata, msg):
        try:
            if msg.topic == "sleep":
                # Xử lý tín hiệu bắt đầu/kết thúc ngủ
                payload = msg.payload.decode()
                if payload == "1" and not self.sleep_data['is_sleeping']:
                    # Bắt đầu ngủ
                    self.sleep_data['is_sleeping'] = True
                    self.sleep_data['start_time'] = datetime.now(pytz.UTC)
                    self.acceleration_buffer = []
                    print("Sleep session started")
                elif payload == "0" and self.sleep_data['is_sleeping']:
                    # Kết thúc ngủ
                    end_time = datetime.now(pytz.UTC)
                    if len(self.acceleration_buffer) > 0:
                        # Phân tích dữ liệu giấc ngủ
                        quality, total_duration, deep_duration, light_duration, wake_duration, movement_count = self.analyze_sleep(self.acceleration_buffer)
                        
                        # Lưu phiên ngủ vào database
                        SleepSession.objects.create(
                            start_time=self.sleep_data['start_time'],
                            end_time=end_time,
                            quality=quality,
                            total_duration=total_duration,
                            deep_sleep_duration=deep_duration,
                            light_sleep_duration=light_duration,
                            wake_duration=wake_duration,
                            avg_acceleration=sum(self.acceleration_buffer) / len(self.acceleration_buffer),
                            movement_count=movement_count
                        )
                        print(f"Sleep session ended. Quality: {quality}")
                    
                    # Reset trạng thái
                    self.sleep_data['is_sleeping'] = False
                    self.sleep_data['start_time'] = None
                    self.acceleration_buffer = []
                return

            # Xử lý dữ liệu sensor thông thường
            payload = json.loads(msg.payload.decode())
            timestamp = datetime.fromtimestamp(payload['timestamp'], pytz.UTC)
            
            # Lấy ngưỡng từ settings
            heart_rate_min = self.settings.heart_rate_min
            heart_rate_max = self.settings.heart_rate_max
            spo2_min = self.settings.spo2_min
            temperature_min = self.settings.temperature_min
            temperature_max = self.settings.temperature_max
            acceleration_min = self.settings.acceleration_min
            acceleration_max = self.settings.acceleration_max

            # Kiểm tra giá trị bất thường
            is_abnormal = (
                payload['heartRate'] < heart_rate_min or
                payload['heartRate'] > heart_rate_max or
                payload['spo2'] < spo2_min or
                payload['temperature'] < temperature_min or
                payload['temperature'] > temperature_max
            )

            # Kiểm tra ngã
            is_fall = (
                payload['acceleration'] < acceleration_min or
                payload['acceleration'] > acceleration_max
            )

            # Lưu dữ liệu vào database
            SensorData.objects.create(
                timestamp=timestamp,
                heartRate=payload['heartRate'],
                spo2=payload['spo2'],
                temperature=payload['temperature'],
                acceleration=payload['acceleration'],
                is_abnormal=is_abnormal,
                is_fall=is_fall
            )

            # Nếu đang trong phiên ngủ, thêm acceleration vào buffer
            if self.sleep_data['is_sleeping']:
                self.acceleration_buffer.append(payload['acceleration'])
                # Giới hạn kích thước buffer
                if len(self.acceleration_buffer) > self.buffer_size:
                    self.acceleration_buffer.pop(0)

        except Exception as e:
            print(f"Error processing message: {e}")

    def disconnect(self):
        if self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            print("Disconnected from MQTT broker")

def get_settings():
    settings, _ = Settings.objects.get_or_create(pk=1)
    return settings

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    settings = get_settings()
    client.subscribe(settings.mqtt_topic)
    # Send current settings to device on connect
    publish_settings()

def on_message(client, userdata, msg):
    try:
        # Tạo message ID dựa trên nội dung và thời gian
        message_content = msg.payload.decode()
        message_id = f"{message_content}_{int(time.time() / 10)}"  # Phân nhóm theo 10 giây
        
        # Kiểm tra nếu đã xử lý tin nhắn này
        with mqtt_lock:
            if message_id in processed_messages:
                print(f"Skipping duplicate message: {message_content[:30]}...")
                return
            
            # Thêm vào danh sách đã xử lý
            processed_messages.add(message_id)
            
            # Giới hạn kích thước của set
            if len(processed_messages) > MAX_PROCESSED_MESSAGES:
                # Xóa phần tử cũ nhất (giả định là phần tử đầu tiên)
                processed_messages.pop()
        
        payload = json.loads(message_content)
        print(f"Processing message: {payload}")  # Debug print
        
        # Skip if any sensor value is 0
        if (payload['heartRate'] == 0 or 
            payload['spo2'] == 0 or 
            payload['temperature'] == 0 or 
            payload['acceleration'] == 0):
            print("Skipping data with zero values")
            return
        
        # Get current settings
        settings = get_settings()
        
        # Check for fall condition
        is_fall = (payload['acceleration'] > settings.acceleration_max or 
                  payload['acceleration'] < settings.acceleration_min)
        
        # Check for abnormal conditions
        is_abnormal = (
            payload['heartRate'] < settings.heart_rate_min or 
            payload['heartRate'] > settings.heart_rate_max or
            payload['spo2'] < settings.spo2_min or
            payload['temperature'] < settings.temperature_min or 
            payload['temperature'] > settings.temperature_max
        )
        
        # Save to database with current timestamp
        SensorData.objects.create(
            timestamp=timezone.now(),
            heartRate=payload['heartRate'],
            spo2=payload['spo2'],
            temperature=payload['temperature'],
            acceleration=payload['acceleration'],
            is_fall=is_fall,
            is_abnormal=is_abnormal
        )
        print(f"Data saved successfully: {payload}")  # Debug print
        
    except Exception as e:
        print(f"Error processing message: {e}")
        print(f"Payload content: {msg.payload.decode()}")  # Debug print

def publish_settings():
    """Publish current threshold settings to the device"""
    if mqtt_client is None:
        print("MQTT client not initialized yet")
        return False
    
    try:
        settings = get_settings()
        
        # Create settings payload in the format the device expects
        settings_payload = {
            "heartRateHigh": settings.heart_rate_max,
            "heartRateLow": settings.heart_rate_min,
            "spo2": settings.spo2_min,
            "tempHigh": settings.temperature_max,
            "tempLow": settings.temperature_min,
            "accLow": settings.acceleration_min,
            "accHigh": settings.acceleration_max
        }
        
        # Convert to JSON
        payload = json.dumps(settings_payload)
        
        # Publish to settings topic
        result = mqtt_client.publish("sensor/settings", payload, qos=1, retain=True)
        
        # Check if the message was published successfully
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Settings published: {payload}")
            return True
        else:
            print(f"Failed to publish settings. Error code: {result.rc}")
            return False
            
    except Exception as e:
        print(f"Error publishing settings: {e}")
        return False

def mqtt_loop(client):
    """Run the MQTT loop forever in a thread"""
    try:
        client.loop_forever()
    except Exception as e:
        print(f"MQTT loop stopped: {e}")

def start_mqtt_client():
    global mqtt_client, mqtt_thread
    
    # Sử dụng khóa để đảm bảo chỉ có một thread gọi hàm này tại mỗi thời điểm
    with mqtt_lock:
        # Kiểm tra nếu đã có client đang chạy
        if mqtt_client is not None and mqtt_thread is not None and mqtt_thread.is_alive():
            print("MQTT client already running")
            return True
        
        # Stop existing client if any
        if mqtt_client:
            try:
                mqtt_client.disconnect()  # This will cause loop_forever() to exit
                
                # Wait for thread to terminate
                if mqtt_thread and mqtt_thread.is_alive():
                    mqtt_thread.join(timeout=2.0)  # Wait up to 2 seconds
                    print("Previous MQTT thread stopped")
            except Exception as e:
                print(f"Error stopping previous MQTT client: {e}")
        
        # Reset client variables to ensure clean state
        mqtt_client = None
        mqtt_thread = None
        
        # Get settings
        settings = get_settings()
        
        # Create new client
        mqtt_client = MQTTClient()
        
        # Start client in a separate thread using loop_forever
        mqtt_thread = threading.Thread(target=mqtt_loop, args=(mqtt_client,))
        mqtt_thread.daemon = True
        mqtt_thread.start()
        
        print(f"MQTT client started successfully with client ID: {client_id}")
        return True

def restart_mqtt_client():
    """Restart the MQTT client with current settings"""
    print("Restarting MQTT client...")
    success = start_mqtt_client()
    return success 