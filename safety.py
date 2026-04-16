from functools import wraps
from collections import defaultdict

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Denna fil konfigurerar rate limiting för applikationen.
# Limiter används för att skydda känsliga rutter mot brute-force och överbelastning.
limiter = Limiter(key_func=get_remote_address)