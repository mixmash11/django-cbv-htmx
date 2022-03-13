from django.forms.widgets import DateInput


class DateNoneInput(DateInput):
    """
    If there's a value, format it, otherwise return None.
    """
    def format_value(self, value):
        if value:
            return super().format_value(value)
        return None
