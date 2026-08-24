from django.urls import path
from .views import register_data,login_user

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import LogoutView
urlpatterns = [
    path("register",register_data),
    path("login",login_user),
    path("refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("account/logout/", LogoutView.as_view(), name="logout")
]



