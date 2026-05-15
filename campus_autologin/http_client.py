from __future__ import annotations

import requests


def create_direct_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.proxies = {}
    return session
