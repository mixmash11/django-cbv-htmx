# cbvhtmx\mixins.py
import logging

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.http.request import QueryDict

from .services import (
    ExportFileProfile,
    read_objects_into_xlsx,
    read_objects_into_csv,
)

logger = logging.getLogger(__name__)


class OrderingMixin:
    """
    A mixin with helpers for ordering the results of a ListView.

    Uses attributes:
    - querydict - the output from a Django QueryDict object read from the request
    - ordering - the field name which to order by

    The mixin reads the request URL to check for an "ordering" parameter.
    If the URL contains an "ordering" parameter the ENTIRE QueryDict is copied to the querydict attribute
    """

    querydict = None
    ordering = None

    def dispatch(self, request, *args, **kwargs):

        if "ordering" in request.GET:
            ordering = request.GET["ordering"]
            try:
                self.model._meta.get_field(ordering.strip("-"))
                self.ordering = ordering
                # registering a valid querydict
                # sets querydict field for easy usage in template (view.querydict)
                self.querydict = request.GET.urlencode()
            except FieldDoesNotExist:
                pass

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.querydict:
            # sets querydict field for easy usage in template (view.querydict)
            context["querydict"] = self.querydict
        elif self.ordering:
            query_dict = QueryDict(mutable=True)
            query_dict["ordering"] = self.ordering
            self.querydict = query_dict.urlencode()
            context["querydict"] = self.querydict

        return context


class FieldQueryMixin:
    """
    A mixin that queries specified fields for a list view

    Uses attributes:
    - querydict - the output from a Django QueryDict object read from the request
    - query - the decoded query
    - query_fields - a list of fields or query string (such as "fieldname__in")

    The mixin reads the request URL to check for an "q" parameter.
    If the URL contains an "q" parameter the ENTIRE QueryDict is copied to the querydict attribute

    Entries in the query_fields should be either of type string (the name of the model field or the query string).
    A string with a dunder (__) is assumed to be query string
    A string with a dunder and in (__in) is assumed to be a query string for use with a list object. When the query
    is constructed, the query value will be inserted into an empty list
    """

    querydict = None
    query = None
    query_fields = []

    def dispatch(self, request, *args, **kwargs):

        if "q" in request.GET:
            query = request.GET["q"]
            # only activates if the q parameter contains something
            if query.strip():
                self.querydict = request.GET.urlencode()
                self.query = query

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if self.query:

            queryset = super().get_queryset()

            q_filter = Q()
            for field_entry in self.query_fields:
                if isinstance(field_entry, str) and field_entry.__contains__("__in"):
                    q_filter |= Q(**{field_entry: [self.query]})
                elif isinstance(field_entry, str) and field_entry.__contains__("__"):
                    q_filter |= Q(**{field_entry: self.query})
                elif isinstance(field_entry, str):
                    icontains_str = f"{field_entry}__icontains"
                    q_filter |= Q(**{icontains_str: self.query})

            filtered_queryset = queryset.filter(q_filter).distinct()
            return filtered_queryset
        else:
            return super().get_queryset()


class TagsMixin:
    """
    A mixin that pre-fetches tags on a given queryset.

    Uses attribute:
    - tags_field: the name the model field to prefetch relative to the queryset.
    - tag_name_field: the name of the tag's model field that represents the tag

    The tags_field defaults to "tags" if the ListView doesn't have an attribute "tag_field"
    """

    tags_field = "tags"
    tag_name_field = "name"

    def get_queryset(self):
        return super().get_queryset().prefetch_related(self.tags_field)


class HxMixin:
    """
    A mixin for identifying if a (Template) View is receiving an HTMX request.

    Uses attributes:
    - hx: a boolean denoting whether the request is an HTMX request
    - hx_template: an attribute to specify an HTMX-specific template

    If a View specifies an "hx_template" attribute and the request is identified as an HTMX request, the specified
    template is loaded when the View is called
    """

    hx = False
    hx_template = None

    def dispatch(self, request, *args, **kwargs):
        if "HX-Request" in request.headers and request.headers["HX-Request"]:
            self.hx = True
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        if self.hx and self.hx_template:
            return self.hx_template
        else:
            return super().get_template_names()


class ExportMixin:
    """
    A mixin that returns files for ListViews
    """

    extension = None
    file_name = "Export"
    export_fields = []
    export_types = {}
    use_defaults = True
    _default_types = {
        "xlsx": ExportFileProfile(
            extension="xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_parser=read_objects_into_xlsx,
        ),
        "csv": ExportFileProfile(
            extension="csv", content_type="text/csv", file_parser=read_objects_into_csv
        ),
    }

    def get_file_name(self):
        combined_file_name = ".".join([self.file_name, self.extension])
        return combined_file_name

    def get_file_data(self, object_list):
        export_file_profile = self.export_types[self.extension]
        file_data = export_file_profile.file_parser(object_list, self.export_fields)
        return file_data

    def get_file_content_type(self):
        export_file_profile = self.export_types[self.extension]
        return export_file_profile.content_type

    def dispatch(self, request, *args, **kwargs):
        # add default types if user didn't specify one
        if self.use_defaults:
            for type_key, type_entry in self._default_types.items():
                if type_key not in self.export_types:
                    self.export_types[type_key] = type_entry

        if "extension" in self.kwargs:
            extension = self.kwargs["extension"]
            if extension not in self.export_types:
                raise Http404(f"Extension {extension} not supported.")
            self.extension = extension
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["file_name"] = self.get_file_name()
        context["file_data"] = self.get_file_data(context["object_list"])
        context["file_content_type"] = self.get_file_content_type()
        return context

    def render_to_response(self, context, **response_kwargs):
        headers = {
            "Content-Type": context["file_content_type"],
            "Content-Disposition": f'attachment; filename="{context["file_name"]}"',
        }

        response = HttpResponse(content=context["file_data"])
        for key, value in headers.items():
            response[key] = value

        return response


class SuperuserRequiredMixin(UserPassesTestMixin):
    """
    A mixin that verifies the user is a superuser.
    """

    def test_func(self):
        return self.request.user.is_superuser
