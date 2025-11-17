from flask import Flask, render_template
from scrapers import get_lol_comparison, get_valorant_news, get_eternal_return_news
# 이메일 및 DB 로직은 이전 답변 참고하여 import

app = Flask(__name__)

@app.route('/')
def index():
    # 3개 게임 데이터 가져오기
    lol_data = get_lol_comparison()
    val_data = get_valorant_news()
    er_data = get_eternal_return_news()
    
    # (선택) 여기서 DB 비교 후 이메일 발송 로직 호출
    # if lol_data['na_title'] != db_saved_title: send_email(...)
    
    return render_template('index.html', lol=lol_data, val=val_data, er=er_data)

if __name__ == '__main__':
    app.run(debug=True)
