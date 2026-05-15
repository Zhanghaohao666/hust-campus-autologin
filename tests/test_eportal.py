import time

from campus_autologin.eportal import (
    EportalClient,
    LoginResult,
    QueryStringCache,
    encrypt_password,
)


class FakeResponse:
    def __init__(self, payload, status_code=200, encoding="utf-8"):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)
        self.encoding = encoding

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.posts = []

    def post(self, url, data, headers=None, timeout=None):
        self.posts.append({"url": url, "data": data, "headers": headers or {}, "timeout": timeout})
        return self.responses.pop(0)


def test_encrypt_password_uses_reverse_bytes_and_rsa_modulus():
    # Mirrors the eportal RSAUtils behavior: append >mac, reverse, then encrypt
    # little-endian chunks.
    exponent_hex = "11"
    modulus_hex = "010001"

    assert encrypt_password("p", exponent_hex, modulus_hex, mac_string="m") == "0a48 ef35"


def test_query_string_cache_expires_and_invalidates():
    now = time.monotonic()
    current = {"value": now}
    cache = QueryStringCache(ttl_seconds=30, clock=lambda: current["value"])

    cache.set("wlanuserip=abc")
    assert cache.get() == "wlanuserip=abc"

    current["value"] = now + 31
    assert cache.get() is None

    current["value"] = now
    cache = QueryStringCache(ttl_seconds=30, clock=lambda: current["value"])
    cache.set("nasip=def")
    cache.invalidate()
    assert cache.get() is None


def test_plain_login_posts_expected_payload():
    session = FakeSession(
        [
            FakeResponse({"passwordEncrypt": "false"}),
            FakeResponse({"result": "success", "message": "ok", "userIndex": "abc"}),
        ]
    )
    client = EportalClient(session=session, base_url="http://172.18.18.61:8080/eportal")

    result = client.login(
        username="<student-id>",
        password="secret",
        query_string="wlanuserip=abc",
        timeout=10,
    )

    assert result == LoginResult(success=True, message="ok", user_index="abc")
    assert session.posts[0]["url"].endswith("method=pageInfo")
    assert session.posts[0]["data"] == {"queryString": "wlanuserip=abc"}
    assert session.posts[1]["url"].endswith("method=login")
    assert session.posts[1]["timeout"] == 10
    assert session.posts[1]["data"]["userId"] == "<student-id>"
    assert session.posts[1]["data"]["password"] == "secret"
    assert session.posts[1]["data"]["queryString"] == "wlanuserip=abc"
    assert session.posts[1]["data"]["passwordEncrypt"] == "false"


def test_encrypted_login_posts_password_with_query_mac():
    session = FakeSession(
        [
            FakeResponse(
                {
                    "passwordEncrypt": "true",
                    "publicKeyExponent": "11",
                    "publicKeyModulus": "010001",
                }
            ),
            FakeResponse({"result": "success", "message": "ok"}),
        ]
    )
    client = EportalClient(session=session, base_url="http://172.18.18.61:8080/eportal")

    result = client.login(
        username="<student-id>",
        password="p",
        query_string="wlanuserip=abc&mac=m&nasip=def",
        timeout=10,
    )

    assert result.success is True
    assert session.posts[1]["data"]["password"] == encrypt_password(
        "p", "11", "010001", mac_string="m"
    )
    assert session.posts[1]["data"]["passwordEncrypt"] == "true"


def test_failed_login_invalidates_cache():
    session = FakeSession(
        [
            FakeResponse({"passwordEncrypt": "false"}),
            FakeResponse({"result": "fail", "message": "bad password"}),
        ]
    )
    cache = QueryStringCache(ttl_seconds=30)
    cache.set("wlanuserip=abc")
    client = EportalClient(
        session=session,
        base_url="http://172.18.18.61:8080/eportal",
        query_cache=cache,
    )

    result = client.login(
        username="<student-id>",
        password="secret",
        query_string="wlanuserip=abc",
        timeout=10,
    )

    assert result.success is False
    assert result.message == "bad password"
    assert cache.get() is None


def test_login_repairs_mojibake_failure_message():
    message = "用户不存在或者密码错误!"
    mojibake = message.encode("utf-8").decode("latin-1")
    session = FakeSession(
        [
            FakeResponse({"passwordEncrypt": "false"}),
            FakeResponse({"result": "fail", "message": mojibake}, encoding="ISO-8859-1"),
        ]
    )
    client = EportalClient(session=session, base_url="http://172.18.18.61:8080/eportal")

    result = client.login(
        username="<student-id>",
        password="secret",
        query_string="wlanuserip=abc",
        timeout=10,
    )

    assert result.success is False
    assert result.message == message
