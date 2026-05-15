from campus_autologin.notifier import Notifier


def test_notifier_returns_false_when_disabled():
    notifier = Notifier(enabled=False)

    assert notifier.notify("title", "message") is False


def test_notifier_falls_back_when_backend_missing(monkeypatch):
    def fail_import(name):
        raise ImportError(name)

    notifier = Notifier(enabled=True, importer=fail_import)

    assert notifier.notify("title", "message") is False
