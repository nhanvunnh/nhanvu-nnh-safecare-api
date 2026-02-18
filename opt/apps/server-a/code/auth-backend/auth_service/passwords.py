from django.contrib.auth.hashers import check_password, make_password


def hash_password(raw_password: str) -> str:
    return make_password(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return check_password(raw_password, password_hash)
