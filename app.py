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
<<<<<<< HEAD
PATCH_LINK_PATTERN = re.compile(r'patch-(\d+)-(\d+)', re.IGNORECASE)
DECIMAL_PATTERN = re.compile(r'\d+\.\d+')
NUMBER_PATTERN = re.compile(r'\d+')

=======
>>>>>>> 3fcb5abe268723619d54c8b4bce3fff5e874d0cb
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
                "desc": "한국어 공식 패치 노트를 정리합니다."
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


def parse_version(text, link=None):
    if link:
        match = PATCH_LINK_PATTERN.search(link)
        if match:
            return f"{match.group(1)}.{match.group(2)}"
    if text:
        decimals = DECIMAL_PATTERN.findall(text)
        for dec in decimals:
            if dec:
                return dec
        numbers = NUMBER_PATTERN.findall(text)
        if numbers:
            return numbers[0]
    return None


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

<<<<<<< HEAD
    def build_payload(game_name, raw_title, link):
        if not raw_title:
            return None
        return {
            'game': game_name,
            'title': translate_text(raw_title),
            'link': link,
            'version': parse_version(raw_title, link)
        }

=======
    # 1. LoL 데이터 수집
>>>>>>> 3fcb5abe268723619d54c8b4bce3fff5e874d0cb
    lol = get_lol_comparison()
    if lol:
        lol_status = {
            'status': translate_text(lol.get('status')),
            'desc': translate_text(lol.get('desc'))
        }
        na_payload = build_payload('League of Legends (NA)', lol.get('na_title'), lol.get('na_link'))
        kr_payload = build_payload('League of Legends (KR)', lol.get('kr_title'), lol.get('kr_link'))
        if na_payload:
            payloads['lol_na'] = na_payload
        if kr_payload:
            payloads['lol_kr'] = kr_payload

    # 2. 발로란트 데이터 수집
    # get_valorant_news는 {'kr': {...}} 형태 반환 가정
    valorant = get_valorant_news()
    for region, info in valorant.items():
        entry = build_payload('Valorant', info.get('title'), info.get('link'))
        if entry:
            payloads[f'valorant_{region}'] = entry

    # 3. 이터널 리턴 데이터 수집
    eternal = get_eternal_return_news()
    for region, info in eternal.items():
        entry = build_payload('Eternal Return', info.get('title'), info.get('link'))
        if entry:
            payloads[f'eternal_return_{region}'] = entry

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
<<<<<<< HEAD
        payload['is_new'] = is_new
=======
        
>>>>>>> 3fcb5abe268723619d54c8b4bce3fff5e874d0cb
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
]
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

    def get_latest_entry(slug):
        if slug in payloads and payloads[slug].get('title'):
            return payloads[slug]
        history = saved.get(slug, {}).get('history') or []
        return history[0] if history else {}

    dashboard_cards = []
    lol_na_entry = get_latest_entry('lol_na')
    lol_kr_entry = get_latest_entry('lol_kr')
    dashboard_cards.append({
        'slug': 'lol',
        'name': '리그 오브 레전드',
        'na_version': payloads.get('lol_na', {}).get('version') or parse_version(
            lol_na_entry.get('title'), lol_na_entry.get('link')
        ),
        'kr_version': payloads.get('lol_kr', {}).get('version') or parse_version(
            lol_kr_entry.get('title'), lol_kr_entry.get('link')
        ),
        'status': (lol_status or {}).get('status') or '상태 미확인',
        'desc': (lol_status or {}).get('desc'),
        'is_new': payloads.get('lol_na', {}).get('is_new', False) or payloads.get('lol_kr', {}).get('is_new', False),
        'has_na': True
    })

    for section in GAME_SECTIONS:
        server_key = section['servers'][0]['key']
        entry = get_latest_entry(server_key)
        dashboard_cards.append({
            'slug': section['slug'],
            'name': section['name'],
            'na_version': None,
            'kr_version': payloads.get(server_key, {}).get('version') or parse_version(
                entry.get('title'), entry.get('link')
            ),
            'status': '동기화 완료' if entry else '대기중',
            'desc': None,
            'is_new': payloads.get(server_key, {}).get('is_new', False),
            'has_na': False
        })

    return render_template(
        'index.html',
        lol_status=lol_status,
        lol_panels=lol_panels,
        other_games=other_games,
        nav_links=NAV_LINKS,
        dashboard_cards=dashboard_cards
    )


if __name__ == '__main__':
    app.run(debug=True)
