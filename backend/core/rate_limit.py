from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter with remote address key
# This will limit requests based on the client's IP address
limiter = Limiter(key_func=get_remote_address)
