import tomllib
from pathlib import Path

from campus_autologin import __version__


def test_package_version_matches_project_metadata():
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert __version__ == project["project"]["version"]
