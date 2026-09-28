from enum import Enum


class DatabaseChangeType(str, Enum):
    REUSE = "REUSE"
    ALTER = "ALTER"
    NEW = "NEW"


class APIChangeType(str, Enum):
    REUSE = "REUSE"
    MODIFY = "MODIFY"
    NEW = "NEW"
    DEPRECATED = "DEPRECATED"


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
