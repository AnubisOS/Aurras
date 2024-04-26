import os
import transformers
import logging
from .aurras import Aurras

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

transformers.logging.set_verbosity_error()

logging.basicConfig(
    filename="logfile.log", format="%(asctime)s %(message)s", filemode="w"
)

