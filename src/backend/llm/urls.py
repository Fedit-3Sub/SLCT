from django.urls import path
from .views import LlmConfigsView, LlmConfigDetailView, LlmLogsView, LlmCopilotView

urlpatterns = [
    path('llm/configs', LlmConfigsView.as_view(), name='llm-configs'),
    path('llm/configs/<int:pk>', LlmConfigDetailView.as_view(), name='llm-config-detail'),
    path('llm/logs', LlmLogsView.as_view(), name='llm-logs'),
    path('llm/copilot', LlmCopilotView.as_view(), name='llm-copilot'),
]
