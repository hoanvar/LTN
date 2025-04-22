from django.db import models
from django.utils import timezone

# Create your models here.

class Settings(models.Model):
    # MQTT Settings
    mqtt_broker = models.CharField(max_length=255, default="0f6bce09467e483792a9cc8f3c79ab5f.s1.eu.hivemq.cloud")
    mqtt_port = models.IntegerField(default=8883)
    mqtt_topic = models.CharField(max_length=255, default="sensor/data")
    mqtt_username = models.CharField(max_length=255, default="hoan1234")
    mqtt_password = models.CharField(max_length=255, default="Hoan1234")

    # Threshold Settings
    heart_rate_min = models.FloatField(default=80)
    heart_rate_max = models.FloatField(default=105)
    spo2_min = models.FloatField(default=95)
    temperature_min = models.FloatField(default=30)
    temperature_max = models.FloatField(default=37)
    acceleration_min = models.FloatField(default=0.5)
    acceleration_max = models.FloatField(default=1.5)

    class Meta:
        verbose_name = 'Settings'
        verbose_name_plural = 'Settings'

    def __str__(self):
        return "System Settings"

class SensorData(models.Model):
    timestamp = models.DateTimeField()
    heartRate = models.FloatField()
    spo2 = models.FloatField()
    temperature = models.FloatField()
    acceleration = models.FloatField()
    is_abnormal = models.BooleanField(default=False)
    is_fall = models.BooleanField(default=False)

    def __str__(self):
        return f"Sensor Data at {self.timestamp}"

class SleepSession(models.Model):
    QUALITY_CHOICES = [
        ('GOOD', 'Good'),
        ('AVERAGE', 'Average'),
        ('BAD', 'Bad')
    ]

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    quality = models.CharField(max_length=20, choices=QUALITY_CHOICES)
    total_duration = models.DurationField()
    deep_sleep_duration = models.DurationField()
    light_sleep_duration = models.DurationField()
    wake_duration = models.DurationField()
    avg_acceleration = models.FloatField(help_text="Average acceleration during sleep")
    movement_count = models.IntegerField(help_text="Number of significant movements detected")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sleep Session {self.start_time.strftime('%Y-%m-%d %H:%M')} - {self.quality}"

    @property
    def deep_sleep_percentage(self):
        """Calculate percentage of deep sleep"""
        if self.total_duration.total_seconds() > 0:
            return (self.deep_sleep_duration.total_seconds() / self.total_duration.total_seconds()) * 100
        return 0

    @property
    def light_sleep_percentage(self):
        """Calculate percentage of light sleep"""
        if self.total_duration.total_seconds() > 0:
            return (self.light_sleep_duration.total_seconds() / self.total_duration.total_seconds()) * 100
        return 0

    @property
    def wake_percentage(self):
        """Calculate percentage of wake time"""
        if self.total_duration.total_seconds() > 0:
            return (self.wake_duration.total_seconds() / self.total_duration.total_seconds()) * 100
        return 0
