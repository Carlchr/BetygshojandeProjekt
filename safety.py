import time
import logging
import secrets
from functools import wraps
from collections import defaultdict

from slowapi import Limiter
from slowapi.util import get_remote_address
from itsdangerous import URLSafeTimedSerializer

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address, default_limits=["5 per minute", "100 per hour"])