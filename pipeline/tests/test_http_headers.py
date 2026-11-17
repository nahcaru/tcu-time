from unittest.mock import MagicMock, patch

from pipeline.adapters.http import DEFAULT_HEADERS, fetch_bytes, fetch_text


def _ok_response() -> MagicMock:
    resp = MagicMock()
    resp.text = "<html></html>"
    resp.content = b"%PDF"
    resp.headers = {}
    return resp


@patch("requests.get")
def test_fetch_text_sends_custom_user_agent(mock_get) -> None:
    # asc.tcu.ac.jp returns 403 to the default python-requests User-Agent.
    mock_get.return_value = _ok_response()
    fetch_text("https://example.com/")
    assert mock_get.call_args.kwargs["headers"] == DEFAULT_HEADERS


@patch("requests.get")
def test_fetch_bytes_sends_custom_user_agent(mock_get) -> None:
    mock_get.return_value = _ok_response()
    fetch_bytes("https://example.com/a.pdf")
    assert mock_get.call_args.kwargs["headers"] == DEFAULT_HEADERS
