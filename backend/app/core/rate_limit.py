from slowapi import Limiter
from slowapi.util import get_remote_address


def get_client_ip(request) -> str:
    return get_remote_address(request)


limiter = Limiter(key_func=get_client_ip, default_limits=["200/minute"], storage_uri="memory://")
