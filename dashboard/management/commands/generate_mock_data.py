from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import SensorData
from datetime import timedelta, datetime
import random

class Command(BaseCommand):
    help = 'Generates mock sensor data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=60,  # Changed default to 60 days (2 months)
            help='Number of days of data to generate'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=20,  # Changed interval to 20 minutes
            help='Interval between readings in minutes'
        )

    def handle(self, *args, **options):
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        SensorData.objects.all().delete()

        days = options['days']
        interval = options['interval']
        
        # Generate data
        self.stdout.write(f'Generating {days} days of mock data with {interval} minute intervals...')
        
        # Start from current time and go back
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)
        current_time = start_time

        # Base values for each metric
        base_heart_rate = 75
        base_spo2 = 98
        base_temp = 36.5
        base_acceleration = 1.0

        # Calculate total number of points for progress tracking
        total_points = int((days * 24 * 60) / interval)  # points per day * number of days
        points_generated = 0

        # Generate data points
        while current_time <= end_time:
            # Add some random variation to base values
            heart_rate = base_heart_rate + random.uniform(-10, 10)
            spo2 = base_spo2 + random.uniform(-3, 1)
            temperature = base_temp + random.uniform(-0.5, 0.5)
            acceleration = base_acceleration + random.uniform(-0.3, 0.3)

            # Add occasional anomalies (10% chance)
            if random.random() < 0.1:
                anomaly_type = random.choice(['heart', 'spo2', 'temp', 'fall'])
                if anomaly_type == 'heart':
                    heart_rate = random.choice([55, 110])  # Abnormal heart rate
                elif anomaly_type == 'spo2':
                    spo2 = random.uniform(90, 94)  # Low SpO2
                elif anomaly_type == 'temp':
                    temperature = random.choice([35.5, 38.0])  # Abnormal temperature
                else:
                    acceleration = random.uniform(1.6, 2.0)  # Fall detection

            # Create the data point with explicit timestamp
            SensorData.objects.create(
                timestamp=current_time,
                heartRate=heart_rate,
                spo2=spo2,
                temperature=temperature,
                acceleration=acceleration,
                is_fall=acceleration > 1.5,
                is_abnormal=(
                    heart_rate < 60 or heart_rate > 100 or
                    spo2 < 95 or
                    temperature < 36 or temperature > 37.5
                )
            )

            # Update progress
            points_generated += 1
            if points_generated % 100 == 0:  # Show progress every 100 points
                progress = (points_generated / total_points) * 100
                self.stdout.write(f'Progress: {progress:.1f}% ({points_generated}/{total_points} points)')
                self.stdout.write(f'Current time: {current_time}')

            # Move to next interval
            current_time += timedelta(minutes=interval)

        total_points = SensorData.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Successfully generated {total_points} data points over {days} days'
        ))
        
        # Print time range of generated data
        first_record = SensorData.objects.order_by('timestamp').first()
        last_record = SensorData.objects.order_by('timestamp').last()
        if first_record and last_record:
            self.stdout.write(f"Data range: from {first_record.timestamp} to {last_record.timestamp}") 