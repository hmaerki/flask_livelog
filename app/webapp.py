import pathlib

import jinja2
from flask import Flask, Markup, render_template

from flask_livelog import livelog

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
DIRECTORY_EXAMPLES = DIRECTORY_OF_THIS_FILE.parent / "examples_pytest"

app = Flask(__name__)  # pylint: disable=invalid-name
# This will force exceptions when a variable is missing in a template
app.jinja_env.undefined = jinja2.StrictUndefined
app.secret_key = b'_6#y2L"F4Q8z\n\xec]/'
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

PROVIDER = livelog.LogfileProvider(DIRECTORY_OF_THIS_FILE.parent, "**/*.ansi")

livelog.LiveLog(app, PROVIDER)

FILENAMES = (
    (
        DIRECTORY_EXAMPLES / "log_pytest.ansi",
        Markup(
            "You may start <code>run_Pytests.sh</code> to see the live update.</code>"
        ),
    ),
    (
        DIRECTORY_EXAMPLES / "log_text.txt",
        "A Logfile with highlighting of ERROR, WARNING and INFO",
    ),
    (
        DIRECTORY_EXAMPLES / "logging_sample.log",
        "A logfile produced from a python-logger [ERRO], [WARN], etc.",
    ),
)


@app.route("/")
def index():
    return render_template("index.html", filenames=FILENAMES)
