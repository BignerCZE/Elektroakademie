"""Keep the existing quiz workflow inside a same-origin iframe when requested."""
from functools import wraps
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from django.shortcuts import render
from django.urls import resolve, Resolver404


def quiz_popup_navigation(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        if request.GET.get('popup') != '1':
            return response
        location = response.get('Location')
        if location and response.status_code in (301, 302, 303):
            parts = urlsplit(location)
            try:
                name = resolve(parts.path).url_name if not parts.netloc and not parts.scheme else None
            except Resolver404:
                name = None
            if name in ('dashboard', 'quiz_attempt_detail'):
                response = render(request, 'courses/quiz_popup_event.html', {
                    'quiz_event': {'type': 'ea-quiz-left' if name == 'dashboard' else 'ea-quiz-completed',
                                   'review_url': location if name == 'quiz_attempt_detail' else ''},
                })
            elif name == 'quiz_question':
                query = dict(parse_qsl(parts.query, keep_blank_values=True))
                query['popup'] = '1'
                response['Location'] = urlunsplit(parts._replace(query=urlencode(query)))
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Cache-Control'] = 'private, no-store'
        return response
    return wrapped
