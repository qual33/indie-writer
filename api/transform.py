import os
import json
from http.server import BaseHTTPRequestHandler
import openai
from supabase import create_client

# 검증 완료된 환경 변수 마스터 로드
openai.api_key = os.environ.get("OPENAI_API_KEY")
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = json.loads(self.rfile.read(content_length).decode('utf-8'))
        
        user_id = post_data.get("user_id")
        original_text = post_data.get("original_text")

        # 1. 자본 방어 유저 크레딧 한도 체크
        user_profile = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        if not user_profile.data:
            self.send_error_response(404, "User Profile Missing")
            return

        profile = user_profile.data
        if not profile.get("is_premium") and profile.get("used_credits") >= profile.get("max_credits"):
            self.send_error_response(402, "Payment Required") # 이 신호를 주면 index.html에서 결제창이 강제로 뿜어져 나옵니다.
            return

        # 2. 실리콘밸리 최고 연봉 카피라이터 톤 적용 프롬프트 엔진
        prompt = f"""
        You are an elite Silicon Valley tech founder and a viral content creator. 
        Convert the following raw, ugly technical notes or messy multi-language update code into TWO distinct high-converting premium content formats in absolute native English.

        Raw Input Notes: "{original_text}"

        Format 1: LinkedIn Authority Post
        - Tone: Thoughtful, insightful, authoritative, hooks the reader instantly.
        - Structure: Compelling first line, clear business value/lesson learned, actionable takeaway, spaced elegantly. No boring corporate boilerplate.

        Format 2: X (Twitter) Viral Thread
        - Tone: High energy, punchy, intellectual, high curiosity-gap.
        - Structure: A breakdown thread (2-3 concise tweets combined into a fluid readable copy) optimized for deep tech-community engagement.

        Return strictly in this exact JSON format below:
        {{
            "linkedin": "...",
            "twitter": "..."
        }}
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            ai_output = json.loads(response.choices[0].message.content.strip())
            
            # 3. 크레딧 차감 (안전하게 동기화)
            supabase.table("profiles").update({"used_credits": profile.get("used_credits") + 1}).eq("id", user_id).execute()

            # 4. 성공 리턴
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(ai_output).encode('utf-8'))

        except Exception as e:
            self.send_error_response(500, str(e))

    def send_error_response(self, status, msg):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode('utf-8'))

