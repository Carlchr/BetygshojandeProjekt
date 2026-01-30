import time
import logging
import secrets
from functools import wraps
from collections import defaultdict

from slowapi import Limiter
from slowapi.util import get_remote_address

# Skappar en "rate limiter" som spårar användare genom deras IP-address 
limiter = Limiter(key_func=get_remote_address)
login_attempts = defaultdict(list)