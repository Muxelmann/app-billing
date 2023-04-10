import random
import hashlib
from datetime import datetime, date

def optional_float(number: str) -> float | None:
    if number == '':
        return None
    try:
        return float(number)
    except:
        return None
    
def optional_int(number: str) -> int | None:
    if number == '':
        return None
    try:
        return int(number)
    except:
        return None
    
def randomstr(length: int = 8) -> str:
    return ''.join(['{:x}'.format(random.randint(0, 15)) for _ in range(length)])

def hexdigest(salt: str, raw_password: str) -> str:
    hashlib.sha256('{salt}{raw_password}'.format(
        salt = salt.encode('utf-8'),
        raw_password = raw_password.encode('utf-8')
    )).hexdigest()

def hash_password(raw_password: str) -> str:
    salt = hexdigest(randomstr(8), randomstr(8))[:16]
    hash = hexdigest(salt, raw_password)
    return f'{salt}:{hash}'

def date_to_int(date: datetime | date) -> int:
    if isinstance(date, datetime):
        date = date.date()
    return int(date.strftime('%Y%m%d'))
            
def int_to_date(date: int) -> date:
    return datetime.strptime(f'{date}', '%Y%m%d').date()