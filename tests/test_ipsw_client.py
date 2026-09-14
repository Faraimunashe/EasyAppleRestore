from easyrestore.backend.http import HttpError, get_json
from easyrestore.backend.ipsw_api import IpswClient, device_ipsws_url


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None


def test_ipsw_client_fetches_and_caches(monkeypatch) -> None:
    calls: list[str] = []
    payload = (
        b'{"identifier":"iPhone13,4","name":"iPhone 12 Pro Max","boards":[],'
        b'"firmwares":[{"identifier":"iPhone13,4","version":"18.0","buildid":"22A",'
        b'"url":"https://example.test/a.ipsw","filesize":10,"sha1sum":"abc","signed":true}]}'
    )

    def fake_urlopen(request, timeout=30.0):  # noqa: ANN001
        calls.append(request.full_url)
        return _FakeResponse(payload)

    monkeypatch.setattr("easyrestore.backend.http.urlopen", fake_urlopen)
    client = IpswClient()
    first = client.fetch_device_firmwares("iPhone13,4")
    second = client.fetch_device_firmwares("iPhone13,4")
    assert first.latest_signed() is not None
    assert first.latest_signed().version == "18.0"
    assert second is first
    assert len(calls) == 1
    assert calls[0] == device_ipsws_url("iPhone13,4")


def test_get_json_maps_http_errors(monkeypatch) -> None:
    from urllib.error import HTTPError
    from io import BytesIO

    def boom(request, timeout=30.0):  # noqa: ANN001
        raise HTTPError(request.full_url, 404, "No", hdrs=None, fp=BytesIO())

    monkeypatch.setattr("easyrestore.backend.http.urlopen", boom)
    try:
        get_json("https://api.ipsw.me/v4/ipsw/device/nope")
        assert False, "expected HttpError"
    except HttpError as exc:
        assert exc.status == 404
