import logging
import sys

logging.basicConfig(level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s - %(name)s - %(filename)s:"
    "%(lineno)s - %(levelname)s - %(message)s")

import monitors
import servers
