from django.core.mail import send_mail
from django.conf import settings
from .models import Settings
import logging
from django.utils import timezone
import pytz

logger = logging.getLogger(__name__)

def send_fall_alert(sensor_data):
    """
    Gửi email thông báo khi phát hiện ngã
    """
    try:
        logger.info("Preparing to send fall alert email...")
        
        # Lấy danh sách email từ settings
        settings_obj = Settings.objects.first()
        if not settings_obj or not settings_obj.email_list:
            logger.warning("No email recipients configured in settings")
            return False

        # Chuyển đổi timestamp sang GMT+7
        bangkok_tz = pytz.timezone('Asia/Bangkok')
        local_time = sensor_data.timestamp.astimezone(bangkok_tz)
        formatted_time = local_time.strftime('%Y-%m-%d %H:%M:%S %Z')

        # Chuẩn bị nội dung email
        subject = '⚠️ Fall Detection Alert!'
        message = f"""
        A fall has been detected!

        Time: {formatted_time}

        Vital Signs at time of fall:
        - Heart Rate: {sensor_data.heartRate} BPM
        - SpO2: {sensor_data.spo2}%
        - Temperature: {sensor_data.temperature}°C
        - Acceleration: {sensor_data.acceleration} g

        Please check on the person immediately!
        """

        # Gửi email đến tất cả địa chỉ trong danh sách
        recipient_list = settings_obj.get_email_list()
        if not recipient_list:
            logger.warning("No email recipients in list")
            return False

        logger.info(f"Attempting to send fall alert email to recipients: {recipient_list}")
        logger.info(f"Email subject: {subject}")
        logger.info(f"Email message: {message}")

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"Fall alert email sent successfully to {recipient_list}")
        return True

    except Exception as e:
        logger.error(f"Error sending fall alert email: {str(e)}", exc_info=True)
        return False 