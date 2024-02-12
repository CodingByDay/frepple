from django.shortcuts import render
from importlib import import_module
import json
from mimetypes import guess_type
import multiprocessing
import os.path
from pathlib import Path
import re

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
class AppsView(View):
    template_name = "common/apps.html"  # assuming the template is located in common directory under templates
    reportkey = "common.apps"  # Define the reportkey attribute
    @classmethod
    @method_decorator(staff_member_required)
    def get(cls, request, *args, **kwargs):
      
        return render(
            request,
            cls.template_name,
            {
                "title": _("apps"),
                "edition": "Test",
                "reportkey": "test",
                "apps": "test",
                "superuser": request.user.is_superuser,
            },
        )
