from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import SensorData, Settings
from django.db.models import Avg, Count
import logging
from django.db import connection
import math
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .mqtt_client import restart_mqtt_client, publish_settings

logger = logging.getLogger(__name__)

# Create your views here.

def index(request):
    # Get latest sensor data
    latest_data = SensorData.objects.first()
    
    # Get recent data for table
    recent_data = SensorData.objects.all()[:10]
    
    # Get current settings for thresholds
    settings, _ = Settings.objects.get_or_create(pk=1)
    
    context = {
        'latest_data': latest_data,
        'recent_data': recent_data,
        'settings': settings,  # Thêm settings vào context
    }
    
    return render(request, 'dashboard/index.html', context)

def sensors_view(request):
    # Get page number from request, default to 1
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1
    
    # Limit to first 20 pages (400 records)
    if page > 20:
        page = 20
    
    # Get all sensor data with pagination
    sensor_data = SensorData.objects.all()[(page-1)*20:page*20]
    
    # Calculate total pages (capped at 20)
    total_records = SensorData.objects.count()
    total_pages = min(20, (total_records + 19) // 20)  # Ceiling division, max 20 pages
    
    context = {
        'sensor_data': sensor_data,
        'current_page': page,
        'total_pages': total_pages,
    }
    
    return render(request, 'dashboard/sensors.html', context)

def analysis_view(request):
    return render(request, 'dashboard/analysis.html')

def analysis_data(request):
    # Get time range from request
    time_range = request.GET.get('time_range', '24h')
    
    # Calculate the start time based on the selected range
    now = timezone.now()
    
    # Debug: Print total records in database
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM dashboard_sensordata")
        total_records = cursor.fetchone()[0]
        logger.info(f"Total records in database: {total_records}")
        
        # Get sample data to check timestamp format
        cursor.execute("SELECT timestamp FROM dashboard_sensordata LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            logger.info(f"Sample timestamp format: {sample[0]}")
    
    # Define maximum number of data points to display
    MAX_DATA_POINTS = 100
    
    if time_range == '1h':
        # Get raw data for 1h view
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    datetime(timestamp, 'localtime') as time,
                    "heartRate",
                    spo2,
                    temperature,
                    acceleration
                FROM dashboard_sensordata
                WHERE timestamp >= datetime('now', '-1 hour')
                ORDER BY time
            """)
            
            rows = cursor.fetchall()
            logger.info(f"1h view - Found {len(rows)} records")
            
            # Calculate sampling interval to reduce data points
            if len(rows) > MAX_DATA_POINTS:
                # Calculate how many records to skip
                skip_factor = math.ceil(len(rows) / MAX_DATA_POINTS)
                logger.info(f"1h view - Sampling every {skip_factor} records to reduce from {len(rows)} to ~{MAX_DATA_POINTS} points")
                
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for i, row in enumerate(rows):
                    if i % skip_factor == 0:  # Only include every nth record
                        try:
                            time_str, hr, spo2, temp, acc = row
                            # Convert time string to datetime for proper formatting
                            time = timezone.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                            timestamps.append(time.strftime('%H:%M'))
                            heart_rate_data.append(float(hr))
                            spo2_data.append(float(spo2))
                            temperature_data.append(float(temp))
                            acceleration_data.append(float(acc))
                        except Exception as e:
                            logger.error(f"Error processing row: {e}, Row data: {row}")
                            continue
            else:
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for row in rows:
                    try:
                        time_str, hr, spo2, temp, acc = row
                        # Convert time string to datetime for proper formatting
                        time = timezone.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        timestamps.append(time.strftime('%H:%M'))
                        heart_rate_data.append(float(hr))
                        spo2_data.append(float(spo2))
                        temperature_data.append(float(temp))
                        acceleration_data.append(float(acc))
                    except Exception as e:
                        logger.error(f"Error processing row: {e}, Row data: {row}")
                        continue
    elif time_range == '6h':
        # Get raw data for 6h view
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    datetime(timestamp, 'localtime') as time,
                    "heartRate",
                    spo2,
                    temperature,
                    acceleration
                FROM dashboard_sensordata
                WHERE timestamp >= datetime('now', '-6 hours')
                ORDER BY time
            """)
            
            rows = cursor.fetchall()
            logger.info(f"6h view - Found {len(rows)} records")
            
            # Calculate sampling interval to reduce data points
            if len(rows) > MAX_DATA_POINTS:
                # Calculate how many records to skip
                skip_factor = math.ceil(len(rows) / MAX_DATA_POINTS)
                logger.info(f"6h view - Sampling every {skip_factor} records to reduce from {len(rows)} to ~{MAX_DATA_POINTS} points")
                
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for i, row in enumerate(rows):
                    if i % skip_factor == 0:  # Only include every nth record
                        try:
                            time_str, hr, spo2, temp, acc = row
                            # Convert time string to datetime for proper formatting
                            time = timezone.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                            timestamps.append(time.strftime('%H:%M'))
                            heart_rate_data.append(float(hr))
                            spo2_data.append(float(spo2))
                            temperature_data.append(float(temp))
                            acceleration_data.append(float(acc))
                        except Exception as e:
                            logger.error(f"Error processing row: {e}, Row data: {row}")
                            continue
            else:
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for row in rows:
                    try:
                        time_str, hr, spo2, temp, acc = row
                        # Convert time string to datetime for proper formatting
                        time = timezone.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        timestamps.append(time.strftime('%H:%M'))
                        heart_rate_data.append(float(hr))
                        spo2_data.append(float(spo2))
                        temperature_data.append(float(temp))
                        acceleration_data.append(float(acc))
                    except Exception as e:
                        logger.error(f"Error processing row: {e}, Row data: {row}")
                        continue
    elif time_range == '12h':
        # Get raw data for 12h view
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    datetime(timestamp, 'localtime') as time,
                    "heartRate",
                    spo2,
                    temperature,
                    acceleration
                FROM dashboard_sensordata
                WHERE timestamp >= datetime('now', '-12 hours')
                ORDER BY time
            """)
            
            rows = cursor.fetchall()
            logger.info(f"12h view - Found {len(rows)} records")
            
            # Calculate sampling interval to reduce data points
            if len(rows) > MAX_DATA_POINTS:
                # Calculate how many records to skip
                skip_factor = math.ceil(len(rows) / MAX_DATA_POINTS)
                logger.info(f"12h view - Sampling every {skip_factor} records to reduce from {len(rows)} to ~{MAX_DATA_POINTS} points")
                
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for i, row in enumerate(rows):
                    if i % skip_factor == 0:  # Only include every nth record
                        try:
                            time_str, hr, spo2, temp, acc = row
                            # Convert time string to datetime for proper formatting
                            time = timezone.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                            timestamps.append(time.strftime('%H:%M'))
                            heart_rate_data.append(float(hr))
                            spo2_data.append(float(spo2))
                            temperature_data.append(float(temp))
                            acceleration_data.append(float(acc))
                        except Exception as e:
                            logger.error(f"Error processing row: {e}, Row data: {row}")
                            continue
            else:
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for row in rows:
                    try:
                        time_str, hr, spo2, temp, acc = row
                        # Convert time string to datetime for proper formatting
                        time = timezone.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        timestamps.append(time.strftime('%H:%M'))
                        heart_rate_data.append(float(hr))
                        spo2_data.append(float(spo2))
                        temperature_data.append(float(temp))
                        acceleration_data.append(float(acc))
                    except Exception as e:
                        logger.error(f"Error processing row: {e}, Row data: {row}")
                        continue
    elif time_range == '24h':
        start_time = now - timedelta(hours=24)
        # Get raw data for 24h view
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    datetime(timestamp, 'localtime') as time,
                    "heartRate",
                    spo2,
                    temperature,
                    acceleration
                FROM dashboard_sensordata
                WHERE timestamp >= datetime('now', '-1 day')
                ORDER BY time
            """)
            
            rows = cursor.fetchall()
            logger.info(f"24h view - Found {len(rows)} records")
            
            # Calculate sampling interval to reduce data points
            if len(rows) > MAX_DATA_POINTS:
                # Calculate how many records to skip
                skip_factor = math.ceil(len(rows) / MAX_DATA_POINTS)
                logger.info(f"24h view - Sampling every {skip_factor} records to reduce from {len(rows)} to ~{MAX_DATA_POINTS} points")
                
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for i, row in enumerate(rows):
                    if i % skip_factor == 0:  # Only include every nth record
                        try:
                            time_str, hr, spo2, temp, acc = row
                            # Convert time string to datetime for proper formatting
                            time = timezone.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                            timestamps.append(time.strftime('%H:%M'))
                            heart_rate_data.append(float(hr))
                            spo2_data.append(float(spo2))
                            temperature_data.append(float(temp))
                            acceleration_data.append(float(acc))
                        except Exception as e:
                            logger.error(f"Error processing row: {e}, Row data: {row}")
                            continue
            else:
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for row in rows:
                    try:
                        time_str, hr, spo2, temp, acc = row
                        # Convert time string to datetime for proper formatting
                        time = timezone.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        timestamps.append(time.strftime('%H:%M'))
                        heart_rate_data.append(float(hr))
                        spo2_data.append(float(spo2))
                        temperature_data.append(float(temp))
                        acceleration_data.append(float(acc))
                    except Exception as e:
                        logger.error(f"Error processing row: {e}, Row data: {row}")
                        continue
                
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
        
        # Use SQLite datetime functions for 7d view (group by hour)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    datetime(timestamp, 'localtime') as hour,
                    AVG(CAST("heartRate" as FLOAT)) as avg_heart_rate,
                    AVG(CAST(spo2 as FLOAT)) as avg_spo2,
                    AVG(CAST(temperature as FLOAT)) as avg_temp,
                    AVG(CAST(acceleration as FLOAT)) as avg_acc
                FROM dashboard_sensordata
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY substr(datetime(timestamp, 'localtime'), 1, 13)
                ORDER BY hour
            """)
            
            rows = cursor.fetchall()
            logger.info(f"7d view - Found {len(rows)} aggregated records")
            
            # Calculate sampling interval to reduce data points
            if len(rows) > MAX_DATA_POINTS:
                # Calculate how many records to skip
                skip_factor = math.ceil(len(rows) / MAX_DATA_POINTS)
                logger.info(f"7d view - Sampling every {skip_factor} records to reduce from {len(rows)} to ~{MAX_DATA_POINTS} points")
                
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for i, row in enumerate(rows):
                    if i % skip_factor == 0:  # Only include every nth record
                        try:
                            hour_str, hr, spo2, temp, acc = row
                            # Convert hour string to datetime for proper formatting
                            hour = timezone.datetime.strptime(hour_str, '%Y-%m-%d %H:%M:%S')
                            timestamps.append(hour.strftime('%d/%m %H:00'))
                            heart_rate_data.append(round(float(hr), 1))
                            spo2_data.append(round(float(spo2), 1))
                            temperature_data.append(round(float(temp), 2))
                            acceleration_data.append(round(float(acc), 3))
                        except Exception as e:
                            logger.error(f"Error processing row: {e}, Row data: {row}")
                            continue
            else:
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for row in rows:
                    try:
                        hour_str, hr, spo2, temp, acc = row
                        # Convert hour string to datetime for proper formatting
                        hour = timezone.datetime.strptime(hour_str, '%Y-%m-%d %H:%M:%S')
                        timestamps.append(hour.strftime('%d/%m %H:00'))
                        heart_rate_data.append(round(float(hr), 1))
                        spo2_data.append(round(float(spo2), 1))
                        temperature_data.append(round(float(temp), 2))
                        acceleration_data.append(round(float(acc), 3))
                    except Exception as e:
                        logger.error(f"Error processing row: {e}, Row data: {row}")
                        continue
                
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
        
        # Use SQLite datetime functions for 30d view (group by day)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    date(timestamp, 'localtime') as day,
                    AVG(CAST("heartRate" as FLOAT)) as avg_heart_rate,
                    AVG(CAST(spo2 as FLOAT)) as avg_spo2,
                    AVG(CAST(temperature as FLOAT)) as avg_temp,
                    AVG(CAST(acceleration as FLOAT)) as avg_acc
                FROM dashboard_sensordata
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY date(timestamp, 'localtime')
                ORDER BY day
            """)
            
            rows = cursor.fetchall()
            logger.info(f"30d view - Found {len(rows)} aggregated records")
            
            # Calculate sampling interval to reduce data points
            if len(rows) > MAX_DATA_POINTS:
                # Calculate how many records to skip
                skip_factor = math.ceil(len(rows) / MAX_DATA_POINTS)
                logger.info(f"30d view - Sampling every {skip_factor} records to reduce from {len(rows)} to ~{MAX_DATA_POINTS} points")
                
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for i, row in enumerate(rows):
                    if i % skip_factor == 0:  # Only include every nth record
                        try:
                            day_str, hr, spo2, temp, acc = row
                            # Convert day string to datetime for proper formatting
                            day = timezone.datetime.strptime(day_str, '%Y-%m-%d')
                            timestamps.append(day.strftime('%d/%m'))
                            heart_rate_data.append(round(float(hr), 1))
                            spo2_data.append(round(float(spo2), 1))
                            temperature_data.append(round(float(temp), 2))
                            acceleration_data.append(round(float(acc), 3))
                        except Exception as e:
                            logger.error(f"Error processing row: {e}, Row data: {row}")
                            continue
            else:
                timestamps = []
                heart_rate_data = []
                spo2_data = []
                temperature_data = []
                acceleration_data = []
                
                for row in rows:
                    try:
                        day_str, hr, spo2, temp, acc = row
                        # Convert day string to datetime for proper formatting
                        day = timezone.datetime.strptime(day_str, '%Y-%m-%d')
                        timestamps.append(day.strftime('%d/%m'))
                        heart_rate_data.append(round(float(hr), 1))
                        spo2_data.append(round(float(spo2), 1))
                        temperature_data.append(round(float(temp), 2))
                        acceleration_data.append(round(float(acc), 3))
                    except Exception as e:
                        logger.error(f"Error processing row: {e}, Row data: {row}")
                        continue
    
    else:
        # Default to 24h view
        start_time = now - timedelta(hours=24)
        sensor_data = SensorData.objects.filter(
            timestamp__gte=start_time
        ).order_by('timestamp')
        
        # Calculate sampling interval to reduce data points
        count = sensor_data.count()
        if count > MAX_DATA_POINTS:
            # Calculate how many records to skip
            skip_factor = math.ceil(count / MAX_DATA_POINTS)
            logger.info(f"Default view - Sampling every {skip_factor} records to reduce from {count} to ~{MAX_DATA_POINTS} points")
            
            timestamps = []
            heart_rate_data = []
            spo2_data = []
            temperature_data = []
            acceleration_data = []

            for i, data in enumerate(sensor_data):
                if i % skip_factor == 0:  # Only include every nth record
                    try:
                        timestamps.append(data.timestamp.strftime('%H:%M'))
                        heart_rate_data.append(float(data.heartRate))
                        spo2_data.append(float(data.spo2))
                        temperature_data.append(float(data.temperature))
                        acceleration_data.append(float(data.acceleration))
                    except Exception as e:
                        logger.error(f"Error processing data point: {e}")
                        continue
        else:
            timestamps = []
            heart_rate_data = []
            spo2_data = []
            temperature_data = []
            acceleration_data = []

            for data in sensor_data:
                try:
                    timestamps.append(data.timestamp.strftime('%H:%M'))
                    heart_rate_data.append(float(data.heartRate))
                    spo2_data.append(float(data.spo2))
                    temperature_data.append(float(data.temperature))
                    acceleration_data.append(float(data.acceleration))
                except Exception as e:
                    logger.error(f"Error processing data point: {e}")
                    continue

    # Debug log
    logger.info(f"Time range: {time_range}, Returning {len(timestamps)} data points")
    if len(timestamps) > 0:
        logger.info(f"First timestamp: {timestamps[0]}, Last timestamp: {timestamps[-1]}")

    return JsonResponse({
        'timestamps': timestamps,
        'heart_rate': heart_rate_data,
        'spo2': spo2_data,
        'temperature': temperature_data,
        'acceleration': acceleration_data
    })

def settings_view(request):
    # Get or create settings
    settings, created = Settings.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        # Update MQTT settings
        settings.mqtt_broker = request.POST.get('mqtt_broker')
        settings.mqtt_port = int(request.POST.get('mqtt_port'))
        settings.mqtt_topic = request.POST.get('mqtt_topic')
        settings.mqtt_username = request.POST.get('mqtt_username')
        settings.mqtt_password = request.POST.get('mqtt_password')
        
        # Update threshold settings
        settings.heart_rate_min = float(request.POST.get('heart_rate_min'))
        settings.heart_rate_max = float(request.POST.get('heart_rate_max'))
        settings.spo2_min = float(request.POST.get('spo2_min'))
        settings.temperature_min = float(request.POST.get('temperature_min'))
        settings.temperature_max = float(request.POST.get('temperature_max'))
        settings.acceleration_min = float(request.POST.get('acceleration_min'))
        settings.acceleration_max = float(request.POST.get('acceleration_max'))
        
        # Update email list
        email_list = request.POST.get('email_list', '')
        settings.email_list = email_list
        
        settings.save()
        
        # Publish new settings to the device via MQTT
        publish_success = publish_settings()
        
        response_data = {
            'status': 'success',
            'settings_published': publish_success
        }
        
        if not publish_success:
            response_data['warning'] = 'Settings saved but could not publish to device. You may need to restart the MQTT client.'
        
        return JsonResponse(response_data)
    
    return render(request, 'dashboard/settings.html', {'settings': settings})

@require_http_methods(["POST"])
@csrf_exempt
def restart_mqtt(request):
    try:
        success = restart_mqtt_client()
        
        # Send settings to device after restart
        if success:
            publish_success = publish_settings()
            return JsonResponse({
                'status': 'success', 
                'settings_published': publish_success
            })
        else:
            return JsonResponse({
                'status': 'error', 
                'message': 'Failed to restart MQTT client'
            })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def time_analysis_view(request):
    """View for time analysis page"""
    
    # Get all data with abnormal status and fall status
    abnormal_events = SensorData.objects.filter(is_abnormal=True)
    fall_events = SensorData.objects.filter(is_fall=True)
    
    # Prepare data for hourly charts
    hours_labels = [f"{i}:00" for i in range(24)]
    
    # Count abnormal events by hour
    hourly_abnormal_counts = [0] * 24
    for event in abnormal_events:
        hour = event.timestamp.hour
        hourly_abnormal_counts[hour] += 1
    
    # Count fall events by hour
    hourly_fall_counts = [0] * 24
    for event in fall_events:
        hour = event.timestamp.hour
        hourly_fall_counts[hour] += 1
    
    # Get peak hour for abnormal events
    if abnormal_events.exists():
        peak_hour = hourly_abnormal_counts.index(max(hourly_abnormal_counts))
    else:
        peak_hour = 0
    
    # Prepare data for weekday charts
    weekday_abnormal_counts = [0] * 7
    weekday_fall_counts = [0] * 7
    
    for event in abnormal_events:
        weekday = event.timestamp.weekday()  # 0 is Monday, 6 is Sunday
        weekday_abnormal_counts[weekday] += 1
    
    for event in fall_events:
        weekday = event.timestamp.weekday()
        weekday_fall_counts[weekday] += 1
    
    # Calculate statistics
    total_abnormal = abnormal_events.count()
    total_falls = fall_events.count()
    
    # Calculate average per day (using the date range from first to last event)
    if abnormal_events.exists() and fall_events.exists():
        # Combine both querysets to find overall date range
        all_events = list(abnormal_events) + list(fall_events)
        earliest_date = min(event.timestamp.date() for event in all_events)
        latest_date = max(event.timestamp.date() for event in all_events)
        date_range = (latest_date - earliest_date).days + 1  # +1 to include both start and end date
        if date_range > 0:
            avg_per_day = (total_abnormal + total_falls) / date_range
        else:
            avg_per_day = total_abnormal + total_falls  # All events occurred on same day
    else:
        avg_per_day = 0
    
    context = {
        'total_abnormal': total_abnormal,
        'total_falls': total_falls,
        'avg_per_day': avg_per_day,
        'peak_hour': peak_hour,
        'hours_labels': json.dumps(hours_labels),
        'hourly_abnormal_data': json.dumps(hourly_abnormal_counts),
        'hourly_fall_data': json.dumps(hourly_fall_counts),
        'weekday_abnormal_data': json.dumps(weekday_abnormal_counts),
        'weekday_fall_data': json.dumps(weekday_fall_counts),
    }
    
    return render(request, 'dashboard/time_analysis.html', context)
