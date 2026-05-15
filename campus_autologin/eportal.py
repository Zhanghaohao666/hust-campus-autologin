from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import parse_qs

import requests


@dataclass(frozen=True)
class LoginResult:
    success: bool
    message: str
    user_index: str | None = None


class QueryStringCache:
    def __init__(
        self, ttl_seconds: int, clock: Callable[[], float] | None = None
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock or time.monotonic
        self._value: str | None = None
        self._expires_at = 0.0

    def set(self, value: str) -> None:
        self._value = value
        self._expires_at = self._clock() + self._ttl_seconds

    def get(self) -> str | None:
        if self._value is None:
            return None
        if self._clock() >= self._expires_at:
            self.invalidate()
            return None
        return self._value

    def invalidate(self) -> None:
        self._value = None
        self._expires_at = 0.0


def encrypt_password(
    password: str,
    exponent_hex: str,
    modulus_hex: str,
    *,
    mac_string: str = "111111111",
) -> str:
    exponent = int(exponent_hex, 16)
    modulus = int(modulus_hex, 16)
    payload = f"{password}>{mac_string}"
    return _rsautils_encrypt(payload, exponent, modulus)


class EportalClient:
    def __init__(
        self,
        *,
        session: requests.Session,
        base_url: str,
        query_cache: QueryStringCache | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._query_cache = query_cache

    def page_info(self, query_string: str, timeout: int) -> dict:
        response = self._session.post(
            self._interface_url("pageInfo"),
            data={"queryString": query_string},
            timeout=timeout,
        )
        return response.json()

    def login(
        self,
        *,
        username: str,
        password: str,
        query_string: str,
        timeout: int,
    ) -> LoginResult:
        page_info = self.page_info(query_string, timeout=timeout)
        payload_password = password
        password_encrypt = "false"
        if str(page_info.get("passwordEncrypt", "")).lower() == "true":
            payload_password = encrypt_password(
                password,
                str(page_info["publicKeyExponent"]),
                str(page_info["publicKeyModulus"]),
                mac_string=_query_mac(query_string),
            )
            password_encrypt = "true"

        payload = {
            "userId": username,
            "password": payload_password,
            "service": "",
            "queryString": query_string,
            "operatorPwd": "",
            "operatorUserId": "",
            "validcode": "",
            "passwordEncrypt": password_encrypt,
        }
        response = self._session.post(
            self._interface_url("login"),
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": self._base_url.rsplit("/eportal", 1)[0],
                "Referer": self._base_url + "/index.jsp?" + query_string,
            },
            timeout=timeout,
        )
        result = response.json()
        success = str(result.get("result", "")).lower() == "success"
        if not success and self._query_cache is not None:
            self._query_cache.invalidate()
        elif success and self._query_cache is not None:
            self._query_cache.set(query_string)
        return LoginResult(
            success=success,
            message=_decode_message(result.get("message", "")),
            user_index=result.get("userIndex"),
        )

    def _interface_url(self, method: str) -> str:
        return f"{self._base_url}/InterFace.do?method={method}"


def _decode_message(value: object) -> str:
    message = str(value)
    try:
        repaired = message.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return message
    if _contains_cjk(repaired) and not _contains_cjk(message):
        return repaired
    return message


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _query_mac(query_string: str) -> str:
    values = parse_qs(query_string, keep_blank_values=True).get("mac")
    if not values or not values[0]:
        return "111111111"
    return values[0]


def _rsautils_encrypt(payload: str, exponent: int, modulus: int) -> str:
    chunk_size = 2 * _rsautils_high_index(modulus)
    if chunk_size <= 0:
        raise ValueError("RSA modulus is too short")

    values = [ord(char) for char in payload[::-1]]
    while len(values) % chunk_size != 0:
        values.append(0)

    chunks: list[str] = []
    for start in range(0, len(values), chunk_size):
        block = 0
        for offset, value in enumerate(values[start : start + chunk_size]):
            block += value << (8 * offset)
        chunks.append(_rsautils_hex(pow(block, exponent, modulus)))
    return " ".join(chunks)


def _rsautils_high_index(value: int) -> int:
    index = 0
    while value >> (16 * (index + 1)):
        index += 1
    return index


def _rsautils_hex(value: int) -> str:
    if value == 0:
        return "0000"
    text = f"{value:x}"
    return "0" * (-len(text) % 4) + text
