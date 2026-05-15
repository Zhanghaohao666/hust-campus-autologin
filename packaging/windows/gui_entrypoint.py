import sys

from campus_autologin.__main__ import main
from campus_autologin.gui import launch_gui


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(main(sys.argv[1:]))
    raise SystemExit(launch_gui())
