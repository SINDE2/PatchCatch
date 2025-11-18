import json
import os
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
# [변경] googletrans -> deep_translator
from deep_translator import GoogleTranslator

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# [변경] 번역 함수 헬퍼
def translate_to_korean(text):
    try:
        return GoogleTranslator(source='auto', target='ko').translate(text)
    except:
        return text

# ===========================================================================
# 1. 리그 오브 레전드 (LoL)
# ===========================================================================
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

# ===========================================================================
# 2. 발로란트 (Valorant)
# ===========================================================================

def get_valorant_news():
    url = "https://playvalorant.com/ko-kr/news/game-updates/"
    r = requests.get(url, headers = HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    
    articles = soup.select('a[href*="/news/game-updates/valorant-patch-notes"]')
    for art in articles:
        title = art.select_one('[data-testid="card-title"]')
        description = art.select_one('[data-testid="card-description"]')
        title_str = title.text.strip() + ' ' + description.text.strip()

        if "패치 노트" in title_str:
            link = "https://playvalorant.com" + art.get('href')
            print(link)
            return{
                "kr": {"game" : "발로란트", "title" : title_str, "link" : link}
            }

# ===========================================================================
# 3. 이터널 리턴 (Eternal Return)
# ===========================================================================
def get_eternal_return_news():
    try:
        url = "https://playeternalreturn.com/posts/news?categoryPath=patchnote"
        soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, 'html.parser')
        card = None
        for link in soup.select('a'):
            href = link.get('href')
            if not href: continue
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
