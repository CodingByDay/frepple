from django.shortcuts import render
from importlib import import_module
import json
from mimetypes import guess_type
import multiprocessing
import os.path
from pathlib import Path
from django.db.models import Q
import re
from freppledb.input.models import (
    Item,
    Resource,
    Operation,
    Location,
    SetupMatrix,
    SetupRule,
    Skill,
    ResourceSkill,
    OperationPlan,
    OperationPlanResource,
)
from django.core import management
from django.core.paginator import Paginator
from django.http import (
    JsonResponse,
    HttpResponseNotAllowed,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import (
    validate_password,
    get_password_validators,
    password_validators_help_text_html,
)
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.db import DEFAULT_DB_ALIAS
from django.db.models.expressions import RawSQL
from django.urls import reverse, resolve
from django import forms
from django.template import Template
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from django.utils.text import capfirst
from django.contrib.auth.models import Group
from django.utils import translation
from django.conf import settings
import requests
from django.http import (
    Http404,
    HttpResponseRedirect,
    HttpResponse,
    HttpResponseServerError,
)
from django.shortcuts import render
from django.views import static
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_variables
from django.views.generic.base import View
from freppledb.common.auth import getWebserviceAuthorization

class GanttView(View):
    template_name = "editor/gantt.html"  
    @classmethod
    @method_decorator(staff_member_required)
    def get(cls, request, *args, **kwargs):
        exp = 0
        try:
            exp = int(request.GET.get("exp", "3"))
        except Exception:
            exp = 3
        if exp > 7:
            exp = 7

        token = getWebserviceAuthorization (
                user=request.user.username, exp=exp * 86400, database=request.database
        )

        base_url = request.scheme + "://" + request.get_host()
        api_url = base_url + "/api/input/operationplanresource/"

        try:
            response = requests.get(api_url, headers={'Authorization': 'Bearer ' + token})
            response.raise_for_status()  # Raise an exception for HTTP errors
            operation_plan_resources = response.json()
        except requests.RequestException as e:
            # Handle request exceptions, such as network errors or invalid responses
            operation_plan_resources = []

        return render(
            request,
            cls.template_name,
            {
                "title": _("Visual editor"),
                "edition": "editor",
                "superuser": request.user.is_superuser,
                "operation_plan_resources": operation_plan_resources,
            },
        )