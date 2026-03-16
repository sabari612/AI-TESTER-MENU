import json


def read_json_menu(file_bytes=None, text=None):
    if file_bytes is not None:
        text = file_bytes.decode("utf-8")
    if not text:
        raise ValueError("JSON input is empty.")
    return json.loads(text)

