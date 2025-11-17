#롤전용
#이 코드는 순수 LoL 패치노트가 나올 때까지 게시물을 탐색합니다.
#핵심 해결책: "제목"과 "URL" 이중 검증
#반복문(Loop) 필수: 리스트의 첫 번째 글(select_one)만 가져오면 안 됩니다. 위에서부터 하나씩 훑으면서 조건에 맞는 게 나올 때까지 찾아야 합니다.
#제외 키워드: 'TFT', '전략적 팀 전투', '개발자' 같은 단어가 들어간 글은 버려야(pass) 합니다.
#포함 키워드: '패치'와 '노트'라는 단어가 반드시 포함되어야 합니다.

import requests
from bs4 import BeautifulSoup

def get_lol_comparison():
    data = {
        "game": "League of Legends",
        "na_title": "탐색 실패", "na_link": "",
        "kr_title": "탐색 실패", "kr_link": "",
        "status": "분석 중...",
        "desc": ""
    }
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # -------------------------------------------------------
    # 1. [북미] NA Server 로직
    # -------------------------------------------------------
    try:
        url_na = "https://www.leagueoflegends.com/en-us/news/game-updates/"
        soup_na = BeautifulSoup(requests.get(url_na, headers=headers).text, 'html.parser')
        
        # 모든 링크를 가져와서 검증 (첫 번째만 보면 안 됨)
        articles_na = soup_na.select('a[href^="/en-us/news/game-updates/"]')
        
        for art in articles_na:
            title = art.get_text(strip=True)
            href = art['href']
            
            # [필터링] 'Patch'와 'Notes'가 있고, 'TFT'는 없어야 함
            if "Patch" in title and "Notes" in title and "TFT" not in title:
                data['na_title'] = title
                data['na_link'] = "https://www.leagueoflegends.com" + href
                break # 찾았으면 반복문 종료
                
    except Exception as e:
        print(f"NA Parsing Error: {e}")

    # -------------------------------------------------------
    # 2. [한국] KR Server 로직 (여기가 중요!)
    # -------------------------------------------------------
    try:
        url_kr = "https://www.leagueoflegends.com/ko-kr/news/game-updates/"
        soup_kr = BeautifulSoup(requests.get(url_kr, headers=headers).text, 'html.parser')
        
        # 한국 사이트의 모든 업데이트 링크 수집
        articles_kr = soup_kr.select('a[href^="/ko-kr/news/game-updates/"]')
        
        for art in articles_kr:
            title = art.get_text(strip=True)
            href = art['href']
            
            # [강력한 필터링] 
            # 1. 제목에 '패치'가 있어야 함
            # 2. 제목에 '노트'가 있어야 함
            # 3. 'TFT', '전략적', '개발자'가 포함되면 안 됨 (롤체 거르기)
            if "패치" in title and "노트" in title:
                if "TFT" not in title and "전략적" not in title and "개발자" not in title:
                    data['kr_title'] = title
                    data['kr_link'] = "https://www.leagueoflegends.com" + href
                    break # 진짜 롤 패치노트를 찾으면 종료
                    
    except Exception as e:
        print(f"KR Parsing Error: {e}")

    # -------------------------------------------------------
    # 3. 비교 로직 (버전 숫자 추출 비교)
    # -------------------------------------------------------
    # 예: "Patch 14.23 Notes" vs "14.23 패치 노트" -> "14.23"만 뽑아서 비교
    import re
    
    # 숫자.숫자 패턴 추출 (예: 14.23)
    na_ver = re.search(r'(\d+\.\d+)', data['na_title'])
    kr_ver = re.search(r'(\d+\.\d+)', data['kr_title'])
    
    if na_ver and kr_ver:
        if na_ver.group(1) == kr_ver.group(1):
            data['status'] = "✅ 동기화 완료"
            data['desc'] = f"한국 서버도 {kr_ver.group(1)} 버전입니다."
        else:
            # 버전이 다르면 보통 숫자가 더 높은 쪽이 최신 (보통 NA가 빠름)
            data['status'] = "⚠️ 버전 불일치"
            data['desc'] = f"북미({na_ver.group(1)}) / 한국({kr_ver.group(1)}) - 차이가 있습니다."
    else:
        # 정규식으로 버전을 못 찾았을 경우 안전장치
        data['status'] = "❓ 버전 확인 불가"
        data['desc'] = "제목 형식이 변경되어 자동 비교가 어렵습니다."

    return data
