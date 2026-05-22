import requests

from campus_autologin.network_probe import (
    ProbeStatus,
    extract_eportal_url,
    extract_query_string,
    is_campus_network_hint,
    probe_connectivity,
)


class FakeResponse:
    def __init__(self, url, text="", status_code=200, headers=None):
        self.url = url
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}


class FakeSession:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def get(self, url, timeout, allow_redirects=True):
        self.calls.append((url, timeout, allow_redirects))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_extract_eportal_url_from_response_url_and_html():
    url = "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc&nasip=def"
    html = f"<script>location.href='{url}'</script>"

    assert extract_eportal_url(FakeResponse(url="http://1.1.1.1", text=html)) == url
    assert extract_eportal_url(FakeResponse(url=url, text="")) == url


def test_extract_query_string_from_eportal_url():
    url = "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc&nasip=def"

    assert extract_query_string(url) == "wlanuserip=abc&nasip=def"


def test_campus_network_hint_matches_ssid_and_school_ranges():
    assert is_campus_network_hint(["HUST_WIRELESS_2.4G 2"])
    assert is_campus_network_hint(["以太网", "218.197.237.254"])
    assert is_campus_network_hint(["DNS 202.114.0.242"])
    assert not is_campus_network_hint(["Home WiFi", "192.168.31.1"])


def test_probe_connectivity_returns_online_for_normal_response():
    session = FakeSession([FakeResponse("http://www.msftconnecttest.com/connecttest.txt", "Microsoft Connect Test")])

    result = probe_connectivity(
        session=session,
        probe_urls=["http://www.msftconnecttest.com/connecttest.txt"],
        portal_base_urls=["http://172.18.18.61:8080/eportal"],
        timeout=5,
        campus_hints=["HUST_WIRELESS"],
    )

    assert result.status is ProbeStatus.ONLINE
    assert session.calls[0][1] == 5


def test_probe_connectivity_detects_captive_portal():
    portal_url = "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc&nasip=def"
    session = FakeSession([FakeResponse(portal_url, "<html>Campus Network</html>")])

    result = probe_connectivity(
        session=session,
        probe_urls=["http://edge-http.microsoft.com/captiveportal/generate_204"],
        portal_base_urls=["http://172.18.18.61:8080/eportal"],
        timeout=5,
        campus_hints=["HUST_WIRELESS"],
    )

    assert result.status is ProbeStatus.CAPTIVE_PORTAL
    assert result.portal_url == portal_url
    assert result.query_string == "wlanuserip=abc&nasip=def"


def test_probe_connectivity_detects_captive_portal_without_campus_hint():
    portal_url = "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc&nasip=def"
    session = FakeSession([FakeResponse(portal_url, "<html>Campus Network</html>")])

    result = probe_connectivity(
        session=session,
        probe_urls=["http://edge-http.microsoft.com/captiveportal/generate_204"],
        portal_base_urls=["http://172.18.18.61:8080/eportal"],
        timeout=5,
        campus_hints=["Dorm router", "192.168.31.1"],
    )

    assert result.status is ProbeStatus.CAPTIVE_PORTAL
    assert result.portal_url == portal_url
    assert result.query_string == "wlanuserip=abc&nasip=def"
    assert session.calls == [
        ("http://edge-http.microsoft.com/captiveportal/generate_204", 5, True),
    ]


def test_probe_connectivity_returns_not_campus_only_after_probe_attempts():
    session = FakeSession(
        [
            requests.Timeout("slow"),
            requests.ConnectTimeout("no route to portal"),
        ]
    )

    result = probe_connectivity(
        session=session,
        probe_urls=["http://www.msftconnecttest.com/connecttest.txt"],
        portal_base_urls=["http://172.18.18.61:8080/eportal"],
        timeout=5,
        campus_hints=["Home WiFi"],
    )

    assert result.status is ProbeStatus.NOT_CAMPUS_NETWORK
    assert session.calls == [
        ("http://www.msftconnecttest.com/connecttest.txt", 5, True),
        ("http://172.18.18.61:8080/eportal/", 5, True),
    ]


def test_probe_connectivity_checks_portal_after_probe_timeout():
    session = FakeSession(
        [
            requests.Timeout("slow"),
            FakeResponse("http://172.18.18.61:8080/eportal/", "<html>eportal</html>"),
        ]
    )

    result = probe_connectivity(
        session=session,
        probe_urls=["http://www.msftconnecttest.com/connecttest.txt"],
        portal_base_urls=["http://172.18.18.61:8080/eportal"],
        timeout=5,
        campus_hints=["HUST_WIRELESS"],
    )

    assert result.status is ProbeStatus.PORTAL_REACHABLE
    assert session.calls == [
        ("http://www.msftconnecttest.com/connecttest.txt", 5, True),
        ("http://172.18.18.61:8080/eportal/", 5, True),
    ]


def test_probe_uses_manual_login_url_when_probes_do_not_find_portal():
    session = FakeSession([requests.Timeout("slow")])
    manual = "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc&mac=def"

    result = probe_connectivity(
        session=session,
        probe_urls=["http://www.msftconnecttest.com/connecttest.txt"],
        portal_base_urls=[],
        timeout=5,
        campus_hints=["HUST_WIRELESS"],
        manual_login_url=manual,
    )

    assert result.status is ProbeStatus.CAPTIVE_PORTAL
    assert result.portal_url == manual
    assert result.query_string == "wlanuserip=abc&mac=def"


def test_probe_uses_manual_login_url_without_campus_hint():
    session = FakeSession([requests.Timeout("slow")])
    manual = "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc&mac=def"

    result = probe_connectivity(
        session=session,
        probe_urls=["http://www.msftconnecttest.com/connecttest.txt"],
        portal_base_urls=[],
        timeout=5,
        campus_hints=["Dorm router", "192.168.31.1"],
        manual_login_url=manual,
    )

    assert result.status is ProbeStatus.CAPTIVE_PORTAL
    assert result.portal_url == manual
    assert result.query_string == "wlanuserip=abc&mac=def"
    assert session.calls == [
        ("http://www.msftconnecttest.com/connecttest.txt", 5, True),
    ]
