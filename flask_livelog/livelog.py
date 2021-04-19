import io
import os
import queue
import html
import time
import shlex
import pathlib
import threading
import subprocess
from dataclasses import dataclass

try:
    import msvcrt
    import win32file

    def fileopen(filename):
        assert isinstance(filename, pathlib.Path)

        class WindowsFile:
            """
            The normal python-file locks windows file, so the cannot be deleted anymore.
            This class opens a file for read without locking the file.
            The class avoids the garbage collector to remove 'self.win_handle' and 'self.os_handle'.
            """

            def __init__(self, filename):
                self.win_handle = win32file.CreateFile(
                    str(filename.absolute()),
                    win32file.GENERIC_READ,
                    win32file.FILE_SHARE_DELETE
                    | win32file.FILE_SHARE_READ
                    | win32file.FILE_SHARE_WRITE,
                    None,
                    win32file.OPEN_EXISTING,
                    win32file.FILE_ATTRIBUTE_NORMAL,
                    None,
                )
                self.os_handle = msvcrt.open_osfhandle(
                    self.win_handle.handle, os.O_RDONLY
                )
                file_handle = os.fdopen(self.os_handle, mode="rb")
                self.file_handle = self.read_bom(file_handle)

            def read_bom(self, file_handle):  # pylint: disable=no-self-use
                for _i in range(10):
                    # https://en.wikipedia.org/wiki/Byte_order_mark
                    bom = file_handle.read(2)
                    if bom == b"\xff\xfe":
                        return io.TextIOWrapper(file_handle, encoding="utf-16-le")
                    time.sleep(0.05)

                # cmd.exe does not use a bom. We assume "utf-8"
                file_handle.seek(0)
                return io.TextIOWrapper(file_handle, encoding="utf-8")

            def read(self):
                text = self.file_handle.read()
                return text

            def close(self):
                self.file_handle.close()

            def __enter__(self):
                return self

            def __exit__(self, _type, _value, _tb):
                self.close()

        return WindowsFile(filename)


except ImportError:

    def fileopen(filename):
        assert isinstance(filename, pathlib.Path)
        return filename.open("r")


try:
    import ansi2html

    ANSI2COLOR_PRESENT = True
except ImportError:
    ANSI2COLOR_PRESENT = False

from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField
from flask import render_template, Response, request


if ANSI2COLOR_PRESENT:

    class Ansi2HtmlRenderer(ansi2html.Ansi2HTMLConverter):
        """This renderer allows to generated colorized pytest-output"""

        def __init__(self):
            super().__init__(inline=True, escaped=False)

        def render(self, text):
            parts = self._apply_regex(text, set())
            parts = self._collapse_cursor(parts)
            return "".join(parts).replace("\n", "<br>")


class LineCodeRenderer:  # pylint: disable=too-few-public-methods
    def render(self, text):  # pylint: disable=no-self-use
        # Surround with 'pre'
        text = f"<pre>{html.escape(text)}</pre>"
        # If there are newlines, replace with 'pre'
        text = text.replace("\n", "</pre><pre>")
        # Remove empty lines
        text = text.replace("<pre></pre>", "")
        return text


@dataclass
class WordHighlight:
    word: str
    color: str


@dataclass
class LogfileRenderer:
    wordrenderer = (
        WordHighlight("ERROR", "red"),
        WordHighlight("WARNING", "#ff7700"),  # Orange
        WordHighlight("INFO", "blue"),
    )
    buffer: str = ""

    def __span(self, line, word, color):  # pylint: disable=no-self-use
        span = f'<span style="font-weight: bold">{word}</span>'
        line = line.replace(word, span)
        return f'<span style="color: {color}">{line}</span>'

    def render(self, text):
        text = self.buffer + html.escape(text)
        self.buffer = ""
        lines = text.split("\n")
        html_ = ""
        self.buffer = lines[-1]
        if len(lines[-1]) == 0:
            # If the line does not end with endline: Keep it for the next call
            lines = lines[:-1]
        for line in lines:
            for wordrenderer in self.wordrenderer:
                if line.find(wordrenderer.word) >= 0:
                    line = self.__span(
                        line=line, word=wordrenderer.word, color=wordrenderer.color
                    )
                    break
            html_ += line + "<br>"

        return html_


def get_renderer(filename):
    assert isinstance(filename, pathlib.Path)
    if ANSI2COLOR_PRESENT:
        if filename.suffix == ".ansi":
            return Ansi2HtmlRenderer()
    return LogfileRenderer()


def generator_file(filename):
    assert isinstance(filename, pathlib.Path)

    renderer = get_renderer(filename)

    try:
        inode = filename.lstat().st_ino
    except FileNotFoundError:
        inode = 0
        yield htmlnotice("File does not exist yet")

    while True:
        try:
            inode_ = filename.lstat().st_ino
            if inode != inode_:
                inode = inode_
                yield htmlnotice("File has been created")
        except FileNotFoundError:
            # No file this point of time.
            time.sleep(0.5)
            continue

        with fileopen(filename) as fin:
            while True:
                text = fin.read()
                if text:
                    yield renderer.render(text)
                    continue
                try:
                    inode_ = filename.lstat().st_ino
                    if inode != inode_:
                        inode = 0
                        # This indicates that a new file has been created
                        yield htmlnotice("File recreated")
                        break
                    # No data at this point of time.
                    time.sleep(0.5)
                except FileNotFoundError:
                    # The file has disappeared
                    inode = 0
                    yield htmlnotice("File disappeared")
                    break


def generator_pipe(args, renderer):
    """
    When sendling line by line, the load is very high for the browser.
    Therefore, we collect lines.
    """
    assert isinstance(args, list)

    def popen_thread():
        # See: https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8"
        )
        while True:
            output = process.stdout.readline()
            if output != "":
                _queue.put(renderer.render(output))
                continue

            exit_code = process.poll()
            if exit_code is not None:
                _queue.put(None)
                return

    _queue = queue.Queue()
    thread = threading.Thread(target=popen_thread)
    thread.start()

    yield htmlnotice(" ".join(args))
    while True:
        buffer = io.StringIO()
        while True:
            try:
                data = _queue.get(timeout=0.1)
                if data is None:
                    yield buffer.getvalue()
                    yield htmlnotice("exit")
                    return
                buffer.write(data)
            except queue.Empty:
                data = buffer.getvalue()
                if len(data) > 0:
                    yield data
                    buffer = io.StringIO()


def generator_pipe_simple(args, renderer):  # pylint: disable=unused-argument
    assert isinstance(args, list)
    # See: https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python
    process = subprocess.Popen(args, stdout=subprocess.PIPE, encoding="utf-8")
    while True:
        output = process.stdout.readline()
        if output != "":
            yield output
            continue
        child_terminated_rc = process.poll()
        if child_terminated_rc:
            return


@dataclass
class LogfileProvider:
    """
    May be derived.
    """

    # pylint: disable=invalid-name
    NO_FILE_SELECTED = ""
    LIVELOG_MOCK = "LIVELOG_MOCK"
    COMMAND_DMESG = "COMMAND_DMESG"
    COMMAND_PS = "COMMAND_PS"
    base_directory: pathlib.Path
    pattern: str

    def select_file(self, filename):  # pylint: disable=no-self-use
        return filename.suffix in (".ansi", ".txt")

    def get_filelist(self):
        for filename in self.base_directory.glob(self.pattern):
            if self.select_file(filename):
                yield str(filename.relative_to(self.base_directory))
        yield LogfileProvider.LIVELOG_MOCK
        yield LogfileProvider.COMMAND_DMESG
        yield LogfileProvider.COMMAND_PS

    def generator(self, filename):
        if filename in (None, LogfileProvider.NO_FILE_SELECTED):
            # yield '... please select a file ...'
            return

        if filename == LogfileProvider.LIVELOG_MOCK:
            for i in range(40):
                yield f"count="
                time.sleep(0.2)
                color = ("black", "black", "black", "blue", "red")[i % 5]
                yield f'<span style="color: {color}">{i}</span><br>'
            yield htmlnotice("EOF")
            return

        if filename == LogfileProvider.COMMAND_DMESG:
            args = shlex.split(
                "dmesg --follow --level=info --facility=kern --color=always"
            )
            renderer = Ansi2HtmlRenderer()
            yield from generator_pipe(args=args, renderer=renderer)
            return

        if filename == LogfileProvider.COMMAND_PS:
            args = shlex.split("ps a")
            renderer = LineCodeRenderer()
            yield from generator_pipe(args=args, renderer=renderer)
            return

        yield from generator_file(self.base_directory / filename)


class LivelogForm(FlaskForm):
    files = SelectField("Select File")
    reload = SubmitField("Reload Filelist", id="reload")
    submit = SubmitField("View File", id="view")


def htmlnotice(msg):
    return f'<span style="display:block; background-color: khaki; text-align: center">{msg}</span>'


class LiveLog:  # pylint: disable=too-few-public-methods
    def __init__(self, app, provider):
        self.provider = provider

        @app.route(
            "/livelog",
            methods=[
                "GET",
                "POST",
            ],
        )
        def livelog():  # pylint: disable=unused-variable
            if request.method == "GET":
                filename = request.args.get("filename")
                if request.args.get("view") == "1":
                    return render_template("livelog.html", filename=filename)

            form = LivelogForm()
            form.files.choices = list(provider.get_filelist())
            filename = LogfileProvider.NO_FILE_SELECTED
            if request.method == "GET":
                filename = request.args.get("filename")
            else:
                if form.validate_on_submit():
                    filename = form.files.data
            return render_template("livelog.html", form=form, filename=filename)

        @app.route(f"/livestream")
        def livestream():  # pylint: disable=unused-variable
            filename = request.args.get("filename")

            def generate():
                for msg in provider.generator(filename):
                    yield f"data: {msg}\n\n"

            return Response(generate(), mimetype="text/event-stream")
