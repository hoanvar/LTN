import json
import paho.mqtt.client as mqtt
from django.conf import settings
from .models import SleepSession, SleepData
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
from django.utils import timezone
# Import MQTT client from dashboard
from dashboard.mqtt_client import mqtt_client, start_mqtt_client

class SleepAnalyzer:
    def __init__(self):
        self.current_session = None
        self.data_buffer = []
        self.model = None
        self.scaler = None
        self.load_model()
        print("\n=== Sleep Analyzer Initialized ===")
        print("Waiting for sleep session to start...")
        
    def load_model(self):
        model_path = os.path.join(settings.BASE_DIR, 'AIPredict', 'models', 'sleep_model.joblib')
        scaler_path = os.path.join(settings.BASE_DIR, 'AIPredict', 'models', 'scaler.joblib')
        
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            print("AI model loaded successfully")
        else:
            self.model = RandomForestClassifier(n_estimators=100)
            self.scaler = StandardScaler()
            print("No AI model found, using default model")
    
    def save_model(self):
        model_path = os.path.join(settings.BASE_DIR, 'AIPredict', 'models', 'sleep_model.joblib')
        scaler_path = os.path.join(settings.BASE_DIR, 'AIPredict', 'models', 'scaler.joblib')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)
    
    def start_session(self):
        self.current_session = SleepSession.objects.create(
            start_time=timezone.now(),
            quality=None
        )
        self.data_buffer = []
        print("\n=== New Sleep Session Started ===")
        print(f"Session ID: {self.current_session.id}")
        print(f"Start Time: {self.current_session.start_time}")
        print("Waiting for sensor data...")
    
    def end_session(self):
        if self.current_session:
            self.current_session.end_time = timezone.now()
            quality = self.analyze_sleep_quality()
            self.current_session.quality = quality
            self.current_session.save()
            print("\n=== Sleep Session Ended ===")
            print(f"Session ID: {self.current_session.id}")
            print(f"End Time: {self.current_session.end_time}")
            print(f"Quality: {quality}")
            print(f"Total Data Points: {len(self.data_buffer)}")
            self.current_session = None
            self.data_buffer = []
    
    def add_data_point(self, data):
        if self.current_session:
            # Extract features from data
            heart_rate = data.get('heartRate', 0)
            spo2 = data.get('spo2', 0)
            temperature = data.get('temperature', 0)
            acceleration = data.get('acceleration', 0)
            
            # Create SleepData object
            sleep_data = SleepData.objects.create(
                session=self.current_session,
                heart_rate=heart_rate,
                spo2=spo2,
                temperature=temperature,
                acceleration=acceleration,
                timestamp=timezone.now()
            )
            
            # Add to buffer for analysis
            self.data_buffer.append({
                'heart_rate': heart_rate,
                'spo2': spo2,
                'temperature': temperature,
                'acceleration': acceleration
            })
            
            # Print data point info every 10 points
            if len(self.data_buffer) % 10 == 0:
                print(f"\nData Point #{len(self.data_buffer)}")
                print(f"Heart Rate: {heart_rate:.1f} bpm")
                print(f"SpO2: {spo2:.1f}%")
                print(f"Temperature: {temperature:.1f}°C")
                print(f"Acceleration: {acceleration:.2f}g")
    
    def analyze_sleep_quality(self):
        if not self.data_buffer:
            return 'MEDIUM'  # Default quality if no data
        
        # Group data by hour
        hourly_data = {}
        for d in self.data_buffer:
            # Extract timestamp from data if available, otherwise use current time
            timestamp = d.get('timestamp', timezone.now())
            hour = timestamp.hour
            
            if hour not in hourly_data:
                hourly_data[hour] = {
                    'heart_rate': [],
                    'spo2': [],
                    'temperature': [],
                    'acceleration': []
                }
            
            hourly_data[hour]['heart_rate'].append(d['heart_rate'])
            hourly_data[hour]['spo2'].append(d['spo2'])
            hourly_data[hour]['temperature'].append(d['temperature'])
            hourly_data[hour]['acceleration'].append(d['acceleration'])
        
        # Calculate quality for each hour
        hourly_qualities = []
        
        for hour, data in hourly_data.items():
            if not data['heart_rate']:
                continue
            
            # Calculate averages for this hour
            avg_heart_rate = np.mean(data['heart_rate'])
            avg_spo2 = np.mean(data['spo2'])
            avg_temperature = np.mean(data['temperature'])
            avg_acceleration = np.mean(data['acceleration'])
            
            # Use AI model to predict quality
            if self.model and self.scaler:
                try:
                    # Prepare features for AI model
                    features = np.array([[
                        float(avg_heart_rate),  # hr_mean
                        0.0,  # hr_std (not available for single value)
                        float(avg_spo2),  # spo2_mean
                        0.0,  # spo2_std
                        float(avg_temperature),  # temp_mean
                        0.0,  # temp_std
                        float(avg_acceleration),  # acc_mean
                        0.0,  # acc_std
                        abs(float(avg_acceleration) - 1),  # acc_dev_mean
                        abs(float(avg_acceleration) - 1),  # acc_dev_max
                        0.0  # hr_iqr
                    ]])
                    
                    # Scale features
                    features_scaled = self.scaler.transform(features)
                    
                    # Predict quality
                    quality_score = float(self.model.predict(features_scaled)[0])
                    hourly_qualities.append(quality_score)
                except Exception as e:
                    print(f"Error using AI model: {e}")
                    # Fallback to heuristic if AI fails
                    criteria_met = 0
                    if 60 <= avg_heart_rate <= 80:
                        criteria_met += 1
                    if avg_spo2 >= 96:
                        criteria_met += 1
                    if 36.5 <= avg_temperature <= 37.0:
                        criteria_met += 1
                    if avg_acceleration <= 1.05:
                        criteria_met += 1
                    
                    if criteria_met >= 3:
                        hourly_qualities.append(3)
                    elif criteria_met >= 2:
                        hourly_qualities.append(2)
                    else:
                        hourly_qualities.append(1)
            else:
                # Use heuristic method if no AI model
                criteria_met = 0
                if 60 <= avg_heart_rate <= 80:
                    criteria_met += 1
                if avg_spo2 >= 96:
                    criteria_met += 1
                if 36.5 <= avg_temperature <= 37.0:
                    criteria_met += 1
                if avg_acceleration <= 1.05:
                    criteria_met += 1
                
                if criteria_met >= 3:
                    hourly_qualities.append(3)
                elif criteria_met >= 2:
                    hourly_qualities.append(2)
                else:
                    hourly_qualities.append(1)
        
        # Calculate overall quality as average of hourly qualities
        if hourly_qualities:
            overall_quality = np.mean(hourly_qualities)
            
            # Determine which value (1, 2, or 3) the score is closest to
            if abs(overall_quality - 3) <= abs(overall_quality - 2) and abs(overall_quality - 3) <= abs(overall_quality - 1):
                return 'GOOD'
            elif abs(overall_quality - 2) <= abs(overall_quality - 3) and abs(overall_quality - 2) <= abs(overall_quality - 1):
                return 'MEDIUM'
            else:
                return 'BAD'
        else:
            return 'MEDIUM'  # Default to medium if no data

class MQTTHandler:
    def __init__(self):
        # Use the MQTT client from dashboard instead of creating a new one
        self.client = mqtt_client
        self.analyzer = SleepAnalyzer()
        self.setup_client()
        print("\n=== MQTT Handler Initialized ===")
        print("Subscribed to topics: 'sleep', 'sensor/data'")
        print(f"Client ID: {self.client._client_id}")
        print(f"Connected: {self.client.is_connected()}")
    
    def setup_client(self):
        # No need to create a new client, just set up the callbacks
        if self.client:
            print("\n=== Setting up MQTT client ===")
            # Store original callbacks
            original_on_connect = self.client.on_connect
            original_on_message = self.client.on_message
            
            # Define new callbacks that call both original and our handlers
            def on_connect_wrapper(client, userdata, flags, rc):
                if original_on_connect:
                    original_on_connect(client, userdata, flags, rc)
                self.on_connect(client, userdata, flags, rc)
            
            def on_message_wrapper(client, userdata, msg):
                if original_on_message:
                    original_on_message(client, userdata, msg)
                self.on_message(client, userdata, msg)
            
            # Set new callbacks
            self.client.on_connect = on_connect_wrapper
            self.client.on_message = on_message_wrapper
            
            # Subscribe to our topics
            print("Subscribing to topics...")
            self.client.subscribe("sleep")
            self.client.subscribe("sensor/data")
            print("Topics subscribed")
        else:
            # If client is not available, start it
            print("\n=== MQTT client not available, starting new client ===")
            start_mqtt_client()
            self.client = mqtt_client
            self.setup_client()  # Retry setup
    
    def on_connect(self, client, userdata, flags, rc):
        print("\n=== MQTT Connected ===")
        print(f"Result code: {rc}")
        print(f"Flags: {flags}")
        print(f"Client ID: {client._client_id}")
        client.subscribe("sleep")
        client.subscribe("sensor/data")
        print("Topics subscribed after connection")
    
    def on_message(self, client, userdata, msg):
        print(f"\n=== Message Received ===")
        print(f"Topic: {msg.topic}")
        print(f"Payload: {msg.payload.decode()}")
        print(f"QoS: {msg.qos}")
        
        if msg.topic == "sleep":
            payload = msg.payload.decode()
            print(f"\n=== Sleep Message Received ===")
            print(f"Topic: {msg.topic}")
            print(f"Payload: {payload}")
            
            if payload == "1":
                print("Starting new sleep session...")
                self.analyzer.start_session()
            else:
                print("Ending current sleep session...")
                self.analyzer.end_session()
        elif msg.topic == "sensor/data":
            try:
                data = json.loads(msg.payload.decode())
                print("Processing sensor data...")
                self.analyzer.add_data_point(data)
            except json.JSONDecodeError:
                print("\n=== Error: Invalid JSON Data ===")
                print(f"Received payload: {msg.payload.decode()}")
    
    def stop(self):
        # Don't disconnect the client as it might be used by other parts of the application
        pass 