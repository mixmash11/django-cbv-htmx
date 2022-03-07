from django.forms.widgets import DateInput


class GermanDateInput(DateInput):
    def format_value(self, value):
        if value:
            return value
        return None
