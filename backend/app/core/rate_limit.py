from slowapi import Limiter

from app.core.client_ip import get_client_ip
from app.core.config import get_settings


limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["200/minute"],
    storage_uri=get_settings().rate_limit_storage_uri,
)
