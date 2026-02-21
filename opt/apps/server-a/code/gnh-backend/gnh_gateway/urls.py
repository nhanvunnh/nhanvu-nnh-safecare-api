from django.urls import re_path

from gnh_gateway.views import GNHCreateView, GNHDeleteView, GNHDetailView, GNHListView, GNHLogsView, GNHSyncView, GNHUpdateView

urlpatterns = [
    re_path(r"^gets$", GNHListView.as_view()),
    re_path(r"^get$", GNHDetailView.as_view()),
    re_path(r"^create$", GNHCreateView.as_view()),
    re_path(r"^update$", GNHUpdateView.as_view()),
    re_path(r"^delete$", GNHDeleteView.as_view()),
    re_path(r"^sync$", GNHSyncView.as_view()),
    re_path(r"^logs$", GNHLogsView.as_view()),
]
