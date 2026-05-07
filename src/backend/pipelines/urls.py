from django.urls import path
from .views import FedItScraperJsonView, PipelineRunView, CustomNodesView, UnifiedSearchView

urlpatterns = [
    path('feditscraper/json', FedItScraperJsonView.as_view(), name='feditscraper-json'),
    path('pipelines/run', PipelineRunView.as_view(), name='pipelines-run'),
    path('custom-nodes', CustomNodesView.as_view(), name='custom-nodes'),
    path('search', UnifiedSearchView.as_view(), name='unified-search'),
]
