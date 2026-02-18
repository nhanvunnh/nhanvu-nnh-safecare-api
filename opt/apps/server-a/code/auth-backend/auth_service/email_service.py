from django.conf import settings
from django.core.mail import send_mail


def send_reset_email(email: str, token: str) -> None:
    reset_link = f"{settings.PASSWORD_RESET_URL}?token={token}"
    subject = "SafeCare password reset"
    body = (
        "Xin chào,\n\n"
        "Chúng tôi nhận được yêu cầu đặt lại mật khẩu SafeCare. Nếu đó là bạn, "
        f"hãy mở liên kết sau hoặc nhập token: {reset_link}.\n\n"
        "Nếu bạn không yêu cầu, vui lòng bỏ qua email này."
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)
