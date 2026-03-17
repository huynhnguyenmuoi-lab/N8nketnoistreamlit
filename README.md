# N8n + Streamlit (Chat UI)

## Deploy trên Streamlit Community Cloud

- **Main file path**: `streamlit_app.py`
- **Python**: chọn trong **Advanced settings** lúc deploy (khuyến nghị **Python 3.11** hoặc **3.12**)
- **Dependencies**: `requirements.txt`

### Secrets (bắt buộc)

Trên Streamlit Cloud, vào **App settings → Secrets** và thêm:

```toml
WEBHOOK_URL = "https://<your-n8n-webhook-url>"
BEARER_TOKEN = "<optional-if-your-webhook-requires>"
```

Ứng dụng sẽ hiện cảnh báo và disable ô chat nếu `WEBHOOK_URL` chưa hợp lệ.

## Chạy local (khuyến nghị)

Vì Python 3.14 có thể không tương thích với một số wheel, nên nên dùng Python 3.11:

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

