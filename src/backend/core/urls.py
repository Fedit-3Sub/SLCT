from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Django Admin 한글 브랜딩
admin.site.site_header = "연합트윈 관리자"
admin.site.site_title = "연합트윈 관리자"
admin.site.index_title = "관리자 홈"

schema_view = get_schema_view(
    openapi.Info(
        title="연합트윈 백엔드 API",
        default_version='v1',
        description="프론트엔드와 연동되는 BPMN/LLM API 문서입니다.",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('bpmns.urls')),
    path('api/', include('llm.urls')),
    path('api/', include('digitaltwins.urls')),
    path('api/', include('pipelines.urls')),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='api-docs'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='api-redoc'),
    path('api/schema.json', schema_view.without_ui(cache_timeout=0), name='api-schema-json'),
]
