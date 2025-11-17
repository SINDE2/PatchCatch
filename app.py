from datetime import datetime
import json
import os

from flask import Flask, render_template
from googletrans import Translator

from email_sender import send_email
from scrapers import (
    get_lol_comparison,
    get_valorant_news,
    get_eternal_return_news,
)

app = Flask(__name__)
DB_FILE = 'database.json'
HISTORY_LIMIT = 12
translator = Translator()

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
    if not text:
        return text
    try:
        detected = translator.detect(text)
        if detected.lang == 'ko':
            return text
        return translator.translate(text, dest='ko').text
    except Exception:
        return text


def ensure_channel_record(storage, key):
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
    record = ensure_channel_record(storage, key)
    entry = {
        'title': title,
        'link': link or '#',
        'captured_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }
    record['history'].insert(0, entry)
    record['history'] = record['history'][:HISTORY_LIMIT]
    record['last_title'] = title
    storage[key] = record


def collect_payloads():
    payloads = {}
    lol_status = None

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

    valorant = get_valorant_news()
    for region, info in valorant.items():
        payloads[f'valorant_{region}'] = {
            'game': 'Valorant',
            'title': translate_text(info.get('title')),
            'link': info.get('link')
        }

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
    payloads, lol_status = collect_payloads()

    for slug, payload in payloads.items():
        title = payload.get('title')
        if not title:
            continue
        record = ensure_channel_record(saved, slug)
        is_new = record.get('last_title') != title
        if is_new:
            add_history_entry(saved, slug, title, payload.get('link'))
            link = payload.get('link')
            if link:
                send_email(payload.get('game', slug), title, link)

    save_db(saved)

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
