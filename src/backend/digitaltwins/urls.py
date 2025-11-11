from django.urls import path
from .views import DigitalTwinListView, DigitalTwinLogsView, DigitalTwinCallView

urlpatterns = [
    path('digitaltwins', DigitalTwinListView.as_view(), name='digital-twins-list'),
    path('digitaltwins/logs', DigitalTwinLogsView.as_view(), name='digital-twins-logs'),
    path('digitaltwins/call', DigitalTwinCallView.as_view(), name='digital-twins-call'),
]
