import pathlib
import logging

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent.absolute()


FORMAT = "[%(levelname)-4.4s] %(pathname)s:%(lineno)s %(message)s"

logging.basicConfig(
    filename=DIRECTORY_OF_THIS_FILE / "logging_sample.log",
    format=FORMAT,
    level=logging.DEBUG,
)
logging.debug("This message should go to the log file")
logging.info("So should this")
logging.warning("And this, too")
logging.error("And non-ASCII stuff, too, like Øresund and Malmö")
