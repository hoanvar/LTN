from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import SleepSession, SleepData
# Import MQTT client from dashboard
from dashboard.mqtt_client import mqtt_client, start_mqtt_client, publish_settings
from django.conf import settings
import json
import numpy as np
from collections import Counter

# Khởi tạo MQTT handler
mqtt_handler = None

def start_mqtt_handler():
    global mqtt_handler
    if mqtt_handler is None:
        # Use the MQTT client from dashboard instead of creating a new one
        print("\n=== Starting MQTT Handler ===")
        start_mqtt_client()
        mqtt_handler = mqtt_client
        print("MQTT client started")
        
        # Import and initialize the MQTT handler from services
        from .services import MQTTHandler
        mqtt_handler = MQTTHandler()
        print("MQTT Handler initialized")
    else:
        print("\n=== MQTT Handler already running ===")

def check_mqtt_status():
    """Kiểm tra trạng thái MQTT và khởi động lại nếu cần"""
    global mqtt_handler
    
    print("\n=== Checking MQTT Status ===")
    
    # Kiểm tra xem MQTT client có đang chạy không
    from dashboard.mqtt_client import mqtt_client, mqtt_thread
    
    if mqtt_client is None or mqtt_thread is None or not mqtt_thread.is_alive():
        print("MQTT client not running, restarting...")
        from dashboard.mqtt_client import start_mqtt_client
        start_mqtt_client()
    
    # Kiểm tra xem MQTT handler có đang chạy không
    if mqtt_handler is None:
        print("MQTT handler not initialized, initializing...")
        start_mqtt_handler()
    
    print("MQTT status check completed")
    return True

def index(request):
    # Kiểm tra trạng thái MQTT trước khi hiển thị trang
    check_mqtt_status()
    
    # Lấy tất cả phiên ngủ và sắp xếp theo thời gian bắt đầu mới nhất
    session_list = SleepSession.objects.all().order_by('-start_time')
    
    # Phân trang, mỗi trang 10 phiên ngủ
    paginator = Paginator(session_list, 10)
    page = request.GET.get('page')
    
    try:
        sessions = paginator.page(page)
    except PageNotAnInteger:
        # Nếu page không phải là số, trả về trang đầu tiên
        sessions = paginator.page(1)
    except EmptyPage:
        # Nếu page vượt quá số trang, trả về trang cuối
        sessions = paginator.page(paginator.num_pages)
    
    return render(request, 'aipredict/index.html', {
        'sessions': sessions,
        'page_obj': sessions,
        'is_paginated': paginator.num_pages > 1,
        'paginator': paginator
    })

def get_sleep_data(request):
    sessions = SleepSession.objects.all().order_by('-start_time')
    data = []
    for session in sessions:
        data.append({
            'id': session.id,
            'start_time': session.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': session.end_time.strftime('%Y-%m-%d %H:%M:%S') if session.end_time else None,
            'quality': session.quality,
            'duration': (session.end_time - session.start_time).total_seconds() / 3600 if session.end_time else None
        })
    return JsonResponse({'sessions': data})

def calculate_sleep_quality(heart_rate, spo2, temperature, acceleration, model=None, scaler=None):
    """
    Calculate sleep quality based on sensor data using AI model
    Returns a score: 3 for good, 2 for medium, 1 for bad
    """
    if model is None or scaler is None:
        raise ValueError("AI model and scaler are required for sleep quality assessment")
    
    # Prepare features for AI model
    features = np.array([[
        float(heart_rate),  # hr_mean
        0.0,  # hr_std (not available for single value)
        float(spo2),  # spo2_mean
        0.0,  # spo2_std
        float(temperature),  # temp_mean
        0.0,  # temp_std
        float(acceleration),  # acc_mean
        0.0,  # acc_std
        abs(float(acceleration) - 1),  # acc_dev_mean
        abs(float(acceleration) - 1),  # acc_dev_max
        0.0  # hr_iqr
    ]])
    
    # Scale features
    features_scaled = scaler.transform(features)
    
    # Predict quality
    return float(model.predict(features_scaled)[0])

def session_detail(request, session_id):
    """View to display detailed information about a sleep session"""
    session = get_object_or_404(SleepSession, id=session_id)
    
    # Get all sleep data points for this session
    sleep_data = SleepData.objects.filter(session=session).order_by('timestamp')
    
    # Calculate hourly averages
    hourly_data = {}
    for data in sleep_data:
        hour = data.timestamp.hour
        if hour not in hourly_data:
            hourly_data[hour] = {
                'heart_rate': [],
                'spo2': [],
                'temperature': [],
                'acceleration': []
            }
        
        hourly_data[hour]['heart_rate'].append(data.heart_rate)
        hourly_data[hour]['spo2'].append(data.spo2)
        hourly_data[hour]['temperature'].append(data.temperature)
        hourly_data[hour]['acceleration'].append(data.acceleration)
    
    # Calculate averages and quality for each hour
    hourly_averages = []
    hourly_quality = []
    
    # Load AI model
    try:
        import joblib
        import os
        from django.conf import settings
        
        model_path = os.path.join(settings.BASE_DIR, 'AIPredict', 'models', 'sleep_model.joblib')
        scaler_path = os.path.join(settings.BASE_DIR, 'AIPredict', 'models', 'scaler.joblib')
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            raise FileNotFoundError("AI model files not found")
            
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
    except Exception as e:
        print(f"Error loading AI model: {e}")
        return render(request, 'aipredict/error.html', {'error': 'Could not load AI model'})
    
    for hour, data in hourly_data.items():
        # Calculate averages
        avg_heart_rate = sum(data['heart_rate']) / len(data['heart_rate']) if data['heart_rate'] else 0
        avg_spo2 = sum(data['spo2']) / len(data['spo2']) if data['spo2'] else 0
        avg_temperature = sum(data['temperature']) / len(data['temperature']) if data['temperature'] else 0
        avg_acceleration = sum(data['acceleration']) / len(data['acceleration']) if data['acceleration'] else 0
        
        # Calculate quality score using AI model
        quality_score = calculate_sleep_quality(
            avg_heart_rate, 
            avg_spo2, 
            avg_temperature, 
            avg_acceleration,
            model,
            scaler
        )
        
        hourly_averages.append({
            'hour': hour,
            'heart_rate': float(avg_heart_rate),
            'spo2': float(avg_spo2),
            'temperature': float(avg_temperature),
            'acceleration': float(avg_acceleration),
            'quality_score': float(quality_score)
        })
        
        hourly_quality.append(float(quality_score))
    
    # Sort by hour
    hourly_averages.sort(key=lambda x: x['hour'])
    
    # Get the most common quality score as overall quality
    quality_counter = Counter(hourly_quality)
    overall_quality = quality_counter.most_common(1)[0][0] if hourly_quality else 0.0
    
    # Convert quality score to quality level
    def score_to_quality(score):
        if score == 3:
            return 'GOOD'
        elif score == 2:
            return 'MEDIUM'
        else:
            return 'BAD'
    
    # Update session quality if it's not set
    if not session.quality and hourly_quality:
        session.quality = score_to_quality(overall_quality)
        session.save()
    
    # Prepare data for charts
    chart_data = {
        'hours': [data['hour'] for data in hourly_averages],
        'heart_rate': [data['heart_rate'] for data in hourly_averages],
        'spo2': [data['spo2'] for data in hourly_averages],
        'temperature': [data['temperature'] for data in hourly_averages],
        'acceleration': [data['acceleration'] for data in hourly_averages],
        'quality_scores': [data['quality_score'] for data in hourly_averages],
        'overall_quality': overall_quality
    }
    
    context = {
        'session': session,
        'sleep_data': sleep_data,
        'hourly_averages': hourly_averages,
        'chart_data': json.dumps(chart_data),
        'overall_quality': overall_quality
    }
    
    return render(request, 'aipredict/session_detail.html', context)

def check_mqtt_status_view(request):
    """API endpoint để kiểm tra trạng thái MQTT"""
    try:
        check_mqtt_status()
        return JsonResponse({
            'status': 'success',
            'message': 'MQTT status checked and updated if needed'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })
