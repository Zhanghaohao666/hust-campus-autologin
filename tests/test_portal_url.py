from campus_autologin.portal_url import ParsedPortalUrl, parse_portal_url


def test_parse_full_eportal_url_extracts_base_and_query():
    parsed = parse_portal_url(
        "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc&mac=def"
    )

    assert parsed == ParsedPortalUrl(
        base_url="http://172.18.18.61:8080/eportal",
        query_string="wlanuserip=abc&mac=def",
    )


def test_parse_portal_base_without_query():
    parsed = parse_portal_url("http://172.18.18.60:8080/eportal")

    assert parsed == ParsedPortalUrl(
        base_url="http://172.18.18.60:8080/eportal",
        query_string="",
    )


def test_parse_rejects_non_eportal_url():
    try:
        parse_portal_url("http://example.com/")
    except ValueError as exc:
        assert "eportal" in str(exc)
    else:
        raise AssertionError("expected ValueError")
