#이 코드는 순수 LoL 패치노트가 나올 때까지 게시물을 탐색합니다.
#핵심 해결책: "제목"과 "URL" 이중 검증
#반복문(Loop) 필수: 리스트의 첫 번째 글(select_one)만 가져오면 안 됩니다. 위에서부터 하나씩 훑으면서 조건에 맞는 게 나올 때까지 찾아야 합니다.
#제외 키워드: 'TFT', '전략적 팀 전투', '개발자' 같은 단어가 들어간 글은 버려야(pass) 합니다.
#포함 키워드: '패치'와 '노트'라는 단어가 반드시 포함되어야 합니다.

import requests
from bs4 import BeautifulSoup
from googletrans import Translator
import re

# 차단 방지 헤더
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def get_lol_comparison():
    """리그 오브 레전드: 북미 vs 한국 버전 비교 및 필터링"""
    data = {
        "game": "League of Legends",
        "na_title": "로딩 중...", "na_link": "#",
        "kr_title": "로딩 중...", "kr_link": "#",
        "status": "확인 불가", "desc": "데이터를 가져오지 못했습니다."
    }
    
    # 1. 북미(NA) - Patch & Notes 키워드 필터링
    try:
        soup = BeautifulSoup(requests.get("https://www.leagueoflegends.com/en-us/news/game-updates/", headers=HEADERS).text, 'html.parser')
        articles = soup.select('a[href^="/en-us/news/game-updates/"]')
        for art in articles:
            t = art.get_text(strip=True)
            if "Patch" in t and "Notes" in t and "TFT" not in t:
                data['na_title'] = t
                data['na_link'] = "https://www.leagueoflegends.com" + art['href']
                break
    except: pass

    # 2. 한국(KR) - 패치 & 노트 키워드 필터링 (TFT 제외)
    try:
        soup = BeautifulSoup(requests.get("https://www.leagueoflegends.com/ko-kr/news/game-updates/", headers=HEADERS).text, 'html.parser')
        articles = soup.select('a[href^="/ko-kr/news/game-updates/"]')
        for art in articles:
            t = art.get_text(strip=True)
            # '패치'와 '노트'가 있고, 'TFT/전략적/개발자'가 없는 것
            if "패치" in t and "노트" in t and not any(x in t for x in ["TFT", "전략적", "개발자"]):
                data['kr_title'] = t
                data['kr_link'] = "https://www.leagueoflegends.com" + art['href']
                break
    except: pass

    # 3. 버전 비교
    na_ver = re.search(r'(\d+\.\d+)', data['na_title'])
    kr_ver = re.search(r'(\d+\.\d+)', data['kr_title'])
    
    if na_ver and kr_ver:
        if na_ver.group(1) == kr_ver.group(1):
            data['status'] = "✅ 동기화 완료"
            data['desc'] = f"한국 서버에 {kr_ver.group(1)} 패치가 적용되었습니다."
        else:
            data['status'] = "🚀 북미 선행 공개"
            data['desc'] = f"북미({na_ver.group(1)})가 한국({kr_ver.group(1)})보다 최신입니다."
    
    return data

def get_valorant_news():
    """발로란트: 한국 공식홈페이지"""
    try:
        url = "https://playvalorant.com/ko-kr/news/game-updates/"
        soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, 'html.parser')
        card = soup.select_one('a[href*="/news/game-updates/valorant-patch-notes"]')
        if card:
            title = card.find(['h3', 'h5']).get_text(strip=True)
            return {"game": "Valorant", "title": title, "link": "https://playvalorant.com" + card['href']}
    except: pass
    return None

def get_eternal_return_news():
    """이터널 리턴: 스팀 뉴스 (안정성)"""
    try:
        url = "https://store.steampowered.com/news/app/1049590"
        soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, 'html.parser')
        # 스팀 뉴스 구조 (변동 가능성 있으나 비교적 안정적)
        link_item = soup.select_one('#NewsMainItems a') 
        if link_item:
            # 번역기능 시연 (제목이 영어일 경우 번역)
            original_title = link_item.get_text(strip=True)
            translator = Translator()
            try:
                translated = translator.translate(original_title, dest='ko').text
            except:
                translated = original_title
                
            return {"game": "Eternal Return", "title": translated, "link": link_item['href']}
    except: pass
    return None
