from django.urls import path
from . import views

app_name = 'aipredict'

urlpatterns = [
    path('', views.index, name='index'),
    path('data/', views.get_sleep_data, name='get_sleep_data'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('check-mqtt/', views.check_mqtt_status_view, name='check_mqtt_status'),
] 