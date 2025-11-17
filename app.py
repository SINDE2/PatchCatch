from datetime import datetime
import json
import os
import re
from flask import Flask, render_template, url_for
# [변경] googletrans -> deep_translator
from deep_translator import GoogleTranslator
from email_sender import send_email
from scrapers import (
    get_lol_comparison,
    get_valorant_news,
    get_eternal_return_news,
)
app = Flask(__name__)
DB_FILE = 'database.json'
HISTORY_LIMIT = 12
KOREAN_PATTERN = re.compile(r'[\u3131-\u318E\uAC00-\uD7A3]')
PATCH_LINK_PATTERN = re.compile(r'patch-(\d+)-(\d+)', re.IGNORECASE)
DECIMAL_PATTERN = re.compile(r'\d+\.\d+')
NUMBER_PATTERN = re.compile(r'\d+')
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
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except json.JSONDecodeError: return {}
    return {}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# [변경] 번역 함수 수정
def translate_text(text):
    if not text: return ""
    if KOREAN_PATTERN.search(text): return text
    try:
        return GoogleTranslator(source='auto', target='ko').translate(text)
    except:
        return text

def parse_version(text, link=None):
    if link:
        match = PATCH_LINK_PATTERN.search(link)
        if match: return f"{match.group(1)}.{match.group(2)}"
    if text:
        decimals = DECIMAL_PATTERN.findall(text)
        for dec in decimals: return dec
        numbers = NUMBER_PATTERN.findall(text)
        if numbers: return numbers[0]
    return None

def ensure_channel_record(storage, key):
    record = storage.get(key)
    if not isinstance(record, dict): record = {}
    history = record.get('history')
    if not isinstance(history, list): history = []
    legacy_title = record.pop('title', None)
    if legacy_title and not history:
        history.append({'title': legacy_title, 'link': '#', 'captured_at': '기록 이전 데이터'})
        record['last_title'] = legacy_title
    record['history'] = history
    storage[key] = record
    return record

def add_history_entry(storage, key, title, link):
    record = ensure_channel_record(storage, key)
    entry = {
        'title': title,
        'link': link or '#',
        'captured_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    record['history'].insert(0, entry)
    record['history'] = record['history'][:HISTORY_LIMIT]
    record['last_title'] = title
    storage[key] = record

def collect_payloads():
    payloads = {}
    lol_status = None

    def build_payload(game_name, raw_title, link):
        if not raw_title: return None
        return {
            'game': game_name,
            'title': translate_text(raw_title),
            'link': link,
            'version': parse_version(raw_title, link)
        }

    lol = get_lol_comparison()
    if lol:
        lol_status = {'status': translate_text(lol.get('status')), 'desc': translate_text(lol.get('desc'))}
        p_na = build_payload('LoL (NA)', lol.get('na_title'), lol.get('na_link'))
        p_kr = build_payload('LoL (KR)', lol.get('kr_title'), lol.get('kr_link'))
        if p_na: payloads['lol_na'] = p_na
        if p_kr: payloads['lol_kr'] = p_kr

    val = get_valorant_news()
    for r, i in val.items():
        e = build_payload('Valorant', i.get('title'), i.get('link'))
        if e: payloads[f'valorant_{r}'] = e

    er = get_eternal_return_news()
    for r, i in er.items():
        e = build_payload('Eternal Return', i.get('title'), i.get('link'))
        if e: payloads[f'eternal_return_{r}'] = e

    return payloads, lol_status

@app.route('/')
def index():
    saved = load_db()
    payloads, lol_status = collect_payloads()

    for slug, payload in payloads.items():
        title = payload.get('title')
        if not title: continue
        record = ensure_channel_record(saved, slug)
        is_new = record.get('last_title') != title
        payload['is_new'] = is_new
        if is_new:
            add_history_entry(saved, slug, title, payload.get('link'))
            link = payload.get('link')
            if link:
                try: send_email(payload.get('game', slug), title, link)
                except: pass
    
    save_db(saved)

    def get_latest_entry(slug):
        if slug in payloads and payloads[slug].get('title'): return payloads[slug]
        h = saved.get(slug, {}).get('history') or []
        return h[0] if h else {}

    def get_history(slug):
        return (saved.get(slug, {}).get('history') or [])[:5]

    lol_panels = {'na': get_history('lol_na'), 'kr': get_history('lol_kr')}
    
    other_games = []
    for sec in GAME_SECTIONS:
        servers = []
        for srv in sec['servers']:
            servers.append({**srv, 'history': get_history(srv['key'])})
        other_games.append({**sec, 'servers': servers})

    dashboard_cards = []
    l_na = get_latest_entry('lol_na')
    l_kr = get_latest_entry('lol_kr')
    dashboard_cards.append({
        'slug': 'lol',
        'name': '리그 오브 레전드',
        'na_version': payloads.get('lol_na', {}).get('version') or parse_version(l_na.get('title'), l_na.get('link')),
        'kr_version': payloads.get('lol_kr', {}).get('version') or parse_version(l_kr.get('title'), l_kr.get('link')),
        'status': (lol_status or {}).get('status') or '상태 미확인',
        'desc': (lol_status or {}).get('desc'),
        'is_new': payloads.get('lol_na', {}).get('is_new') or payloads.get('lol_kr', {}).get('is_new'),
        'has_na': True
    })

    for sec in GAME_SECTIONS:
        s_key = sec['servers'][0]['key']
        entry = get_latest_entry(s_key)
        dashboard_cards.append({
            'slug': sec['slug'],
            'name': sec['name'],
            'na_version': None,
            'kr_version': payloads.get(s_key, {}).get('version') or parse_version(entry.get('title'), entry.get('link')),
            'status': '동기화 완료' if entry else '대기중',
            'desc': None,
            'is_new': payloads.get(s_key, {}).get('is_new'),
            'has_na': False
        })

    return render_template('index.html', lol_status=lol_status, lol_panels=lol_panels, other_games=other_games, nav_links=NAV_LINKS, dashboard_cards=dashboard_cards)

@app.route('/game/<slug>')
def game_detail(slug):
    saved = load_db()
    target_game = None
    if slug == 'lol':
        target_game = {
            "slug": "lol", "name": "League of Legends", "badge": "Riot Games",
            "subtitle": "북미 & 한국 서버 패치 노트",
            "external_link": "https://www.leagueoflegends.com/ko-kr/news/game-updates/"
        }
        history = saved.get('lol_kr', {}).get('history', [])
    else:
        for sec in GAME_SECTIONS:
            if sec['slug'] == slug:
                target_game = sec
                target_game['external_link'] = "#"
                break
        if not target_game: return "Game Not Found", 404
        history = []
        if target_game.get('servers'):
            s_key = target_game['servers'][0]['key']
            history = saved.get(s_key, {}).get('history', [])

    return render_template('game_list.html', game=target_game, history=history)

if __name__ == '__main__':
    app.run(debug=True)
