from http_client import do_request


def run_tests():
    import json

    def extract_json(resp):
        return json.loads(
            "".join([l for l in resp[0] if not l.startswith("//")])
        )

    def test(assertion, test):
        print("Test %s: %s" % ("passed" if assertion else "failed", test))
        if not assertion:
            raise AssertionError

    resp = extract_json(
        do_request(
            [
                "# comment",
                "# :a=barf",
                "GET http://httpbin.org/headers",
                "X-Hey: :a",
                "# comment",
            ],
            [],
        )
    )
    test(
        resp["headers"]["X-Hey"] == "barf",
        "Headers are passed with variable substitution.",
    )

    resp = extract_json(
        do_request(["# :a = barf", "GET http://httpbin.org/get?data=:a"], [])
    )
    test(
        resp["args"]["data"] == "barf",
        "GET data is passed with variable substitution.",
    )

    resp = extract_json(
        do_request(["POST http://httpbin.org/post", "some data"], [])
    )
    test(
        resp["data"] == "some data",
        "POST data is passed with variable substitution.",
    )

    resp = extract_json(
        do_request(["POST http://httpbin.org/post", "forma=a", "formb=b",], [])
    )
    test(resp["form"]["forma"] == "a", "POST form data is passed.")

    resp = extract_json(
        do_request(
            ["POST http://$global/post", "forma=a", "formb=b",],
            ["# $global = httpbin.org"],
        )
    )
    test(resp["form"]["forma"] == "a", "Global variables are substituted.")

    import os
    from tempfile import NamedTemporaryFile

    SAMPLE_FILE_CONTENT = "sample file content"

    temp_file = NamedTemporaryFile(delete=False)
    temp_file.write(SAMPLE_FILE_CONTENT)
    temp_file.close()
    resp = extract_json(
        do_request(
            [
                "POST http://httpbin.org/post",
                "forma=a",
                "formb=b",
                "formc=!file(%s)" % temp_file.name,
            ],
            [],
        )
    )
    test(
        resp["files"]["formc"] == SAMPLE_FILE_CONTENT,
        "Files given as path are sent properly.",
    )
    test(not "formc" in resp["form"], "File not included in form data.")
    os.unlink(temp_file.name)

    resp = extract_json(
        do_request(
            [
                "POST http://httpbin.org/post",
                "forma=a",
                "formb=b",
                "formc=!content(%s)" % SAMPLE_FILE_CONTENT,
            ],
            [],
        )
    )
    test(
        resp["files"]["formc"] == SAMPLE_FILE_CONTENT,
        "Files given as content are sent properly.",
    )

    resp = extract_json(
        do_request(
            ["POST http://httpbin.org/post", "c=!content(foo \\(bar\\))",], []
        )
    )
    test(
        resp["files"]["c"] == "foo (bar)",
        "Escaped parenthesis should be unescaped during request",
    )

