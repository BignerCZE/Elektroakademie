from functools import wraps

from django.http import HttpResponseBadRequest


CONTACT_ONLY_COURSES = frozenset({"6", "7"})


def prevent_contact_only_course_order(view_func):
    """Reject direct standard-order POSTs for courses handled via contact."""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if (
            request.method == "POST"
            and request.POST.get("selected_course") in CONTACT_ONLY_COURSES
        ):
            return HttpResponseBadRequest(
                "Toto školení aktuálně probíhá individuální formou."
            )

        return view_func(request, *args, **kwargs)

    return wrapped
