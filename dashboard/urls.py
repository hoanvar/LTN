from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('sensors/', views.sensors_view, name='sensors'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('api/analysis-data/', views.analysis_data, name='analysis_data'),
    path('time-analysis/', views.time_analysis_view, name='time_analysis'),
    path('settings/', views.settings_view, name='settings'),
    path('api/restart-mqtt/', views.restart_mqtt, name='restart_mqtt'),
    path('sleep-analysis/', views.sleep_analysis, name='sleep_analysis'),
] 