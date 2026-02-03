from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'claims', views.ClaimViewSet, basename='claim')
router.register(r'policies', views.InsurancePolicyViewSet, basename='policy')
router.register(r'policy-documents', views.PolicyDocumentViewSet, basename='policy-document')
router.register(r'fraud-alerts', views.FraudAlertViewSet, basename='fraud-alert')
router.register(r'agent-tasks', views.AgentTaskViewSet, basename='agent-task')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('auth/register/', views.register, name='register'),
    path('auth/me/', views.current_user, name='current-user'),
    path('dashboard/', views.dashboard_summary, name='dashboard'),
    path('analytics/', views.analytics_report, name='analytics'),
    path('', include(router.urls)),
]
