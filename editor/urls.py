from django.urls import path
from .views import GanttView

autodiscover = True


urlpatterns = [
    path('editor', GanttView.as_view(), name='editor'),  # Maps /editor/ to AppsView
    # other URL patterns...
]
