"""
URL configuration for DocChat project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.urls import include
from django.views.generic import RedirectView

from webapp import views

urlpatterns = [
    path('admin/users/', views.role_management, name='admin_roles_dashboard'),
    path('admin/users/<int:user_id>/edit/', views.edit_role, name='admin_edit_role'),
    path('admin/groups/', views.group_dashboard, name='group_dashboard'),
    path('admin/groups/<int:group_id>/edit/', views.edit_group, name='edit_group'),
    path('admin/groups/add/', views.add_group, name='add_group'),
    path("admin/create/", views.create_user, name="create_user"),
    path("admin/", admin.site.urls),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("upload/", views.upload_document, name="upload_document"),
    path("download/<int:doc_id>/", views.download_document, name="download_document"),
    path("auth/", include("webapp.urls")),
    path('documents/<int:doc_id>/view/', views.view_document, name='view_document'),
    path('documents/<int:doc_id>/delete/', views.delete_document, name='delete_document'),
    path('documents/<int:doc_id>/send/', views.send_document, name='send_document'),
    path('documents/<int:doc_id>/sign/', views.sign_document, name='sign_document'),
    path('documents/<int:doc_id>/verify/', views.verify_document, name='verify_document'),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),

]
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)