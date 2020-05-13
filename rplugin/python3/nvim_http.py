# Python
import json
import re
from typing import List
from datetime import datetime, timedelta

# pynvim
import pynvim
from pynvim import Nvim

# requests
import requests
from requests import exceptions


METHOD_REGEX: re.Pattern = re.compile(
    "^(GET|POST|DELETE|PUT|HEAD|OPTIONS|PATCH) (.*)$"
)
HEADER_REGEX: re.Pattern = re.compile("^([^()<>@,;:\<>/\[\]?={}]+):\\s*(.*)$")
VAR_REGEX: re.Pattern = re.compile("^# ?(:[^: ]+)\\s*=\\s*(.+)$")

GLOBAL_VAR_REGEX: re.Pattern = re.compile("^# ?(\$[^$ ]+)\\s*=\\s*(.+)$")
FILE_REGEX: re.Pattern = re.compile("!((?:file)|(?:(?:content)))\((.+)\)")
JSON_REGEX: re.Pattern = re.compile("(javascript|json)$", re.IGNORECASE)

BUFFER_NAME: str = "__NVIM_HTTP_Response__"


def replace_vars(string: str, variables: dict):
    for var, val in variables.items():
        string = string.replace(var, val)

    return string


def is_comment(string: str) -> bool:
    return string.startswith("#")


def find_block(buf, line_num):
    length = len(buf)
    is_buffer_terminator = lambda s: s.strip() == ""

    block_start = line_num
    while block_start > 0 and not is_buffer_terminator(buf[block_start]):
        block_start -= 1

    block_end = line_num
    while block_end < length and not is_buffer_terminator(buf[block_end]):
        block_end += 1

    return buf[block_start : block_end + 1]


@pynvim.plugin
class HttpPlugin(object):
    def __init__(self, vim):
        self.vim: Nvim = vim
        self.options = {
            "application/json": "javascript",
            "application/xml": "xml",
            "text/html": "html",
        }
        self.request_in_progress = False

    @pynvim.command("SendHttpRequest", sync=False)
    def command_handler(self):
        win: int = self.vim.current.window
        line_num: int = win.cursor[0] - 1
        block = find_block(win.buffer, line_num)

        self.request_in_progress = True
        self.vim.command("let g:nvim_http_request_in_progress = v:true")
        self.vim.command("doautocmd User NvimHttpRequestStarted")

        try:
            result = self.do_request(block, win.buffer)
        except exceptions.MissingSchema:
            self.log_error("URL is missing schema.")
            return
        except exceptions.InvalidSchema:
            self.log_error("URL is has invalid schema.")
            return
        except exceptions.InvalidURL:
            self.log_error("URL is invalid.")
            return
        except exceptions.ConnectionError:
            self.log_error("Cannot connect to host.")
            return
        except (
            exceptions.Timeout,
            exceptions.ConnectTimeout,
            exceptions.ReadTimeout,
        ):
            self.log_error("Connection timed out.")
            return
        except (exceptions.RequestException,) as ex:
            error_msg: str = ex.response.content if ex.response else "Unspecified."
            self.open_scratch_buffer(
                "Error sending request: {}".format(error_msg), "text"
            )
            return
        finally:
            self.request_in_progress = False
            self.vim.command("let g:nvim_http_request_in_progress = v:false")
            self.vim.command("doautocmd User NvimHttpRequestEnded")

        if result:
            response, content_type = result
            vim_ft = self.options.get(content_type, "text")
            self.open_scratch_buffer(response, vim_ft)

    @pynvim.function("NvimHttpRequestInProgress", sync=True)
    def function_handler(self, args) -> bool:
        return self.request_in_progress

    def do_request(self, block: List[str], buf):
        variables = dict(
            (m.groups() for m in (GLOBAL_VAR_REGEX.match(l) for l in buf) if m)
        )
        variables.update(
            dict((m.groups() for m in (VAR_REGEX.match(l) for l in block) if m))
        )

        block = [
            line
            for line in block
            if not is_comment(line) and line.strip() != ""
        ]

        if len(block) == 0:
            self.log_error("Request was empty.")
            return

        method_url = block.pop(0)
        method_url_match = METHOD_REGEX.match(method_url)
        if not method_url_match:
            self.log_error("Could not find method or URL!")
            return

        method, url = method_url_match.groups()
        url = replace_vars(url, variables)
        url = url.strip()

        headers = {}
        while len(block) > 0:
            header_match = HEADER_REGEX.match(block[0])
            if header_match:
                block.pop(0)
                header_name, header_value = header_match.groups()
                headers[header_name] = replace_vars(header_value, variables)
            else:
                break

        data = [replace_vars(l, variables) for l in block]
        files = None
        if all(["=" in l for l in data]):
            # Form data: separate entries into data dict, and files dict
            key_value_pairs = dict([l.split("=", 1) for l in data])

            def to_file(expr):
                type, arg = FILE_REGEX.match(expr).groups()
                arg = arg.replace("\\(", "(").replace("\\)", ")")
                return open(arg, "rb") if type == "file" else (arg)

            files = dict(
                [
                    (k, to_file(v))
                    for (k, v) in key_value_pairs.items()
                    if FILE_REGEX.match(v)
                ]
            )
            data = dict(
                [
                    (k, v)
                    for (k, v) in key_value_pairs.items()
                    if not FILE_REGEX.match(v)
                ]
            )
        else:
            # Straight data: just send it off as a string.
            data = "\n".join(data)

        json_data = None
        if headers.get("Content-Type") == "application/json":
            json_data = json.loads(data)
            data = None

        request_start_date: datetime = datetime.now()
        response = requests.request(
            method,
            url,
            headers=headers,
            data=data,
            files=files,
            json=json_data,
        )
        request_end_date: datetime = datetime.now()
        request_duration: timedelta = request_end_date - request_start_date

        content_type = response.headers.get("Content-Type", "").split(";")[0]

        response_body = response.text
        if JSON_REGEX.search(content_type):
            content_type = "application/json"
            try:
                response_body = json.dumps(
                    json.loads(response.text),
                    sort_keys=True,
                    indent=2,
                    separators=(",", ": "),
                    ensure_ascii=self.vim.eval("g:nvim_http_json_escape_utf")
                    == "1",
                )
            except ValueError:
                pass

        display = (
            response_body.split("\n")
            + ["", "// Status Code: {}".format(response.status_code)]
            + ["// %s: %s" % (k, v) for k, v in response.headers.items()]
            + ["-----"]
            + [
                "// Request Start Date: {}".format(
                    request_start_date.isoformat()
                ),
            ]
            + ["// Request End Date: {}".format(request_end_date.isoformat())]
            + [
                "// Request Duration: {} Seconds".format(
                    request_duration.total_seconds()
                )
            ]
        )

        return display, content_type

    def write_buffer(self, contents, buffer):
        if self.vim.eval("g:nvim_http_preserve_responses") == "1":
            if len(buffer):
                buffer[0:0] = [""]
            buffer[0:0] = contents
            self.vim.command("0")
        else:
            buffer[:] = contents

    def log_error(self, message: str):
        self.vim.command("echohl ErrorMsg")
        self.vim.command("echo '[nvim-http] {}'".format(message))
        self.vim.command("echohl None")

    def open_scratch_buffer(self, contents: str, filetype: str):
        previous_window: int = self.vim.current.window
        existing_buffer_window: int = self.vim.eval(
            'bufwinnr("{}")'.format(BUFFER_NAME)
        )

        if existing_buffer_window == -1:
            if self.vim.eval("g:nvim_http_result_vsplit") == 1:
                split_cmd: str = "vsplit"
            else:
                split_cmd: str = "split"

            self.vim.command("rightbelow {} {}".format(split_cmd, BUFFER_NAME))
            self.vim.command("setlocal buftype=nofile nospell")
        else:
            self.vim.command("{}wincmd w".format(existing_buffer_window))

        self.vim.command("set filetype={}".format(filetype))
        self.write_buffer(contents, self.vim.current.buffer)

        if self.vim.eval("g:nvim_http_focus_output_window") != "1":
            self.vim.current.window = previous_window
