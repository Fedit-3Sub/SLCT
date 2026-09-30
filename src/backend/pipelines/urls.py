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
from .logic_api import LogicListView, LogicInvokeView, LogicSpecView, LogicFeditView

urlpatterns = [
    path('feditscraper/json', FedItScraperJsonView.as_view(), name='feditscraper-json'),
    path('pipelines/run', PipelineRunView.as_view(), name='pipelines-run'),
    path('pipelines/execute', PipelineExecuteView.as_view(), name='pipelines-execute'),
    path('pipelines/runs', PipelineRunListView.as_view(), name='pipelines-runs'),
    path('pipelines/runs/<int:pk>', PipelineRunDetailView.as_view(), name='pipelines-run-detail'),
    path('custom-nodes', CustomNodesView.as_view(), name='custom-nodes'),
    path('search', UnifiedSearchView.as_view(), name='unified-search'),
    path('logics', LogicListView.as_view(), name='logics'),
    path('logics/<str:uid>/invoke', LogicInvokeView.as_view(), name='logic-invoke'),
    path('logics/<str:uid>/spec', LogicSpecView.as_view(), name='logic-spec'),
    path('logics/<str:uid>/fedit', LogicFeditView.as_view(), name='logic-fedit'),
]
