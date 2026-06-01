from django.urls import path
from . import views

app_name = "bifrost"

urlpatterns = [
    path("", views.index, name="bifrost_home"),
]
