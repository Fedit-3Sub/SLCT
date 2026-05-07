from django.urls import path
from .views import BpmnListCreateView, BpmnRetrieveUpdateView

urlpatterns = [
    path('bpmns', BpmnListCreateView.as_view(), name='bpmn-list-create'),
    path('bpmns/<int:pk>', BpmnRetrieveUpdateView.as_view(), name='bpmn-detail'),
]
