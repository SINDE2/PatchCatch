import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr


def send_email(game_name, title, link):
    """새로운 패치 발견 시 이메일 발송"""
    # ---------------- 설정 구역 ----------------
    SENDER_EMAIL= "their_email@gmail.com"
    APP_PASSWORD="their_app_password"
    RECEIVER_EMAIL="their_receiver@gmail.com" #returnaddress 받을이메일 작성
    # -------------------------------------------
    subject = f"[패치캐치!! 알림!!] {game_name} 새 업데이트 발견!"
    content = f"""
    [새로운 패치노트가 감지되었습니다]
    게임: {game_name}
    제목: {title}
    바로가기: {link}
    """
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = formataddr(('PatchCatch', sender_email))
    msg['To'] = receiver_email
    try:
        with smtplib.SMTP('smtp.naver.com', 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, app_password)
            server.send_message(msg)
        print(f"📧 이메일 발송 성공: {game_name}")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")
