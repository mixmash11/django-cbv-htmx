# computer_management/views.py
import datetime

from django.contrib.auth.decorators import user_passes_test
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from .forms import ComputerForm, RechnerFileForm
from .models import Computer, ComputerNameChange
from .services import (
    import_updated_computer_excel,
    parse_tags,
)
from ..cbvhtmx.mixins import (
    OrderingMixin,
    SuperuserRequiredMixin,
    TagsMixin,
    HxMixin,
    FieldQueryMixin,
    ExportMixin,
)
from ..cbvhtmx.services import ExportField
from ..school_management.models import Schule


class SchuleFilterMixin:
    queryset = None
    scope = "MTK"
    schule = None
    schul_abb = None

    def dispatch(self, request, *args, **kwargs):
        if "schule" in self.kwargs:
            try:
                self.schule = Schule.objects.get(kuerzel=self.kwargs["schule"])
            except Schule.DoesNotExist:
                raise Http404("Keine Schule mit diesen Kuerzel.")
            self.scope = self.schule.kuerzel
            self.schul_abb = self.schule.kuerzel
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if self.schule:
            self.queryset = Computer.objects.filter(schule=self.schule).select_related(
                "schule"
            )
        else:
            self.queryset = Computer.objects.all().select_related("schule")

        return super().get_queryset()

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context["school_abb_list"] = Schule.objects.distinct("kuerzel")
        return context


class ComputerListView(
    FieldQueryMixin, SchuleFilterMixin, HxMixin, OrderingMixin, TagsMixin, ListView
):
    model = Computer
    ordering = "computer_name"
    paginate_by = 100
    hx_template = "computer_management/htmx/computer_list.html"
    query_fields = [
        "computer_name",
        "function",
        "hw_model",
        "mac_address",
        "os",
        "serial",
        "tags__name__in",
    ]


class ComputerDetailView(HxMixin, DetailView):
    model = Computer
    hx_template = "computer_management/htmx/computer_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        computer_name_changes = ComputerNameChange.objects.filter(
            computer=self.object.pk
        )
        context["computer_name_changes"] = computer_name_changes
        return context


class HTMXComputerDetailView(HxMixin, DetailView):
    model = Computer
    template_name = "computer_management/htmx/computer_detail.html"

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class ComputerCreateView(SuperuserRequiredMixin, HxMixin, CreateView):
    model = Computer
    form_class = ComputerForm
    action = "add"
    action_text = "hinzufügen"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class ComputerUpdateView(SuperuserRequiredMixin, HxMixin, UpdateView):
    model = Computer
    form_class = ComputerForm
    action = "update"
    action_text = "verwalten"


class HTMXComputerUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Computer
    form_class = ComputerForm
    action = "verwalten"
    template_name = "computer_management/htmx/computer-form.html"

    def get_success_url(self):
        return reverse_lazy(
            "rechner:detail",
            kwargs={"schule": self.kwargs["schule"], "slug": self.kwargs["slug"]},
        )


class ComputerExportListView(
    ExportMixin, FieldQueryMixin, SchuleFilterMixin, OrderingMixin, TagsMixin, ListView
):
    model = Computer
    ordering = "computer_name"
    query_fields = [
        "computer_name",
        "function",
        "hw_model",
        "mac_address",
        "os",
        "serial",
        "tags__name__in",
    ]
    export_fields = [
        ExportField(display_name="Rechner", model_field="computer_name"),
        ExportField(display_name="Schule", model_field="schule"),
        ExportField(display_name="Betriebsystem", model_field="os"),
        ExportField(display_name="Model", model_field="hw_model"),
        ExportField(display_name="MAC Adresse", model_field="mac_address"),
        ExportField(display_name="Funktion", model_field="function"),
        ExportField(display_name="Gebäude", model_field="building"),
        ExportField(display_name="Etage", model_field="floor"),
        ExportField(display_name="Raum", model_field="room"),
        ExportField(display_name="VM", model_field="virtual"),
        ExportField(display_name="Seriennummer", model_field="serial"),
        ExportField(
            display_name="Kaufdatum",
            model_field="purchase_date",
        ),
        ExportField(display_name="Tags", parser_function=parse_tags),
    ]

    def get_file_name(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        return f"Rechner_{timestamp}.{self.extension}"


def get_computers(schule):
    if schule:
        try:
            schule = Schule.objects.get(kuerzel=schule)
        except Schule.DoesNotExist:
            raise Http404("Keine Schule mit diesen Kuerzel.")
        computers = (
            Computer.objects.filter(schule=schule)
            .select_related("schule")
            .order_by("computer_name")
        )
    else:
        computers = (
            Computer.objects.all().select_related("schule").order_by("computer_name")
        )
    return computers


def md_computers(request, schule=None):
    computers = get_computers(schule)

    if schule:
        title = f"{schule}_Rechner"
        header = f"{schule} Rechner"
    else:
        title = f"MTK_Rechner"
        header = f"MTK Rechner"

    filename = f"{title}.md"

    response = HttpResponse(content_type="text/markdown")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    response.write(f"# {header}\n\n")

    for computer in computers:
        response.write(f"-[ ] {computer}\n")

    return response


@user_passes_test(lambda u: u.is_superuser)
def import_computers(request):
    if request.method == "POST":
        form = RechnerFileForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES["file"].read()
            name_change = form.cleaned_data["name_change"]
            import_updated_computer_excel(excel_file, name_change=name_change)
            return HttpResponseRedirect("erfolg")
    else:
        form = RechnerFileForm()

    return render(request, "computer_management/import_computers.html", {"form": form})
