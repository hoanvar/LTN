from django.db import models
from django.utils import timezone
import pytz

def get_current_time():
    tz = pytz.timezone('Asia/Bangkok')
    return timezone.now().astimezone(tz)

class SleepSession(models.Model):
    start_time = models.DateTimeField(default=get_current_time)
    end_time = models.DateTimeField(null=True, blank=True)
    quality = models.CharField(max_length=20, choices=[
        ('GOOD', 'Tốt'),
        ('MEDIUM', 'Trung Bình'),
        ('BAD', 'Không tốt')
    ], null=True, blank=True)
    
    def __str__(self):
        return f"Sleep Session {self.id} - {self.start_time}"

class SleepData(models.Model):
    session = models.ForeignKey(SleepSession, on_delete=models.CASCADE, related_name='data_points')
    timestamp = models.DateTimeField(default=get_current_time)
    heart_rate = models.FloatField()
    spo2 = models.FloatField()
    temperature = models.FloatField()
    acceleration = models.FloatField()
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Data Point {self.id} - HR: {self.heart_rate}, SpO2: {self.spo2}"
