from django.urls import path
from .views import (
    DigitalTwinListView,
    DigitalTwinLogsView,
    DigitalTwinCallView,
    FeditObjectListView,
    FeditObjectLatestView,
    FeditObjectSeriesView,
    FeditMetadataView,
    FeditMetadataResourceView,
)

urlpatterns = [
    path('digitaltwins', DigitalTwinListView.as_view(), name='digital-twins-list'),
    path('digitaltwins/logs', DigitalTwinLogsView.as_view(), name='digital-twins-logs'),
    path('digitaltwins/call', DigitalTwinCallView.as_view(), name='digital-twins-call'),
    path('fedit/objects', FeditObjectListView.as_view(), name='fedit-objects'),
    path('fedit/objects/latest', FeditObjectLatestView.as_view(), name='fedit-object-latest'),
    path('fedit/metadata', FeditMetadataView.as_view(), name='fedit-metadata'),
    path('fedit/metadata/<str:resource>', FeditMetadataResourceView.as_view(), name='fedit-metadata-resource'),
    path('fedit/objects/series', FeditObjectSeriesView.as_view(), name='fedit-object-series'),
]
