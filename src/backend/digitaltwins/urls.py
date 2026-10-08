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
    TwinListView,
    TwinDetailView,
    TwinLatestView,
    TwinLinkageView,
)

urlpatterns = [
    path('twins', TwinListView.as_view(), name='twins'),
    path('twins/linkage', TwinLinkageView.as_view(), name='twin-linkage'),
    path('twins/<str:kind>/<str:a>/<str:b>', TwinDetailView.as_view(), name='twin-detail'),
    path('twins/<str:kind>/<str:a>/<str:b>/latest', TwinLatestView.as_view(), name='twin-latest'),
    path('digitaltwins', DigitalTwinListView.as_view(), name='digital-twins-list'),
    path('digitaltwins/logs', DigitalTwinLogsView.as_view(), name='digital-twins-logs'),
    path('digitaltwins/call', DigitalTwinCallView.as_view(), name='digital-twins-call'),
    path('fedit/objects', FeditObjectListView.as_view(), name='fedit-objects'),
    path('fedit/objects/latest', FeditObjectLatestView.as_view(), name='fedit-object-latest'),
    path('fedit/metadata', FeditMetadataView.as_view(), name='fedit-metadata'),
    path('fedit/metadata/<str:resource>', FeditMetadataResourceView.as_view(), name='fedit-metadata-resource'),
    path('fedit/objects/series', FeditObjectSeriesView.as_view(), name='fedit-object-series'),
]
