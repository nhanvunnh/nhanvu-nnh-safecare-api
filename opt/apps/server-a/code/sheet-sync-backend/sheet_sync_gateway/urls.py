from django.urls import re_path

from sheet_sync_gateway.views import SyncAppGetView, SyncAppListView, SyncAppUpsertView, SyncJobRunView, SyncLogsListView

urlpatterns = [
    re_path(r"^apps/upsert$", SyncAppUpsertView.as_view()),
    re_path(r"^apps/get$", SyncAppGetView.as_view()),
    re_path(r"^apps/list$", SyncAppListView.as_view()),
    re_path(r"^jobs/run$", SyncJobRunView.as_view()),
    re_path(r"^logs/list$", SyncLogsListView.as_view()),
]
