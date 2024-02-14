from django.urls import path, re_path
from .views.views import GanttView

autodiscover = True


urlpatterns = [
    path('editor', GanttView.as_view(), name='editor'),  # Maps /editor/ to AppsView
    # other URL patterns...
    re_path(
    r"^data/input/operationplanresource/resource/(.+)/$",
        views.ResourceDetail.as_view(),
        name="input_operationplanresource_plandetail",
    ),       
	re_path (
	    r"^api/input/operationplanresource/$",
	    serializers.OperationPlanResourceAPI.as_view(),
	),
    re_path (
        r"^api/input/operationplanresource/$",
        serializers.OperationPlanResourceAPI.as_view(),
    ),       
    re_path (
        r"^api/input/operationplanresource/(?P<pk>(.+))/$",
        serializers.OperationPlanResourcedetailAPI.as_view(),
    ),
]
