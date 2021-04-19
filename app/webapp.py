import pathlib

import jinja2
from flask import Flask, render_template

from flask_livelog import livelog

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
DIRECTORY_EXAMPLES = DIRECTORY_OF_THIS_FILE.parent / 'examples_pytest'

app = Flask(__name__)
# This will force exceptions when a variable is missing in a template
app.jinja_env.undefined = jinja2.StrictUndefined
app.secret_key = b'_6#y2L"F4Q8z\n\xec]/'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

provider = livelog.LogfileProvider(DIRECTORY_OF_THIS_FILE.parent, '**/*.ansi')

livelog.LiveLog(app, provider)

@app.route('/')
def index():
    filename_pytest = str(DIRECTORY_EXAMPLES / 'log_pytest.ansi')
    filename_test = str(DIRECTORY_EXAMPLES / 'log_text.txt')
    return render_template(
        'index.html',
        filename_pytest=filename_pytest,
        filename_test=filename_test
    )
