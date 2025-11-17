from datetime import datetime, timezone
import json
import os
import re
from flask import Flask, render_template
from googletrans import Translator
# email_sender.py 파일이 같은 폴더에 있어야 합니다.
# 만약 이메일 설정이 안 되어 있다면 이 줄을 주석 처리하고 아래 send_email 호출부도 주석 처리하세요.
from email_sender import send_email 
from scrapers import (
    get_lol_comparison,
    get_valorant_news,
    get_eternal_return_news,
)
app = Flask(__name__)
DB_FILE = 'database.json'
HISTORY_LIMIT = 12
# googletrans 버전 문제 대비 (pip install googletrans==4.0.0-rc1 필요)
translator = Translator()
KOREAN_PATTERN = re.compile(r'[\u3131-\u318E\uAC00-\uD7A3]')
GAME_SECTIONS = [
    {
        "slug": "valorant",
        "badge": "Riot Games",
        "name": "Valorant",
        "subtitle": "게임 업데이트 & 패치 노트",
        "accent": "accent-valorant",
        "servers": [
            {
                "key": "valorant_kr",
                "label": "한국 서버",
                "chip": "KR",
                "desc": "한국어 공식 패치 노트를 정리합니다."
            }
        ]
    },
    {
        "slug": "eternal-return",
        "badge": "Nimble Neuron",
        "name": "Eternal Return",
        "subtitle": "스팀 공지 & 패치 요약",
        "accent": "accent-er",
        "servers": [
            {
                "key": "eternal_return_kr",
                "label": "한국 서버",
                "chip": "KR",
                "desc": "글로벌 공지를 한국어로 번역해 제공합니다."
            }
        ]
    }
]

NAV_LINKS = [
    {"label": "LoL 서버 비교", "target": "lol"},
    {"label": "발로란트", "target": "valorant"},
    {"label": "이터널 리턴", "target": "eternal-return"}
]
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {}
    if not isinstance(data, dict):
        return {}
    return data
def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
def translate_text(text):
    
    """
    텍스트 번역 함수. 
    1. 텍스트가 없으면 리턴
    2. 한국어가 포함되어 있으면 번역 불필요 -> 리턴
    3. 그 외의 경우 구글 번역 시도 -> 실패하면 원문 리턴
    """
    if not text:
        return ""
    if KOREAN_PATTERN.search(text):
        return text
    try:
        # src='auto'는 생략 가능, dest='ko'로 한국어 번역
        return translator.translate(text, dest='ko').text
    except Exception as e:
        print(f"번역 실패 (원문 사용): {e}")
        return text


def ensure_channel_record(storage, key):
    """DB 데이터 구조 호환성 유지 함수"""
    record = storage.get(key)
    if not isinstance(record, dict):
        record = {}

    history = record.get('history')
    if not isinstance(history, list):
        history = []

    legacy_title = record.pop('title', None)
    if legacy_title and not history:
        history.append({
            'title': legacy_title,
            'link': '#',
            'captured_at': '기록 이전 데이터'
        })
        record['last_title'] = legacy_title

    record['history'] = history
    storage[key] = record
    return record


def add_history_entry(storage, key, title, link):
    """새로운 기록을 history 리스트 맨 앞에 추가"""
    record = ensure_channel_record(storage, key)
    
    # 현재 시간 (UTC -> 한국 시간 고려 시 +9시간 필요하지만 여기선 UTC 기준 저장)
    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    entry = {
        'title': title,
        'link': link or '#',
        'captured_at': now_str
    }
    record['history'].insert(0, entry)
    record['history'] = record['history'][:HISTORY_LIMIT] # 개수 제한
    record['last_title'] = title
    storage[key] = record


def collect_payloads():
    """각 스크래퍼를 호출하여 데이터 수집"""
    payloads = {}
    lol_status = None

    # 1. LoL 데이터 수집
    lol = get_lol_comparison()
    if lol:
        lol_status = {
            'status': translate_text(lol.get('status')),
            'desc': translate_text(lol.get('desc'))
        }
        payloads['lol_na'] = {
            'game': 'League of Legends (NA)',
            'title': translate_text(lol.get('na_title')),
            'link': lol.get('na_link')
        }
        payloads['lol_kr'] = {
            'game': 'League of Legends (KR)',
            'title': translate_text(lol.get('kr_title')),
            'link': lol.get('kr_link')
        }

    # 2. 발로란트 데이터 수집
    # get_valorant_news는 {'kr': {...}} 형태 반환 가정
    valorant = get_valorant_news()
    for region, info in valorant.items():
        payloads[f'valorant_{region}'] = {
            'game': 'Valorant',
            'title': translate_text(info.get('title')),
            'link': info.get('link')
        }

    # 3. 이터널 리턴 데이터 수집
    eternal = get_eternal_return_news()
    for region, info in eternal.items():
        payloads[f'eternal_return_{region}'] = {
            'game': 'Eternal Return',
            'title': translate_text(info.get('title')),
            'link': info.get('link')
        }

    return payloads, lol_status

@app.route('/')
def index():
    saved = load_db()
    # 페이지 접속 시마다 크롤링 실행 (실제 서비스에선 비효율적이지만 2일 프로젝트엔 적합)
    payloads, lol_status = collect_payloads()

    for slug, payload in payloads.items():
        title = payload.get('title')
        # 제목이 없으면 건너뜀
        if not title:
            continue
            
        record = ensure_channel_record(saved, slug)
        
        # [비교 로직] 저장된 마지막 제목과 다르면 -> 새로운 글!
        is_new = record.get('last_title') != title
        
        if is_new:
            print(f"✨ 새로운 업데이트 발견: {slug} - {title}")
            add_history_entry(saved, slug, title, payload.get('link'))
            
            # 이메일 발송 (에러가 나도 페이지는 뜨도록 처리)
            link = payload.get('link')
            if link:
                try:
                    # send_email 함수가 email_sender.py에 정의되어 있어야 함
                    send_email(payload.get('game', slug), title, link)
                except Exception as e:
                    print(f"❌ 이메일 발송 실패: {e}")

    # 변경된 DB 저장
    save_db(saved)

    # 템플릿에 넘겨줄 데이터 정리
    def get_history(slug):
        return (saved.get(slug, {}).get('history') or [])[:5]

    lol_panels = {
        'na': get_history('lol_na'),
        'kr': get_history('lol_kr')
    }

    other_games = []
    for section in GAME_SECTIONS:
        servers = []
        for server in section['servers']:
            history = get_history(server['key'])
            servers.append({
                **server,
                'history': history
            })
        other_games.append({
            **section,
            'servers': servers
        })

    return render_template(
        'index.html',
        lol_status=lol_status,
        lol_panels=lol_panels,
        other_games=other_games,
        nav_links=NAV_LINKS
    )


if __name__ == '__main__':
    app.run(debug=True)
