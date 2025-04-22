from django.db import models

# Create your models here.

class Settings(models.Model):
    # MQTT Settings
    mqtt_broker = models.CharField(max_length=255, default='broker.hivemq.com')
    mqtt_port = models.IntegerField(default=1883)
    mqtt_topic = models.CharField(max_length=255, default='sensor/data')
    mqtt_username = models.CharField(max_length=255, blank=True)
    mqtt_password = models.CharField(max_length=255, blank=True)

    # Threshold Settings
    heart_rate_min = models.FloatField(default=60.0)
    heart_rate_max = models.FloatField(default=100.0)
    spo2_min = models.FloatField(default=95.0)
    temperature_min = models.FloatField(default=30.0)
    temperature_max = models.FloatField(default=37.0)
    acceleration_min = models.FloatField(default=0.5)
    acceleration_max = models.FloatField(default=2.0)
    email_list = models.TextField(default='', blank=True, help_text='Comma-separated list of email addresses')

    def get_email_list(self):
        if not self.email_list:
            return []
        return [email.strip() for email in self.email_list.split(',') if email.strip()]

    def set_email_list(self, emails):
        self.email_list = ','.join(emails)
        self.save()

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
    is_fall = models.BooleanField(default=False)
    is_abnormal = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
