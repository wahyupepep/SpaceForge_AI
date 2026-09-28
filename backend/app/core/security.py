import re

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(postgres(?:ql)?(?:\+\w+)?://[^:/\s]+:)[^@\s]+(@)"),
)


def sanitized_error(error: Exception, max_length: int = 2000) -> str:
    value = f"{type(error).__name__}: {error}"
    value = SECRET_PATTERNS[0].sub("[REDACTED_API_KEY]", value)
    value = SECRET_PATTERNS[1].sub(r"\1[REDACTED]", value)
    value = SECRET_PATTERNS[2].sub(r"\1[REDACTED]\2", value)
    return value[:max_length]
