from django.urls import path
from .views import (
    FedItScraperJsonView,
    PipelineRunView,
    PipelineExecuteView,
    PipelineRunListView,
    PipelineRunDetailView,
    CustomNodesView,
    UnifiedSearchView,
)

urlpatterns = [
    path('feditscraper/json', FedItScraperJsonView.as_view(), name='feditscraper-json'),
    path('pipelines/run', PipelineRunView.as_view(), name='pipelines-run'),
    path('pipelines/execute', PipelineExecuteView.as_view(), name='pipelines-execute'),
    path('pipelines/runs', PipelineRunListView.as_view(), name='pipelines-runs'),
    path('pipelines/runs/<int:pk>', PipelineRunDetailView.as_view(), name='pipelines-run-detail'),
    path('custom-nodes', CustomNodesView.as_view(), name='custom-nodes'),
    path('search', UnifiedSearchView.as_view(), name='unified-search'),
]
