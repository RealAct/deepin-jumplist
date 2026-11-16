import time

_STARTED = time.time()  # taken before importing Qt; see app.REOPEN_GUARD_SECONDS

import sys  # noqa: E402

from deepin_jumplist.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(started=_STARTED))
