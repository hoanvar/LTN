import paho.mqtt.client as mqtt
import json
from .models import SensorData, Settings
from django.utils import timezone
import threading
import time
from .email_utils import send_fall_alert

# Global MQTT client
mqtt_client = None
mqtt_thread = None
mqtt_lock = threading.Lock()  # Khóa để đảm bảo chỉ có một instance MQTT
client_id = f"dashboard_client_{int(time.time())}"  # Client ID cố định

# Biến theo dõi tin nhắn đã xử lý để tránh lặp lại
processed_messages = set()
MAX_PROCESSED_MESSAGES = 100  # Giới hạn kích thước để tránh memory leak

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
        payload = json.loads(msg.payload.decode())
        print(f"Received message: {payload}")

        # Skip if any sensor value is 0
        if any(value == 0 for value in [
            payload.get('heartRate', 0),
            payload.get('spo2', 0),
            payload.get('temperature', 0),
            payload.get('acceleration', 0)
        ]):
            print("Skipping data with zero values")
            return

        # Create sensor data object
        sensor_data = SensorData(
            timestamp=timezone.now(),
            heartRate=payload.get('heartRate', 0),
            spo2=payload.get('spo2', 0),
            temperature=payload.get('temperature', 0),
            acceleration=payload.get('acceleration', 0)
        )

        # Check for abnormal values
        settings = Settings.objects.first()
        if settings:
            # Check for fall detection
            if sensor_data.acceleration >= settings.acceleration_max or sensor_data.acceleration <= settings.acceleration_min:
                print("Fall detected!")
                sensor_data.is_fall = True
                # Send email alert
                send_fall_alert(sensor_data)

            # Check other vital signs
            if (sensor_data.heartRate < settings.heart_rate_min or 
                sensor_data.heartRate > settings.heart_rate_max):
                sensor_data.is_abnormal = True
            elif (sensor_data.spo2 < settings.spo2_min or 
                  sensor_data.spo2 > settings.spo2_max):
                sensor_data.is_abnormal = True
            elif (sensor_data.temperature < settings.temperature_min or 
                  sensor_data.temperature > settings.temperature_max):
                sensor_data.is_abnormal = True

        # Save to database
        sensor_data.save()
        print(f"Saved sensor data: {sensor_data}")

    except json.JSONDecodeError:
        print("Error decoding JSON message")
    except Exception as e:
        print(f"Error processing message: {str(e)}")

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
        print("\n=== MQTT Loop Started ===")
        print(f"Thread ID: {threading.get_ident()}")
        print(f"Client ID: {client._client_id}")
        client.loop_forever()
    except Exception as e:
        print(f"MQTT loop stopped: {e}")

def start_mqtt_client():
    global mqtt_client, mqtt_thread
    
    # Sử dụng khóa để đảm bảo chỉ có một thread gọi hàm này tại mỗi thời điểm
    with mqtt_lock:
        # Kiểm tra nếu đã có client đang chạy
        if mqtt_client is not None and mqtt_thread is not None and mqtt_thread.is_alive():
            print("\n=== MQTT client already running ===")
            print(f"Thread ID: {mqtt_thread.ident}")
            print(f"Thread alive: {mqtt_thread.is_alive()}")
            return True
        
        # Stop existing client if any
        if mqtt_client:
            try:
                print("\n=== Stopping existing MQTT client ===")
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
        mqtt_client = mqtt.Client(client_id=client_id)  # Sử dụng client ID cố định
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        
        # Set authentication
        mqtt_client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        
        # Set TLS/SSL
        mqtt_client.tls_set()
        
        try:
            # Connect to broker
            print("\n=== Connecting to MQTT broker ===")
            print(f"Broker: {settings.mqtt_broker}")
            print(f"Port: {settings.mqtt_port}")
            print(f"Client ID: {client_id}")
            mqtt_client.connect(settings.mqtt_broker, settings.mqtt_port, 60)
            
            # Start client in a separate thread using loop_forever
            mqtt_thread = threading.Thread(target=mqtt_loop, args=(mqtt_client,))
            mqtt_thread.daemon = True
            mqtt_thread.start()
            
            print(f"MQTT client started successfully with client ID: {client_id}")
            print(f"Thread ID: {mqtt_thread.ident}")
            return True
        except Exception as e:
            print(f"Error connecting to MQTT broker: {e}")
            return False

def restart_mqtt_client():
    """Restart the MQTT client with current settings"""
    print("Restarting MQTT client...")
    success = start_mqtt_client()
    return success 