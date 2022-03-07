from django import template
from django.http.request import QueryDict

register = template.Library()


@register.filter(name="append_page", is_safe=True)
def append_page(value, arg):
    """
    Updates a QueryDict with a "page" parameter

    :param value: QueryDict or None
    :param arg: the page number to put in
    :return: the output from a QueryDict
    """
    if value:
        query_dict = QueryDict(value, mutable=True)

    else:
        query_dict = QueryDict(mutable=True)

    query_dict["page"] = arg
    return query_dict.urlencode()


@register.filter(name="append_ordering", is_safe=True)
def append_ordering(value, arg):
    """
    Updates a QueryDict with a "ordering" parameter

    :param value: QueryDict or None
    :param arg: the value for the "ordering" parameter
    :return: the output from a QueryDict
    """
    if value:
        query_dict = QueryDict(value, mutable=True)

    else:
        query_dict = QueryDict(mutable=True)

    if "ordering" in query_dict and query_dict["ordering"] == arg:
        query_dict["ordering"] = f"-{arg}"
    else:
        query_dict["ordering"] = arg

    return query_dict.urlencode()


@register.filter(name="drop_q", is_safe=True)
def drop_q(value):
    """
    Removes the current "q" parameter from a QueryDict if it exists and returns a parameter string if any other
    parameters are defined.

    IMPORTANT: If there are more parameters than q, the string given back contains the "?" AND the QueryDict output

    :param value: QueryDict
    :return: The outpu
    """
    if value:
        query_dict = QueryDict(value, mutable=True)

    else:
        return ""

    if "q" in query_dict:
        query_dict.pop("q")

    if len(query_dict) < 1:
        return ""

    return f"?{query_dict.urlencode()}"


@register.filter(name="get_q", is_safe=True)
def get_q(value):
    """
    Reads the "q" parameter from a QueryDict, if one exists. Otherwise it returns the empty string.
    :param value:
    :return:
    """
    if value:
        query_dict = QueryDict(value)

        if "q" in query_dict:
            return query_dict["q"]

    return ""
