from django.urls import path

from .admin_api import AgentRegistrationSecretView, ApiKeyDisableView, ApiKeyListCreateView
from .agent_api import AgentHeartbeatView, AgentJobsNextView, AgentRegisterView, AgentReportView
from .reports_api import ReportsExportView, ReportsSummaryView
from .requests_api import SmsMessageAllListView, SmsMessageListView, SmsRequestCreateView, SmsRequestDetailView
from .templates_api import TemplateApproveView, TemplateDetailView, TemplateListCreateView
from .views import HealthView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("admin/api-keys", ApiKeyListCreateView.as_view(), name="api-keys"),
    path("admin/api-keys/<str:key_id>/disable", ApiKeyDisableView.as_view(), name="api-key-disable"),
    path("admin/agent/registration-secret", AgentRegistrationSecretView.as_view(), name="agent-registration-secret"),
    path("templates", TemplateListCreateView.as_view(), name="templates"),
    path("templates/<str:template_id>", TemplateDetailView.as_view(), name="template-detail"),
    path("templates/<str:template_id>/approve", TemplateApproveView.as_view(), name="template-approve"),
    path("requests", SmsRequestCreateView.as_view(), name="requests-create"),
    path("requests/<str:request_id>", SmsRequestDetailView.as_view(), name="requests-detail"),
    path("messages", SmsMessageListView.as_view(), name="messages-list"),
    path("messages/all", SmsMessageAllListView.as_view(), name="messages-all"),
    path("agent/register", AgentRegisterView.as_view(), name="agent-register"),
    path("agent/heartbeat", AgentHeartbeatView.as_view(), name="agent-heartbeat"),
    path("agent/jobs/next", AgentJobsNextView.as_view(), name="agent-jobs"),
    path("agent/messages/report", AgentReportView.as_view(), name="agent-report"),
    path("reports/summary", ReportsSummaryView.as_view(), name="reports-summary"),
    path("reports/export.csv", ReportsExportView.as_view(), name="reports-export"),
]
