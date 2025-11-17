import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from googletrans import Translator

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

translator = Translator()


def get_lol_comparison():
    data = {
        "game": "League of Legends",
        "na_title": "로딩 중...", "na_link": "#",
        "kr_title": "로딩 중...", "kr_link": "#",
        "status": "확인 불가", "desc": "데이터를 가져오지 못했습니다."
    }

    try:
        soup = BeautifulSoup(
            requests.get("https://www.leagueoflegends.com/en-us/news/game-updates/", headers=HEADERS).text,
            'html.parser'
        )
        articles = soup.select('a[href^="/en-us/news/game-updates/"]')
        for art in articles:
            t = art.get_text(strip=True)
            if "Patch" in t and "Notes" in t and "TFT" not in t:
                data['na_title'] = t
                data['na_link'] = "https://www.leagueoflegends.com" + art['href']
                break
    except Exception:
        pass

    try:
        soup = BeautifulSoup(
            requests.get("https://www.leagueoflegends.com/ko-kr/news/game-updates/", headers=HEADERS).text,
            'html.parser'
        )
        articles = soup.select('a[href^="/ko-kr/news/game-updates/"]')
        for art in articles:
            t = art.get_text(strip=True)
            if "패치" in t and "노트" in t and not any(x in t for x in ["TFT", "전략", "개발"]):
                data['kr_title'] = t
                data['kr_link'] = "https://www.leagueoflegends.com" + art['href']
                break
    except Exception:
        pass

    na_ver = re.search(r'(\d+\.\d+)', data['na_title'])
    kr_ver = re.search(r'(\d+\.\d+)', data['kr_title'])
    if na_ver and kr_ver:
        if na_ver.group(1) == kr_ver.group(1):
            data['status'] = "동기화 완료"
            data['desc'] = f"한국 서버에 {kr_ver.group(1)} 패치가 적용되었습니다."
        else:
            data['status'] = "북미 선행 공개"
            data['desc'] = f"북미({na_ver.group(1)})가 한국({kr_ver.group(1)})보다 최신 버전입니다."

    return data


def get_valorant_news():
    try:
        base = "https://playvalorant.com/ko-kr/news/game-updates/"
        soup = BeautifulSoup(requests.get(base, headers=HEADERS).text, 'html.parser')
        card = soup.select_one('a[href*="/news/game-updates/valorant-patch-notes"]')
        if not card:
            return {}
        title = card.find(['h3', 'h5']).get_text(strip=True)
        return {
            "kr": {
                "game": "발로란트",
                "title": title,
                "link": "https://playvalorant.com" + card['href']
            }
        }
    except Exception:
        return {}


def get_eternal_return_news():
    try:
        url = "https://playeternalreturn.com/posts/news?categoryPath=patchnote"
        soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, 'html.parser')
        card = None
        for link in soup.select('a'):
            href = link.get('href')
            if not href:
                continue
            if '/posts/news/' in href:
                text = link.get_text(" ", strip=True)
                if text:
                    card = (href, text)
                    break
        if card:
            full_link = urljoin(url, card[0])
            return {
                "kr": {"game": "이터널 리턴", "title": card[1], "link": full_link}
            }
    except Exception:
        pass
    return {}
