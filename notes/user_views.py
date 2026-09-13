"""
User management.

  * Administrators: list users, create a user (with a set password and group),
    and reset any user's password at any time.
  * Every logged-in user: change their own password (needs current password).

No email/SMTP required — password setting is done directly by an admin or by
the user themselves. (An email-based "forgot password" flow can be added later
if you configure SMTP; see README.)
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.models import Group, User
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from . import permissions
from .forms import AdminUserCreateForm
from .models import GROUP_ADMIN


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not permissions.is_admin(request.user):
            return HttpResponseForbidden("Administrators only.")
        return view(request, *args, **kwargs)
    return wrapper


def _style(form):
    """Give auth forms the app input class."""
    for f in form.fields.values():
        f.widget.attrs.setdefault("class", "in")
    return form


@admin_required
def user_list(request):
    locked = _locked_usernames()
    users = User.objects.all().order_by("username").prefetch_related("groups")
    rows = [{
        "u": u,
        "groups": ", ".join(u.groups.values_list("name", flat=True)) or "—",
        "is_admin": permissions.is_admin(u),
        "locked": u.username in locked,
    } for u in users]
    return render(request, "notes/users.html", {"rows": rows})


def _locked_usernames():
    """Usernames currently locked out by django-axes."""
    try:
        from axes.models import AccessAttempt
        from django.conf import settings
        limit = getattr(settings, "AXES_FAILURE_LIMIT", 5)
        return set(
            AccessAttempt.objects
            .filter(failures_since_start__gte=limit)
            .values_list("username", flat=True)
        )
    except Exception:
        return set()


@admin_required
def user_unlock(request, pk):
    target = get_object_or_404(User, pk=pk)
    try:
        from axes.utils import reset
        reset(username=target.username)
        messages.success(request, f"Unlocked “{target.username}”. They can log in again.")
    except Exception as e:
        messages.error(request, f"Could not unlock: {e}")
    return redirect("user_list")


@admin_required
def user_create(request):
    if request.method == "POST":
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            group = form.cleaned_data["group"]
            # Administrators get Django-admin access too.
            if group.name == GROUP_ADMIN:
                user.is_staff = True
                user.is_superuser = True
            user.save()
            user.groups.set([group])
            messages.success(request, f"User “{user.username}” created.")
            return redirect("user_list")
    else:
        form = AdminUserCreateForm()
    return render(request, "notes/user_form.html", {"form": form, "mode": "create"})


@admin_required
def user_reset_password(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = SetPasswordForm(target, request.POST)
        _style(form)
        if form.is_valid():
            form.save()
            messages.success(request, f"Password reset for “{target.username}”.")
            return redirect("user_list")
    else:
        form = _style(SetPasswordForm(target))
    return render(request, "notes/user_reset.html", {"form": form, "target": target})


@login_required
def password_change(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        _style(form)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # stay logged in
            messages.success(request, "Your password has been changed.")
            return redirect("home")
    else:
        form = _style(PasswordChangeForm(request.user))
    return render(request, "notes/password_change.html", {"form": form})
