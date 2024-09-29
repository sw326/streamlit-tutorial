import json
import configparser
import http.client
import streamlit as st
import requests


class CompletionExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id

    def _send_request(self, completion_request):
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id
        }

        with requests.post(self._host + '/testapp/v1/chat-completions/HCX-003',
                           headers=headers, json=completion_request, stream=True) as response:
            response = response.json()
            return response

    def execute(self, completion_request):
        res = self._send_request(completion_request)
        return res['result']['message']['content']


config = configparser.ConfigParser()

completion_executor = CompletionExecutor(
    host='https://clovastudio.stream.ntruss.com',
    api_key='NTA0MjU2MWZlZTcxNDJiY7jFx/wWX8LCfeVPuTazO9h5cW1M7/Cdct4jS5N147MV',
    api_key_primary_val='0XZl8XOscK9wM0320Tq8I2r1epxHGjGG4La4aHXF',
    request_id='edcae841-33ad-4522-9fd2-92b6e8eda7c5'
)

st.title('MBTI 대백과사전')
question = st.text_input(
    '질문',
    placeholder='질문을 입력해 주세요'
)

if question:
    preset_text = [{"role": "system",
                    "content": "- MBTI에 대한 지식을 기반으로, MBTI 질문에 답해보세요.\n\n질문: ESFJ는 문제에 봉착했을때 어떻게 대응하는가?\n답: 현실적인 해결 방법을 찾기 위해 노력합니다.\n###\n질문: ISFJ는 연인에게 어떻게 대하는 편인가?\n답: 섬세하고 다정하게 케어해주는 편입니다.\n####\n질문: INTP는 사람들이 많은 곳에 가면 어떻게 행동하는가?\n답: 주변의 상황을 파악하기 위해 관찰하는 편입니다.\n###\n질문: ESFJ는 충동적인 선택을 많이 하는 편인가?\n답: 아니다. 계획적으로 움직이는 편입니다."},
                   {"role": "user", "content": question}]

    request_data = {
        'messages': preset_text,
        'topP': 0.8,
        'topK': 0,
        'maxTokens': 512,
        'temperature': 0.5,
        'repeatPenalty': 5.0,
        'stopBefore': [],
        'includeAiFilters': False,
        'seed': 0
    }

    response_text = completion_executor.execute(request_data)
    st.markdown(response_text)
