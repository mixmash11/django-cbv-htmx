# utils/tools.py
import logging
from functools import wraps

from django.http import HttpResponse

logger = logging.getLogger(__name__)


def operation(op):
    """
    Logging for methods
    """
    def operation_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logging.info(f"START - {op}")
            try:
                return_val = func(*args, **kwargs)
            except Exception as func_e:
                logging.info(f"FAILED - {op}")
                logging.exception(f"EXCEPTION: {func_e}")
                raise
            logging.info(f"STOP - {op}")
            return return_val

        try:
            return wrapper
        except Exception:
            raise

    return operation_decorator


def superuser_required(func):
    """
    A test for Django views requiring the user to be a super user
    """
    @wraps(func)
    def test_user(request, *args, **kwargs):
        if request.user.is_superuser:
            return func(request, *args, **kwargs)
        else:
            return HttpResponse("Unauthorized", status=401)

    return test_user


def value_to_string_or_empty_string(value):
    if value:
        return str(value)
    return ""
