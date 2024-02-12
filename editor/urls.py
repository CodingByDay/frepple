from django.urls import path
from .views import AppsView

autodiscover = True


urlpatterns = [
    path('editor/', AppsView.as_view(), name='editor'),  # Maps /editor/ to AppsView
    # other URL patterns...
]
