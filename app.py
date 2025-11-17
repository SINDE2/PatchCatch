#핵심: database.json을 읽어서 이전 데이터와 다르면 send_email을 실행합니다.


from flask import Flask, render_template
from scrapers import get_lol_comparison, get_valorant_news, get_eternal_return_news
from flask import Flask, render_template
import json
import os
from scrapers import get_lol_comparison, get_valorant_news, get_eternal_return_news
from email_sender import send_email

app = Flask(__name__)
DB_FILE = 'database.json'

def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    # 1. DB 로드
    saved_data = load_db()
    
    # 2. 현재 데이터 크롤링
    lol = get_lol_comparison()
    val = get_valorant_news()
    er = get_eternal_return_news()
    
    current_data = {'LoL': lol, 'Valorant': val, 'EternalReturn': er}
    display_data = {}

    # 3. 비교 및 알림 로직
    for key, new_item in current_data.items():
        if not new_item: continue # 크롤링 실패시 스킵
        
        # DB에 없거나, 제목이 다르면 -> NEW!
        if key not in saved_data or saved_data[key]['title'] != new_item['title']:
            new_item['is_new'] = True
            # 이메일 발송 (처음 실행하거나 업데이트 시)
            # 실행 속도를 위해 주석 처리 해제 후 사용하세요
            # send_email(new_item['game'], new_item['title'], new_item['link'])
        else:
            new_item['is_new'] = False
            
        display_data[key] = new_item
        
        # LoL의 경우 북미/한국 타이틀 비교를 위해 별도 저장 필요하지만
        # 여기선 간단히 대표 타이틀(한국) 기준으로 저장
        if key == 'LoL':
            saved_data[key] = {'title': new_item['kr_title']}
        else:
            saved_data[key] = {'title': new_item['title']}

    # 4. DB 업데이트
    save_db(saved_data)

    return render_template('index.html', lol=lol, val=val, er=er)

if __name__ == '__main__':
    app.run(debug=True)
