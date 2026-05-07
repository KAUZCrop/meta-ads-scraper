"""
테스트 전체에서 공유하는 mock 설정.
app.py는 모듈 레벨에서 Streamlit/Playwright를 호출하므로
import 전에 sys.modules에 완전한 MagicMock을 주입합니다.
"""
import sys
from unittest.mock import MagicMock

# ── Streamlit mock ─────────────────────────────────────────────────────────
st_mock = MagicMock()
st_mock.secrets = {}
st_mock.session_state = MagicMock()
st_mock.session_state.get = MagicMock(return_value=None)

# st.columns(n) / st.columns([...]) 은 n개의 MagicMock을 반환해야 unpack이 됩니다
def _columns(spec, **kwargs):
    n = spec if isinstance(spec, int) else len(spec)
    return [MagicMock() for _ in range(n)]

st_mock.columns = _columns

# st.tabs(labels) 도 동일하게 처리
def _tabs(labels):
    return [MagicMock() for _ in labels]

st_mock.tabs = _tabs

sys.modules["streamlit"] = st_mock

# ── Playwright mock ────────────────────────────────────────────────────────
playwright_mock = MagicMock()
sys.modules["playwright"] = playwright_mock
sys.modules["playwright.sync_api"] = playwright_mock
