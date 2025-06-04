import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib.parse
import io

# 페이지 설정
st.set_page_config(
    page_title="네이버 블로그 검색 크롤러",
    page_icon="🔍",
    layout="wide"
)

def crawl_naver_blog(search_keyword, max_results=20):
    """네이버 블로그 검색 결과 크롤링"""
    
    # 검색어 URL 인코딩
    encoded_keyword = urllib.parse.quote(search_keyword)
    url = f"https://search.naver.com/search.naver?ssc=tab.blog.all&sm=tab_jum&query={encoded_keyword}"
    
    # 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # 웹페이지 요청
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 데이터 수집
        user_info_elements = soup.select('.user_info')[:max_results]
        
        # user_info 안의 첫 번째 sub 클래스만 수집
        sub_elements = []
        for user_info in user_info_elements:
            first_sub = user_info.select_one('.sub')
            if first_sub:
                sub_elements.append(first_sub)
        
        title_area_elements = soup.select('.title_area')[:max_results]
        dsc_area_elements = soup.select('.dsc_area')[:max_results]
        
        # 오늘 날짜
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 결과 데이터
        results = []
        
        # 최대 길이 결정
        max_length = max(
            len(user_info_elements),
            len(sub_elements), 
            len(title_area_elements),
            len(dsc_area_elements)
        )
        
        for i in range(min(max_length, max_results)):
            # 블로그명 추출
            blog_name = ""
            if i < len(user_info_elements):
                name_element = user_info_elements[i].select_one('.name')
                blog_name = name_element.get_text(strip=True) if name_element else ""
            
            # 게시일 추출
            post_date = ""
            if i < len(sub_elements):
                post_date = sub_elements[i].get_text(strip=True)
            
            # 타이틀 추출
            title = ""
            if i < len(title_area_elements):
                title = title_area_elements[i].get_text(strip=True)
            
            # 디스크립션과 링크 추출
            description = ""
            link = ""
            is_ad = "N"
            if i < len(dsc_area_elements):
                description = dsc_area_elements[i].get_text(strip=True)
                links = dsc_area_elements[i].select('a[href]')
                if links:
                    link_urls = [a.get('href', '') for a in links]
                    link = ' | '.join(link_urls)
                    # 광고 판별
                    if any(url.startswith('https://ader.naver.com/') for url in link_urls):
                        is_ad = "Y"
            
            # user_info 링크도 광고 체크
            if i < len(user_info_elements):
                name_element = user_info_elements[i].select_one('.name')
                if name_element:
                    name_href = name_element.get('href', '')
                    if name_href.startswith('https://ader.naver.com/'):
                        is_ad = "Y"
            
            # 결과 추가
            results.append({
                '날짜': today,
                '검색어': search_keyword,
                '노출순위': i + 1,
                '블로그명': blog_name,
                '타이틀': title,
                '디스크립션': description,
                '게시일': post_date,
                '광고여부': is_ad,
                '링크': link
            })
        
        return results, None
        
    except Exception as e:
        return None, str(e)

def main():
    """메인 웹앱"""
    
    # 제목
    st.title("🔍 네이버 블로그 검색 크롤러")
    st.markdown("검색어를 입력하면 네이버 블로그 검색 결과를 크롤링해서 CSV로 다운로드할 수 있습니다.")
    
    # 사이드바
    st.sidebar.header("⚙️ 설정")
    
    # 검색어 입력
    search_keyword = st.text_input(
        "🔍 검색어를 입력하세요:",
        placeholder="예: 온리프의원",
        help="네이버 블로그에서 검색할 키워드를 입력해주세요."
    )
    
    # 결과 개수 선택
    max_results = st.sidebar.selectbox(
        "📊 크롤링할 결과 개수:",
        [10, 20, 30, 50],
        index=1  # 기본값 20
    )
    
    # 검색 버튼
    if st.button("🚀 크롤링 시작", type="primary"):
        if not search_keyword.strip():
            st.error("❌ 검색어를 입력해주세요!")
            return
        
        # 로딩 표시
        with st.spinner(f"'{search_keyword}' 검색 결과를 크롤링 중..."):
            results, error = crawl_naver_blog(search_keyword.strip(), max_results)
        
        if error:
            st.error(f"❌ 크롤링 중 오류 발생: {error}")
            return
        
        if not results:
            st.warning("⚠️ 검색 결과를 찾을 수 없습니다.")
            return
        
        # 결과 표시
        st.success(f"✅ 총 {len(results)}개의 결과를 수집했습니다!")
        
        # 데이터프레임 생성
        df = pd.DataFrame(results)
        
        # 통계 정보
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("전체 결과", len(results))
        
        with col2:
            ad_count = len(df[df['광고여부'] == 'Y'])
            st.metric("광고 게시물", ad_count)
        
        with col3:
            normal_count = len(df[df['광고여부'] == 'N'])
            st.metric("일반 게시물", normal_count)
        
        with col4:
            if len(results) > 0:
                ad_ratio = round((ad_count / len(results)) * 100, 1)
                st.metric("광고 비율", f"{ad_ratio}%")
        
        # 데이터 테이블 표시
        st.subheader("📋 크롤링 결과")
        
        # 필터 옵션
        filter_option = st.selectbox(
            "필터:",
            ["전체", "일반 게시물만", "광고만"]
        )
        
        if filter_option == "일반 게시물만":
            filtered_df = df[df['광고여부'] == 'N']
        elif filter_option == "광고만":
            filtered_df = df[df['광고여부'] == 'Y']
        else:
            filtered_df = df
        
        # 테이블 표시
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )
        
        # CSV 다운로드 버튼
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_data = csv_buffer.getvalue()
        
        filename = f"naver_blog_search_{search_keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        st.download_button(
            label="📥 CSV 파일 다운로드",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            type="primary"
        )
        
        # 미리보기
        st.subheader("👀 상위 3개 결과 미리보기")
        for i, result in enumerate(results[:3]):
            ad_badge = "🔴 광고" if result['광고여부'] == "Y" else "🟢 일반"
            with st.expander(f"{i+1}순위 {ad_badge}: {result['블로그명']}"):
                st.write(f"**제목:** {result['타이틀']}")
                st.write(f"**설명:** {result['디스크립션'][:100]}...")
                st.write(f"**게시일:** {result['게시일']}")
                if result['링크']:
                    st.write(f"**링크:** {result['링크']}")

if __name__ == "__main__":
    main()