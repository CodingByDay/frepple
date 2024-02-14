from django.urls import path, re_path
from .views import views, capacity
from . import serializers
autodiscover = True


urlpatterns = [
    path('editor', views.GanttView.as_view(), name='editor'),  # Maps /editor/ to AppsView
    # other URL patterns...
    re_path(
    r"^editor/operationplanresource/resource/(.+)/$",
        capacity.EditorDetail.as_view(),
        name="input_operationplanresource_plandetail",
    ),     
    re_path(
        r"^editor/operationplanresource/$",
        capacity.EditorDetail.as_view(),
        name="input_operationplanresource_plan",
    ),  
	re_path (
	    r"^editor/operationplanresource/$",
	    serializers.OperationPlanResourceAPI.as_view(),
	),
      
    re_path (
        r"^editor/operationplanresource/(?P<pk>(.+))/$",
        serializers.OperationPlanResourcedetailAPI.as_view(),
    ),
]
