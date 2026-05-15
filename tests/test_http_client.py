from campus_autologin.http_client import create_direct_session


def test_create_direct_session_ignores_environment_proxy():
    session = create_direct_session()

    assert session.trust_env is False
    assert session.proxies == {}
