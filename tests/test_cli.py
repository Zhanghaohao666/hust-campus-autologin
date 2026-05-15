from campus_autologin.__main__ import build_parser


def test_cli_has_public_mvp_subcommands():
    parser = build_parser()

    subcommands_action = next(
        action for action in parser._actions if getattr(action, "choices", None)
    )

    assert {
        "doctor",
        "gui",
        "init",
        "set-credential",
        "login",
        "watch",
        "logs",
        "install-service",
        "uninstall-service",
        "service-status",
        "install-task",
        "uninstall-task",
    }.issubset(set(subcommands_action.choices))


def test_init_accepts_username_interval_and_manual_url():
    parser = build_parser()

    args = parser.parse_args(
        [
            "init",
            "--username",
            "<student-id>",
            "--interval",
            "15",
            "--manual-login-url",
            "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc",
        ]
    )

    assert args.command == "init"
    assert args.username == "<student-id>"
    assert args.interval == 15
    assert args.manual_login_url.endswith("wlanuserip=abc")


def test_set_credential_accepts_username():
    parser = build_parser()

    args = parser.parse_args(["set-credential", "--username", "<student-id>"])

    assert args.command == "set-credential"
    assert args.username == "<student-id>"
