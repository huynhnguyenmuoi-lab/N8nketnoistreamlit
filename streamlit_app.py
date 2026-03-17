import streamlit as st
import requests
import uuid
import re
import os
from urllib.parse import urlparse
import json

# Hàm đọc nội dung từ file văn bản
def rfile(name_file):
    try:
        with open(name_file, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
            st.error(f"File {name_file} không tồn tại.")

# Constants
def _get_secret(key: str, default: str | None = None) -> str | None:
    # Streamlit Cloud: set secrets in App settings; local: env var fallback.
    try:
        val = st.secrets.get(key, default)
    except Exception:
        val = default
    if val in (None, ""):
        val = os.getenv(key, default)
    return val


BEARER_TOKEN = _get_secret("BEARER_TOKEN")
WEBHOOK_URL = _get_secret("WEBHOOK_URL")
N8N_BASE_URL = _get_secret("N8N_BASE_URL")

def _is_valid_http_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


def _extract_webhook_id_from_n8n_workflow(path: str = "05. TroLydemo_1.json") -> str | None:
    """
    Đọc file workflow n8n (export JSON) và lấy webhookId của node type `n8n-nodes-base.webhook`.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for node in data.get("nodes", []):
            if node.get("type") == "n8n-nodes-base.webhook":
                wid = node.get("webhookId")
                if isinstance(wid, str) and _UUID_RE.search(wid):
                    return _UUID_RE.search(wid).group(0)
    except Exception:
        return None
    return None


def _normalize_n8n_webhook_url(url: str | None) -> str | None:
    """
    Sửa các URL bị dính ký tự rác sau UUID.
    Ví dụ: .../webhook-test/<uuid>rf3... -> .../webhook-test/<uuid>
    """
    if not url:
        return None
    m = _UUID_RE.search(url)
    if not m:
        return url
    wid = m.group(0)
    # giữ nguyên prefix trước UUID (bao gồm /webhook-test/)
    prefix = url[: m.start(0)]
    # nếu prefix không kết thúc bằng '/', thêm cho chắc
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    return f"{prefix}{wid}"


def _resolve_webhook_url() -> str | None:
    # 1) ưu tiên URL từ secrets/env nhưng normalize
    if WEBHOOK_URL:
        return _normalize_n8n_webhook_url(WEBHOOK_URL)

    # 2) nếu có base URL, tự ghép từ file workflow
    if not N8N_BASE_URL:
        return None
    wid = _extract_webhook_id_from_n8n_workflow()
    if not wid:
        return None
    base = N8N_BASE_URL.rstrip("/")
    return f"{base}/webhook-test/{wid}"


RESOLVED_WEBHOOK_URL = _resolve_webhook_url()

def generate_session_id():
    return str(uuid.uuid4())

def send_message_to_llm(session_id, message):
    if not _is_valid_http_url(RESOLVED_WEBHOOK_URL):
        return "Error: WEBHOOK_URL chưa được cấu hình hoặc không hợp lệ.", None
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN or ''}",
        "Content-Type": "application/json"
    }
    payload = {
        "sessionId": session_id,
        "chatInput": message
    }
    try:
        response = requests.post(RESOLVED_WEBHOOK_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        response_data = response.json()
        try:
            content = response_data.get("content") or response_data.get("output")
            image_url = response_data.get('url', None)
            return content, image_url  # Return both content and image URL
        except:
            content = response_data[0].get("content") or response_data[0].get("output")
            image_url = response_data[0].get('url', None)
            return content, image_url  # Return both content and image URL
    except requests.exceptions.RequestException as e:
        return f"Error: Failed to connect to the LLM - {str(e)}", None

def extract_text(output):
    """Trích xuất văn bản từ chuỗi output (loại bỏ hình ảnh)"""
    # Loại bỏ tất cả các phần chứa hình ảnh
    text_only = re.sub(r'!\[.*?\]\(.*?\)', '', output)
    return text_only

def display_message_with_image(text, image_url):
    """Hiển thị tin nhắn với văn bản và hình ảnh"""
    if image_url:
        st.markdown(
            f"""
            <a href="{image_url}" target="_blank">
                <img src="{image_url}" alt="Biểu đồ" style="width: 100%; height: auto; margin-bottom: 10px;">
            </a>
            """,
            unsafe_allow_html=True
        )
    
    # Hiển thị văn bản
    st.markdown(text, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Trợ lý AI", page_icon="🤖", layout="centered")
    st.markdown(
        """
        <style>
            .assistant {
                padding: 10px;
                border-radius: 10px;
                max-width: 75%;
                background: none;
                text-align: left;
                margin-bottom: 10px;
            }
            .user {
                padding: 10px;
                border-radius: 10px;
                max-width: 75%;
                background: none;
                text-align: right;
                margin-left: auto;
                margin-bottom: 10px;
            }
            .assistant::before { content: "🤖 "; font-weight: bold; }
            .user::before { content: " "; font-weight: bold; }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Hiển thị logo (nếu có)
    try:
        col1, col2, col3 = st.columns([3, 2, 3])
        with col2:
            st.image("logo.png")
    except:
        pass
    
    # Đọc nội dung tiêu đề từ file
    try:
        with open("00.xinchao.txt", "r", encoding="utf-8") as file:
            title_content = file.read()
    except Exception as e:
        title_content = "Trợ lý AI"

    st.markdown(
        f"""<h1 style="text-align: center; font-size: 24px;">{title_content}</h1>""",
        unsafe_allow_html=True
    )

    if not _is_valid_http_url(RESOLVED_WEBHOOK_URL):
        st.warning(
            "Chưa có `WEBHOOK_URL` hợp lệ. "
            "Trên Streamlit Cloud, vào **App settings → Secrets** và set `WEBHOOK_URL` "
            "(hoặc set `N8N_BASE_URL` để app tự ghép từ `05. TroLydemo_1.json`)."
        )

    # Khởi tạo session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = generate_session_id()

    # Hiển thị lịch sử tin nhắn
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            st.markdown(f'<div class="assistant">{message["content"]}</div>', unsafe_allow_html=True)
            # Hiển thị hình ảnh nếu có
            if "image_url" in message and message["image_url"]:
                st.markdown(
                    f"""
                    <a href="{message['image_url']}" target="_blank">
                        <img src="{message['image_url']}" alt="Biểu đồ" style="width: 100%; height: auto; margin-bottom: 10px;">
                    </a>
                    """,
                    unsafe_allow_html=True
                )
        elif message["role"] == "user":
            st.markdown(f'<div class="user">{message["content"]}</div>', unsafe_allow_html=True)

    # Ô nhập liệu cho người dùng
    if prompt := st.chat_input(
        "Nhập nội dung cần trao đổi ở đây nhé?",
        disabled=not _is_valid_http_url(RESOLVED_WEBHOOK_URL),
    ):
        # Thêm tin nhắn người dùng vào lịch sử
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Hiển thị tin nhắn người dùng ngay lập tức
        st.markdown(f'<div class="user">{prompt}</div>', unsafe_allow_html=True)
        
        # Gửi yêu cầu đến LLM và nhận phản hồi
        with st.spinner("Đang chờ phản hồi từ AI..."):
            llm_response, image_url = send_message_to_llm(st.session_state.session_id, prompt)
    
        # Kiểm tra nếu phản hồi không phải lỗi
        if isinstance(llm_response, str) and "Error" in llm_response:
            st.error(llm_response)
            # Thêm tin nhắn lỗi vào lịch sử
            st.session_state.messages.append({
                "role": "assistant", 
                "content": llm_response,
                "image_url": None
            })
        else:
            # Hiển thị phản hồi từ AI
            st.markdown(f'<div class="assistant">{llm_response}</div>', unsafe_allow_html=True)
            
            # Hiển thị hình ảnh nếu có
            if image_url:
                st.markdown(
                    f"""
                    <a href="{image_url}" target="_blank">
                        <img src="{image_url}" alt="Biểu đồ" style="width: 100%; height: auto; margin-bottom: 10px;">
                    </a>
                    """,
                    unsafe_allow_html=True
                )
            
            # Thêm phản hồi AI vào lịch sử
            st.session_state.messages.append({
                "role": "assistant", 
                "content": llm_response,
                "image_url": image_url
            })
        
        # Rerun để cập nhật giao diện
        st.rerun()

if __name__ == "__main__":
    main()