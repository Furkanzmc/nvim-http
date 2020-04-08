# Python
import json
import re
from os import getenv
from typing import List

# Third Party
import requests
from requests import exceptions

if not getenv("NVIM_LISTEN_ADDRESS"):
    IS_NEOVIM = True
    import pynvim

    nvim = pynvim.attach("socket", path=getenv("NVIM_LISTEN_ADDRESS"))
else:
    IS_NEOVIM = False
    import vim


def vim_eval(command: str):
    if IS_NEOVIM:
        return nvim.eval(command)
    else:
        return vim.eval(command)


def vim_command(command: str):
    if IS_NEOVIM:
        return nvim.command(command)
    else:
        return vim.command(command)


def vim_current_window():
    if IS_NEOVIM:
        return nvim.current.window()
    else:
        return vim.current.window


def vim_current_buffer():
    if IS_NEOVIM:
        return nvim.current.buffer()
    else:
        return vim.current.buffer


def vim_set_current_window(window):
    if IS_NEOVIM:
        return nvim.current.window(window)
    else:
        vim.current.window = window


def log_error(message: str):
    if IS_NEOVIM:
        nvim.command("echohl ErrorMsg")
        nvim.command("echomsg '{}'".format(message))
        nvim.command("echohl None")
    else:
        vim.command("echohl ErrorMsg")
        vim.command("echomsg '{}'".format(message))
        vim.command("echohl None")


METHOD_REGEX: re.Pattern = re.compile(
    "^(GET|POST|DELETE|PUT|HEAD|OPTIONS|PATCH) (.*)$"
)
HEADER_REGEX: re.Pattern = re.compile("^([^()<>@,;:\<>/\[\]?={}]+):\\s*(.*)$")
VAR_REGEX: re.Pattern = re.compile("^# ?(:[^: ]+)\\s*=\\s*(.+)$")

GLOBAL_VAR_REGEX: re.Pattern = re.compile("^# ?(\$[^$ ]+)\\s*=\\s*(.+)$")
FILE_REGEX: re.Pattern = re.compile("!((?:file)|(?:(?:content)))\((.+)\)")
JSON_REGEX: re.Pattern = re.compile("(javascript|json)$", re.IGNORECASE)

VERIFY_SSL = vim_eval("g:http_client_verify_ssl") == "1"
BUFFER_NAME = "__HTTP_Client_Response__"


def replace_vars(string: str, variables: dict):
    for var, val in variables.items():
        string = string.replace(var, val)
    return string


def is_comment(string: str):
    return string.startswith("#")


def do_request(block: List[str], buf):
    variables = dict(
        (m.groups() for m in (GLOBAL_VAR_REGEX.match(l) for l in buf) if m)
    )
    variables.update(
        dict((m.groups() for m in (VAR_REGEX.match(l) for l in block) if m))
    )

    block = [
        line for line in block if not is_comment(line) and line.strip() != ""
    ]

    if len(block) == 0:
        log_error("Request was empty.")
        return

    method_url = block.pop(0)
    method_url_match = METHOD_REGEX.match(method_url)
    if not method_url_match:
        log_error("Could not find method or URL!")
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

    if not VERIFY_SSL:
        from requests.packages.urllib3.exceptions import InsecureRequestWarning

        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    json_data = None
    if headers.get("Content-Type") == "application/json":
        json_data = json.loads(data)
        data = None

    try:
        response = requests.request(
            method,
            url,
            verify=VERIFY_SSL,
            headers=headers,
            data=data,
            files=files,
            json=json_data,
        )
    except (exceptions.RequestException, exceptions.MissingSchema) as ex:
        vim_command("echoerr '{}'".format(ex))

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
                ensure_ascii=vim_eval("g:http_client_json_escape_utf") == "1",
            )
        except ValueError:
            pass

    display = (
        response_body.split("\n")
        + ["", "// status code: %s" % response.status_code]
        + ["// %s: %s" % (k, v) for k, v in response.headers.items()]
    )

    return display, content_type


# Vim methods.


def vim_filetypes_by_content_type():
    return {
        "application/json": vim_eval("g:http_client_json_ft"),
        "application/xml": "xml",
        "text/html": "html",
    }


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


def open_scratch_buffer(contents, filetype):
    previous_window = vim_current_window()
    existing_buffer_window_id = vim_eval('bufwinnr("{}")'.format(BUFFER_NAME))

    if existing_buffer_window_id == "-1":
        if vim_eval("g:http_client_result_vsplit") == "1":
            split_cmd = "vsplit"
        else:
            split_cmd = "split"

        vim_command("rightbelow {} {}".format(split_cmd, BUFFER_NAME))
        vim_command("setlocal buftype=nofile nospell")
    else:
        vim_command("{}wincmd w".format(existing_buffer_window_id))

    vim_command("set filetype={}".format(filetype))
    write_buffer(contents, vim_current_buffer())

    if vim_eval("g:http_client_focus_output_window") != "1":
        vim_set_current_window(previous_window)


def do_request_from_buffer():
    win = vim_current_window()
    line_num = win.cursor[0] - 1
    block = find_block(win.buffer, line_num)
    result = do_request(block, win.buffer)
    if result:
        response, content_type = result
        vim_ft = vim_filetypes_by_content_type().get(content_type, "text")
        open_scratch_buffer(response, vim_ft)


def write_buffer(contents, buffer):
    if vim_eval("g:http_client_preserve_responses") == "1":
        if len(buffer):
            buffer[0:0] = [""]
        buffer[0:0] = contents
        vim_command("0")
    else:
        buffer[:] = contents
