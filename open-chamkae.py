import openai
import os
import streamlit as st
import requests
from dotenv import load_dotenv
from datetime import datetime, time
from urllib.parse import quote

load_dotenv()

# 한글 폰트 설정
st.set_page_config(page_title="열려라 참깨", page_icon="🍽️")

# OpenAI API 키 설정 (환경 변수에서 불러오기)
openai.api_key = os.getenv("OPENAI_API_KEY")

# 카카오맵 REST API 키 설정 (환경 변수에서 불러오기)
kakao_api_key = os.getenv("KAKAO_API_KEY")


def get_coordinates_kakao(address):
    # 주소를 URL 인코딩
    encoded_address = quote(address)
    # 카카오맵 API로 주소를 위도와 경도로 변환
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={encoded_address}"
    headers = {"Authorization": f"KakaoAK {kakao_api_key}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result['documents']:
            lat = float(result['documents'][0]['y'])
            lng = float(result['documents'][0]['x'])
            return lat, lng
        else:
            st.error(f"주소 검색 결과가 없습니다: {result}")
    else:
        st.error(f"API 요청 오류: {response.status_code}")
    return None, None


def search_nearby_restaurants_kakao(lat, lng, radius=5000, query="음식점"):
    # 카카오맵 API로 주변 음식점 검색
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {kakao_api_key}"}
    params = {
        "y": lat,
        "x": lng,
        "radius": radius,
        "query": query
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()
        if result['documents']:
            return result['documents']
        else:
            st.error(f"음식점 검색 결과가 없습니다: {result}")
    else:
        st.error(f"API 요청 오류: {response.status_code}")
    return []


def get_business_status():
    # 가정된 영업 시간 (10:00 ~ 22:00)
    start_time = time(10, 0)
    end_time = time(22, 0)
    current_time = datetime.now().time()

    if start_time <= current_time <= end_time:
        return "영업 중"
    else:
        return "영업 종료"


def get_bot_response(address=None, query=None):
    info_str = ""
    all_closed = True

    # 주소와 키워드가 모두 주어졌는지 확인
    if address and query:
        # 주소로부터 좌표를 가져오기
        lat, lng = get_coordinates_kakao(address)
        if lat and lng:
            # 주변 음식점 검색
            nearby_restaurants = search_nearby_restaurants_kakao(
                lat, lng, query=query)

            # 거리에 따라 음식점을 정렬
            sorted_restaurants = sorted(
                nearby_restaurants, key=lambda x: float(x['distance']))

            if sorted_restaurants:
                info_str += f"### '{query}' 관련 음식점 목록 (반경 5km)\n\n"
                closed_info_str = "**모든 음식점이 현재 영업 종료 상태입니다.**\n\n참고 자료로 안내드립니다:\n\n"
                business_status = get_business_status()

                for idx, restaurant in enumerate(sorted_restaurants, 1):
                    place_name = restaurant['place_name']
                    place_address = restaurant['address_name']
                    place_url = restaurant['place_url']
                    distance = float(restaurant['distance']) / 1000  # km로 변환
                    # 영업 상태를 확인하고 모두 영업 종료인지 체크
                    is_open = (business_status == "영업 중")
                    all_closed = all_closed and not is_open
                    status_color = "red" if business_status == "영업 종료" else "black"

                    # 음식점 정보를 테이블 형태로 표시
                    info_str += f"**{idx}. {place_name}**\n"
                    info_str += f"- 주소: {place_address}\n"
                    info_str += f"- 거리: {distance:.2f} km\n"
                    info_str += f"- <span style='color: {status_color}'>영업 상태: {business_status}</span>\n"
                    info_str += f"- [지도보기]({place_url})\n\n"

                    # 영업 종료된 음식점 목록을 추가
                    closed_info_str += f"- **{place_name}**: {place_address}(거리: {distance:.2f} km) - 영업 상태: {business_status}([지도보기]({place_url}))\n"

                # 모든 음식점이 영업 종료인 경우 빨간 글씨로 안내
                if all_closed:
                    info_str = f"<span style='color:red;'>모든 음식점이 현재 영업 종료 상태입니다.</span>\n\n" + closed_info_str
            else:
                info_str += f"입력한 위치로부터 반경 5km 이내의 '{{query}}' 관련 음식점 정보를 찾을 수 없습니다.\n"
        else:
            info_str += "유효한 주소를 입력해주세요.\n"
    elif address:
        # 주소만 주어졌을 때: 키워드 요청
        return "주소를 입력해 주셨습니다. 이제 찾으실 음식 종류(키워드)를 입력해 주세요. (예: 치킨)"
    elif query:
        # 키워드만 주어졌을 때: 주소 요청
        return "키워드를 입력해 주셨습니다. 검색하고자 하는 주소를 함께 입력해 주세요."
    else:
        return "올바른 형식으로 입력해주세요. 예시: '서울특별시 종로구, 치킨'"

    # OpenAI GPT를 사용하여 응답 생성
    prompt = f"사용자가 '{address}, {query}'에 대해 물어봤습니다. 다음은 제공된 정보입니다: \n{info_str}\n\n이 정보를 바탕으로 고객에게 친절하게 응답해주세요."

    try:
        st.write("OpenAI API 호출 중...")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 친절한 챗봇입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        gpt_response = response.choices[0].message['content'].strip()
        st.write("OpenAI API 응답 받음")
        return f"{info_str}\n\n**AI 응답**: {gpt_response}"
    except Exception as e:
        st.error(f"OpenAI API 호출 중 오류 발생: {str(e)}")
        return info_str


def main():
    st.title("음식점 검색 챗봇 🍽️")

    # 상태 변수 초기화
    if 'address' not in st.session_state:
        st.session_state.address = ""
    if 'query' not in st.session_state:
        st.session_state.query = ""
    if 'reset' not in st.session_state:
        st.session_state.reset = False

    # 메인 채팅 인터페이스
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # 사이드바 설정: 검색 이력 표시와 새로운 검색 버튼
    with st.sidebar:
        # 새로운 검색 버튼
        if st.button('새로운 검색'):
            st.session_state.address = ""
            st.session_state.query = ""
            st.session_state.reset = True
            st.session_state.search_history.clear()  # 검색 이력 초기화

        st.header("검색 이력")
        if 'search_history' not in st.session_state:
            st.session_state.search_history = []

        # 검색 이력 표시
        for search in st.session_state.search_history:
            st.write(search)

    # 인풋 창 (주소와 키워드 입력)
    prompt = st.chat_input("주소와 검색할 키워드를 입력해주세요 (예: '서울특별시 종로구, 치킨')")

    if prompt and not st.session_state.reset:
        # 입력 내용을 ,로 분리해서 주소와 키워드 구분
        parts = prompt.split(",")

        # 주소와 키워드 분리
        if len(parts) == 2:
            st.session_state.address = parts[0].strip()
            st.session_state.query = parts[1].strip()
        elif len(parts) == 1:
            # 하나의 입력만 있을 때, 주소나 키워드 중 남은 항목을 채워줌
            part = parts[0].strip()
            if st.session_state.address:
                st.session_state.query = part
            else:
                st.session_state.address = part

        # 챗봇 응답
        response = get_bot_response(
            st.session_state.address, st.session_state.query)

        # 대화 기록 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append(
            {"role": "assistant", "content": response})

        # 검색 이력 저장
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.search_history.append(f"{current_time}: {prompt}")

    elif st.session_state.reset:
        st.write("새로운 검색을 시작해주세요.")
        st.session_state.reset = False  # 초기화 후 상태 변경

    # 대화 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)


if __name__ == "__main__":
    main()
