from playwright.sync_api import sync_playwright
import re

def crawl_single_part_sync(page, part_number):
    """
    Crawls details for a single part number synchronously using the provided Playwright page.
    """
    url = f"https://kr.misumi-ec.com/vona2/result/?Keyword={part_number}"
    
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
        
        # HTTP 상태 코드 검사 (403 Forbidden 등 탐지)
        if response and response.status in [403, 401, 503]:
            return {
                "검색 품번": part_number,
                "매칭 여부": f"보안 차단됨 ({response.status} Forbidden - Akamai 방화벽)",
                "실제 품번": "-",
                "품명/설명": "-",
                "브랜드": "-",
                "가격": "-",
                "출하일": "-"
            }
            
        # Wait for AJAX results to load
        page.wait_for_timeout(6000)
        
        # Check if the page displays a "No results found" or "Access Denied" pattern
        body_text = page.inner_text("body")
        
        if "Access Denied" in body_text or "Reference #" in body_text or "you don't have permission to access" in body_text:
            return {
                "검색 품번": part_number,
                "매칭 여부": "보안 차단됨 (Access Denied - Akamai 방화벽)",
                "실제 품번": "-",
                "품명/설명": "-",
                "브랜드": "-",
                "가격": "-",
                "출하일": "-"
            }
            
        if "검색하신 정보를 찾을 수 없습니다" in body_text or "일치하는 상품이 없습니다" in body_text or "정보를 찾지 못했습니다" in body_text:
            return {
                "검색 품번": part_number,
                "매칭 여부": "검색 결과 없음",
                "실제 품번": "-",
                "품명/설명": "-",
                "브랜드": "-",
                "가격": "-",
                "출하일": "-"
            }
            
        # Extract product rows
        base_rows = page.query_selector_all("[class*='ProductBaseColumn_dataRowBase']")
        aside_rows = page.query_selector_all("[class*='ProductAsideColumns_dataRowBase']")
        
        if not base_rows:
            return {
                "검색 품번": part_number,
                "매칭 여부": "검색 결과 없음",
                "실제 품번": "-",
                "품명/설명": "-",
                "브랜드": "-",
                "가격": "-",
                "출하일": "-"
            }
            
        exact_row_idx = -1
        # Loop to find exact match
        clean_target = part_number.strip().upper().replace("-", "").replace(" ", "")
        
        for i, row in enumerate(base_rows):
            pn_el = row.query_selector("p[class*='partNumber'] a")
            if pn_el:
                pn_text = pn_el.inner_text()
                clean_pn = pn_text.strip().upper().replace("-", "").replace(" ", "")
                if clean_pn == clean_target:
                    exact_row_idx = i
                    break
                    
        if exact_row_idx != -1:
            idx = exact_row_idx
            matching_status = "일치하는 형번 있음"
        else:
            idx = 0
            matching_status = "일치하는 형번 없음 (추천 유사 형번)"
            
        base_row = base_rows[idx]
        aside_row = aside_rows[idx] if idx < len(aside_rows) else None
        
        pn_el = base_row.query_selector("p[class*='partNumber'] a")
        actual_pn = pn_el.inner_text() if pn_el else "-"
        
        desc_el = base_row.query_selector("p[class*='seriesName']")
        desc = desc_el.inner_text() if desc_el else "-"
        
        brand_el = base_row.query_selector("p[class*='brandName']")
        brand = brand_el.inner_text() if brand_el else "-"
        
        price = "-"
        shipping = "-"
        
        if aside_row:
            price_el = aside_row.query_selector("td[class*='priceLeadTimeDataCell']")
            if price_el:
                price_text = price_el.inner_text()
                
                # Parse price
                price_match = re.search(r"표준 가격\(VAT 별도\)\s*:\s*([^\n]+)", price_text)
                if price_match:
                    price = price_match.group(1).strip()
                
                # Parse shipping
                shipping_match = re.search(r"출하일\s*:\s*(.*)", price_text, re.DOTALL)
                if shipping_match:
                    shipping = shipping_match.group(1).strip().replace('\n', ' / ')
                    
        return {
            "검색 품번": part_number,
            "매칭 여부": matching_status,
            "실제 품번": actual_pn.strip(),
            "품명/설명": desc.strip(),
            "브랜드": brand.strip(),
            "가격": price.strip(),
            "출하일": shipping.strip()
        }
        
    except Exception as e:
        return {
            "검색 품번": part_number,
            "매칭 여부": f"오류 발생 ({str(e)})",
            "실제 품번": "-",
            "품명/설명": "-",
            "브랜드": "-",
            "가격": "-",
            "출하일": "-"
        }

def crawl_parts_service_sync(part_numbers, callback=None):
    """
    Crawls a list of part numbers sequentially (Synchronously).
    callback: function that receives (index, total_count, result_dict)
    """
    import os
    results = []
    total = len(part_numbers)
    
    with sync_playwright() as p:
        # Streamlit Cloud (Linux) 및 GUI가 없는 환경인지 감지
        is_streamlit_cloud = os.environ.get("STREAMLIT_SERVER") or os.name != "nt"
        headless = True if is_streamlit_cloud else False
        
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox"
        ]
        
        try:
            if is_streamlit_cloud:
                # 리눅스 컨테이너 서버에서는 채널 지정 없이 헤드리스 크로미움 실행
                browser = p.chromium.launch(headless=True, args=launch_args)
            else:
                # 로컬(Windows 등)에서는 기존 방식대로 Chrome 채널 및 헤드풀 실행
                browser = p.chromium.launch(channel="chrome", headless=headless, args=launch_args)
        except Exception as e:
            # 실패 시 일반 크로미움 헤드리스로 폴백 실행
            try:
                browser = p.chromium.launch(headless=True, args=launch_args)
            except Exception as e2:
                raise RuntimeError(
                    f"브라우저 실행 실패. Playwright 크로미움 다운로드가 필요할 수 있습니다. "
                    f"(에러1: {e}, 에러2: {e2})"
                )
                
        # 실제 데스크톱 크롬과 동일한 User-Agent 정보 추가
        chrome_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            user_agent=chrome_user_agent,
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1"
            }
        )
        page = context.new_page()
        
        for i, pn in enumerate(part_numbers):
            pn = pn.strip()
            if not pn:
                continue
                
            res = crawl_single_part_sync(page, pn)
            results.append(res)
            
            if callback:
                callback(i + 1, total, res)
                
        browser.close()
        
    return results
