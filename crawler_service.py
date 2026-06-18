from playwright.sync_api import sync_playwright
import re

def crawl_single_part_sync(page, part_number):
    """
    Crawls details for a single part number synchronously using the provided Playwright page.
    """
    url = f"https://kr.misumi-ec.com/vona2/result/?Keyword={part_number}"
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        # Wait for AJAX results to load
        page.wait_for_timeout(6000)
        
        # Check if the page displays a "No results found" pattern
        body_text = page.inner_text("body")
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
    results = []
    total = len(part_numbers)
    
    with sync_playwright() as p:
        # Launch system Chrome in headful mode to bypass Akamai block
        browser = p.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
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
