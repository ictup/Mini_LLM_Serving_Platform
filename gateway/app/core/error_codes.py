ERROR_CODE_HEADER = "X-Gateway-Error-Code"
UNKNOWN_ERROR_CODE = "unknown"


def error_code_headers(code: str, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
    headers = {ERROR_CODE_HEADER: code}
    if extra_headers:
        headers.update(extra_headers)
    return headers
