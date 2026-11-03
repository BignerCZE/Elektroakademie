"""Cookie preferences: signed, anonymous and recorded without IP addresses."""
import json
import uuid
from datetime import timedelta
from django.conf import settings
from django.core import signing
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from .models import CookieConsent

VERSION = "2026-11-03"
AGE = 60 * 60 * 24 * 180
COOKIE = "ea_consent"

def preferences(request):
    try:
        value = json.loads(request.get_signed_cookie(COOKIE, salt=COOKIE, max_age=AGE))
        if value["version"] != VERSION:
            return None
        return value
    except (signing.BadSignature, ValueError, KeyError, TypeError):
        return None

def cookie_context(request):
    name = getattr(request.resolver_match, "url_name", "")
    public = {"index", "courses", "register", "course_selector"}
    measurement_id = settings.GA4_MEASUREMENT_ID
    order_created = name == "order_payment_simulation" and request.session.pop("analytics_order_created", False)
    if order_created:
        public.add("order_payment_simulation")
    return {"cookie_config": {
        "version": VERSION, "preferences": preferences(request),
        "measurementId": measurement_id if name in public and not request.user.is_staff else "",
        "page": name if name in public else "",
        "orderCreated": bool(order_created),
    }}

@ensure_csrf_cookie
def consent_settings(request):
    return render(request, "courses/cookies.html")

@require_POST
def save_consent(request):
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict) or any(type(data.get(k)) is not bool for k in ("analytics", "media")):
            raise ValueError
    except (ValueError, TypeError, UnicodeDecodeError):
        return JsonResponse({"error": "Neplatná volba cookies."}, status=400)
    previous = preferences(request)
    identifier = previous["id"] if previous else str(uuid.uuid4())
    CookieConsent.objects.filter(created_at__lt=timezone.now()-timedelta(days=365)).delete()
    CookieConsent.objects.create(identifier=identifier, version=VERSION,
                                 analytics=data["analytics"], media=data["media"])
    value = {"id": identifier, "version": VERSION, "analytics": data["analytics"], "media": data["media"]}
    response = JsonResponse(value)
    response.set_signed_cookie(COOKIE, value=json.dumps(value), salt=COOKIE,
        max_age=AGE, secure=request.is_secure(), httponly=True, samesite="Lax")
    response["Cache-Control"] = "no-store"
    return response
