
#주의: 구글 앱 비밀번호를 발급받아 password 부분에 넣어야 합니다.


import smtplib
from email.mime.text import MIMEText

def send_email(game_name, title, link):
    """새로운 패치 발견 시 이메일 발송"""
    # ---------------- 설정 구역 ----------------
    sender_email = "example@gmail.com"    #example 대신 본인의 계정이메일작성
    app_password = "password"             # 2단계 인증 -> 앱 비밀번호 생성
    receiver_email = "returnaddress@gmail.com"      #returnaddress 받을이메일 작성
    # -------------------------------------------

    subject = f"[패치캐치!! 알림!!] {game_name} 새 업데이트 발견!"
    content = f"""
    [새로운 패치노트가 감지되었습니다]
    
    게임: {game_name}
    제목: {title}
    
    바로가기: {link}
    """
    
    msg = MIMEText(content)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        # 지메일 SMTP 포트 465 (SSL)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        print(f"📧 이메일 발송 성공: {game_name}")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")
