# cbvhtmx\services.py
import codecs
import csv
import io
import logging

from pandas.tests.io.excel.test_xlsxwriter import xlsxwriter

from .tools import operation

logger = logging.getLogger(__name__)


@operation("Read objects into CSV")
def read_objects_into_csv(query_set, export_fields):
    """
    Reads a list of Django model objects into a CSV file
    :param django.db.models.query.QuerySet query_set: set of Django model Objects
    :param list export_fields: list of ExportField objects
    :return: byte-string of the csv output
    """

    bytes_object = io.BytesIO()
    stream_writer = codecs.getwriter("utf-8")

    file_stream = stream_writer(bytes_object)
    field_names = [str(entry) for entry in export_fields]

    writer = csv.writer(file_stream)
    writer.writerow(field_names)

    for model_entry in query_set:

        value_list = get_value_list(export_fields, model_entry)
        writer.writerow(value_list)

    return bytes_object.getvalue()


@operation("Read objects into XLSX")
def read_objects_into_xlsx(query_set, export_fields):
    """
    Reads a list of Django model objects into a CSV file
    :param django.db.models.query.QuerySet query_set: set of Django model Objects
    :param list export_fields: list of ExportField objects
    :return: byte-string of the csv output
    """

    bytes_object = io.BytesIO()

    workbook = xlsxwriter.Workbook(bytes_object, {"in_memory": True})
    worksheet = workbook.add_worksheet()

    col_names = [str(entry) for entry in export_fields]

    bold = workbook.add_format({"bold": True})
    for col_num, col_name in enumerate(col_names):
        worksheet.write(0, col_num, col_name, bold)

    for row_num, model_entry in enumerate(query_set, start=1):
        value_list = get_value_list(export_fields, model_entry)
        worksheet.write_row(row_num, 0, value_list)

    workbook.close()

    return bytes_object.getvalue()


def get_value_list(export_fields, model_entry):
    """

    :param list export_fields: list of ExportField objects
    :param django.db.models.base.Model model_entry: Django Model instance
    :return: list of string values corresponding to each ExportField
    """
    value_list = [field_entry.parse_field(model_entry) for field_entry in export_fields]
    return value_list


class ExportField:
    def __init__(self, display_name, model_field=None, parser_function=None):
        self.display_name = display_name
        if model_field and parser_function:
            raise ValueError(
                "ExportField can use either model_field or parser_function, NOT both!"
            )
        elif model_field:
            if isinstance(model_field, str):
                self.model_field = model_field
                self.parser_function = None
            else:
                raise ValueError("ExportField attribute display_name must be a string!")
        elif parser_function:
            if callable(parser_function):
                self.parser_function = parser_function
                self.model_field = None
            else:
                raise ValueError(
                    "ExportField attribute parser_function must be a function!"
                )
        else:
            raise ValueError(
                "ExportField attribute(s) model_field and/or parser_function must be used!"
            )

    def __str__(self):
        return self.display_name

    def parse_field(self, model_entry):
        """
        Converts a Django Model object into a string for a given field and/or parser.

        Fields that return None/False will default to an empty string.
        If the parser is being used, returning None/False will default to an empty string.

        :param ExportField self:
        :param django.db.models.base.Model model_entry:
        :return: str
        """
        if self.model_field and not self.parser_function:
            field_value = getattr(model_entry, self.model_field, None)
            if field_value:
                field_string = str(field_value)
            else:
                field_string = ""
        elif self.parser_function:
            field_string = self.parser_function(model_entry)
            if not field_string:
                field_string = ""
        else:
            raise ValueError(f"Invalid ExportField: {self}")
        return field_string


class ExportFileProfile:
    def __init__(self, extension, content_type, file_parser):
        if isinstance(extension, str):
            self.extension = extension
        else:
            raise ValueError("ExportFileProfile attribute extension must be a string!")
        if isinstance(content_type, str):
            self.content_type = content_type
        else:
            raise ValueError(
                "ExportFileProfile attribute content_type must be a string!"
            )
        if callable(file_parser):
            self.file_parser = file_parser
        else:
            raise ValueError(
                "ExportFileProfile attribute file_parser must be a function!"
            )
