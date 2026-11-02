from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

handler500 = "sigab.api.views.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("sigab.api.urls")),
    path(
        "entrar/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("sigab.urls")),
]
