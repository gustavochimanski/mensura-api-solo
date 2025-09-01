from datetime import datetime


def now_trimmed():
    return datetime.now().replace(microsecond=0)