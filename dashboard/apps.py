from django.apps import AppConfig
import sys
import os

# Biến toàn cục để theo dõi trạng thái khởi động của MQTT
mqtt_started = False

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        global mqtt_started
        
        # Chỉ khởi động MQTT client một lần, trong main process, và không trong migration
        if (not mqtt_started and 
            'makemigrations' not in sys.argv and 
            'migrate' not in sys.argv and
            'runserver' in sys.argv and
            os.environ.get('RUN_MAIN') == 'true'):  # Chỉ chạy trong main process của Django
            
            print("Initializing MQTT client (once only)")
            from . import mqtt_client
            mqtt_client.start_mqtt_client()
            mqtt_started = True
