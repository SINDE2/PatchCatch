import json
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from googletrans import Translator
# ---------------------------------------------------------------------------
# [기본 설정]
# HEADERS: 봇(Bot)으로 오해받아 차단당하지 않도록, 일반 웹 브라우저(Chrome)인 척 속이는 헤더입니다.
# User-Agent가 없으면 일부 사이트(라이엇 등)는 접속을 거부합니다.
# ---------------------------------------------------------------------------
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
translator = Translator()
# ===========================================================================
# 1. 리그 오브 레전드 (LoL) 파싱 함수
# 특징: 북미(NA)와 한국(KR) 사이트를 모두 긁어와서 '버전'을 비교함
# ===========================================================================
def get_lol_comparison():
    # 기본 데이터 구조 초기화 (실패 시에도 이 구조는 반환됨)
    data = {
        "game": "League of Legends",
        "na_title": "로딩 중...", "na_link": "#",
        "kr_title": "로딩 중...", "kr_link": "#",
        "status": "확인 불가", "desc": "데이터를 가져오지 못했습니다."
    }
    # --- [1단계] 북미(NA) 사이트 크롤링 ---
    try:
        # requests로 HTML 텍스트 가져오기
        soup = BeautifulSoup(
            requests.get("https://www.leagueoflegends.com/en-us/news/game-updates/", headers=HEADERS).text,
            'html.parser'
        )
        # CSS Selector로 뉴스 링크들 찾기
        articles = soup.select('a[href^="/en-us/news/game-updates/"]')
        
        for art in articles:
            t = art.get_text(strip=True)
            # [필터링 로직]
            # 1. "Patch"와 "Notes" 단어가 반드시 있어야 함 (정규 패치노트)
            # 2. "TFT"(롤토체스) 단어는 없어야 함 (협곡 패치노트만 원함)
            if "Patch" in t and "Notes" in t and "TFT" not in t:
                data['na_title'] = t
                # href는 상대 경로(/en-us/...)이므로 앞에 도메인을 붙여 완전한 URL로 만듦
                data['na_link'] = "https://www.leagueoflegends.com" + art['href']
                break # 최신 글 하나만 찾으면 되므로 반복문 종료
    except Exception:
        pass # 에러가 나도 프로그램이 죽지 않고 다음 단계로 넘어가도록 처리
        
    # --- [2단계] 한국(KR) 사이트 크롤링 ---
    try:
        soup = BeautifulSoup(
            requests.get("https://www.leagueoflegends.com/ko-kr/news/game-updates/", headers=HEADERS).text,
            'html.parser'
        )
        articles = soup.select('a[href^="/ko-kr/news/game-updates/"]')
        for art in articles:
            t = art.get_text(strip=True)
            # [한국어 필터링 로직]
            # '패치'와 '노트'가 포함되어야 함.
            # 'TFT', '전략'(전략적 팀 전투), '개발'(개발자 인사이드) 등이 포함된 글은 제외
            if "패치" in t and "노트" in t and not any(x in t for x in ["TFT", "전략", "개발"]):
                data['kr_title'] = t
                data['kr_link'] = "https://www.leagueoflegends.com" + art['href']
                break
    except Exception:
        pass
        
    # --- [3단계] 버전 비교 (핵심 로직) ---
    
    # 정규표현식(re)을 사용해 제목에서 '숫자.숫자' 형태(예: 14.23)만 추출
    na_ver = re.search(r'(\d+\.\d+)', data['na_title'])
    kr_ver = re.search(r'(\d+\.\d+)', data['kr_title'])
    
    if na_ver and kr_ver:
        # 두 버전 숫자가 같으면 동기화 완료
        if na_ver.group(1) == kr_ver.group(1):
            data['status'] = "동기화 완료"
            data['desc'] = f"한국 서버에 {kr_ver.group(1)} 패치가 적용되었습니다."
        else:
            # 다르면 북미가 보통 더 빠르므로 '선행 공개'로 판단
            data['status'] = "북미 선행 공개"
            data['desc'] = f"북미({na_ver.group(1)})가 한국({kr_ver.group(1)})보다 최신 버전입니다."

    return data
# ===========================================================================
# 2. 발로란트 (Valorant) 파싱 헬퍼 함수들
# 특징: 발로란트 사이트는 Next.js로 만들어진 동적 사이트라 
# 일반적인 HTML 파싱(select)으로는 내용이 안 나올 수 있음.
# 따라서 숨겨진 JSON 데이터(page-data.json 또는 __NEXT_DATA__)를 직접 찾음.
# ===========================================================================
def _valorant_nodes_from_page_data():
    """
    방법 1: Next.js 사이트가 데이터를 로드하는 내부 API(page-data.json)를 직접 호출
    """
    data_url = "https://playvalorant.com/page-data/ko-kr/news/game-updates/page-data.json"
    # HTML이 아니라 JSON 형식이므로 .json()으로 바로 변환
    payload = requests.get(data_url, headers=HEADERS).json()
    
    # JSON 구조를 타고 들어가서 실제 뉴스 리스트(nodes) 추출
    return (
        payload.get("result", {})
        .get("data", {})
        .get("allContentstackNewsArticle", {})
        .get("nodes", [])
    )
def _valorant_nodes_from_next_data():
    """
    방법 2: HTML 안에 숨겨진 <script id="__NEXT_DATA__"> 태그 안의 JSON 파싱
    """
    html = requests.get("https://playvalorant.com/ko-kr/news/game-updates/", headers=HEADERS).text
    soup = BeautifulSoup(html, 'html.parser')
    
    # 숨겨진 데이터 스크립트 찾기
    script = soup.find('script', id="__NEXT_DATA__")
    if not script or not script.string:
        return []
        
    # 문자열을 JSON 객체로 변환
    data = json.loads(script.string)
    
    # 복잡한 JSON 트리에서 뉴스 데이터 위치 찾아가기
    return (
        data.get("props", {})
        .get("pageProps", {})
        .get("pageData", {})
        .get("data", {})
        .get("allContentstackNewsArticle", {})
        .get("nodes", [])
    )
def get_valorant_news():
    """
    위의 두 가지 방법(헬퍼 함수)을 사용하여 발로란트 뉴스를 가져오는 메인 함수
    """
    nodes = []
    # 1순위: page-data.json 방식 시도
    try:
        nodes = _valorant_nodes_from_page_data()
    except Exception:
        nodes = []
    # 실패하면 2순위: __NEXT_DATA__ 방식 시도 (이중 안전장치)
    if not nodes:
        try:
            nodes = _valorant_nodes_from_next_data()
        except Exception:
            nodes = []
    # 가져온 데이터 리스트(nodes)를 순회하며 패치노트 찾기
    for node in nodes:
        url_field = node.get("url")
        url_path = None
        # url 필드가 딕셔너리일 수도, 문자열일 수도 있어서 타입 체크
        if isinstance(url_field, dict):
            url_path = url_field.get("url")
        elif isinstance(url_field, str):
            url_path = url_field
        # URL에 'patch-notes'가 포함된 것만 찾음
        if not url_path or "patch-notes" not in url_path:
            continue
        title = node.get("title")
        link = "https://playvalorant.com" + url_path # 도메인 결합
        
        if title and link:
            return {
                "kr": {"game": "발로란트", "title": title, "link": link}
            }
    return {} # 실패 시 빈 딕셔너리 반환
# ===========================================================================
# 3. 이터널 리턴 (Eternal Return) 파싱 함수
# 특징: 공식 홈페이지의 HTML 구조를 분석하여 크롤링
# ===========================================================================
def get_eternal_return_news():
    try:
        # 패치노트 카테고리 URL
        url = "https://playeternalreturn.com/posts/news?categoryPath=patchnote"
        soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, 'html.parser')
        
        card = None
        # 모든 a 태그(링크)를 검사
        for link in soup.select('a'):
            href = link.get('href')
            if not href:
                continue
            
            # 링크 주소에 '/posts/news/'가 포함되어 있으면 뉴스글로 판단
            if '/posts/news/' in href:
                text = link.get_text(" ", strip=True) # 텍스트 추출
                if text:
                    card = (href, text)
                    break # 최신글 하나만 필요하므로 종료  
        if card:
            # urljoin: 현재 페이지 URL과 상대 경로(href)를 지능적으로 합쳐줌
            # 예: "https://site.com/page" + "/news/1" -> "https://site.com/news/1"
            full_link = urljoin(url, card[0])
            return {
                "kr": {"game": "이터널 리턴", "title": card[1], "link": full_link}
            }
    except Exception:
        pass
        
    return {}
