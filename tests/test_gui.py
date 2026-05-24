from campus_autologin.gui import (
    CampusAutologinApp,
    MANUAL_LOGIN_URL_HINT,
    OVERVIEW_SERVICE_HINT,
)


class FakeTextWidget:
    def __init__(self):
        self.calls = []

    def configure(self, **kwargs):
        self.calls.append(("configure", kwargs))

    def delete(self, start, end):
        self.calls.append(("delete", start, end))

    def insert(self, index, text):
        self.calls.append(("insert", index, text))

    def see(self, index):
        self.calls.append(("see", index))


def test_write_log_text_scrolls_to_latest_line():
    widget = FakeTextWidget()

    CampusAutologinApp._write_log_text(object(), widget, "old\nnew")

    assert ("insert", "1.0", "old\nnew") in widget.calls
    assert widget.calls[-2:] == [
        ("see", "end"),
        ("configure", {"state": "disabled"}),
    ]


def test_manual_login_url_hint_explains_optional_candidate_usage():
    assert MANUAL_LOGIN_URL_HINT == "可留空，此项仅提供探测候选参考。"


def test_overview_hint_explains_ui_can_be_closed_after_service_start():
    assert OVERVIEW_SERVICE_HINT == "服务启动后可以关闭本窗口，UI 仅用于查看状态和辅助操作。"
