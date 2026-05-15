from campus_autologin.logs import tail_lines


def test_tail_lines_returns_last_n_lines(tmp_path):
    log = tmp_path / "watch.log"
    log.write_text("one\ntwo\nthree\n", encoding="utf-8")

    assert tail_lines(log, 2) == ["two", "three"]


def test_tail_lines_missing_file_returns_empty_list(tmp_path):
    assert tail_lines(tmp_path / "missing.log", 80) == []
