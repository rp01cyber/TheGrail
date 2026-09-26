"""
Tag repository — admin-managed.

Admins maintain a central list of tags here. On a page, users pick from this
list via a searchable dropdown; only admins can create new tags.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from . import permissions
from .models import Tag


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not permissions.is_admin(request.user):
            return HttpResponseForbidden("Administrators only.")
        return view(request, *args, **kwargs)
    return wrapper


@admin_required
def tag_list(request):
    tags = Tag.objects.all().order_by("name")
    rows = [{"tag": t, "uses": t.pages.count()} for t in tags]
    return render(request, "notes/tags.html", {"rows": rows})


@admin_required
def tag_create(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            Tag.objects.get_or_create(
                slug=slugify(name), defaults={"name": name}
            )
            messages.success(request, f"Tag “{name}” added.")
    return redirect("tag_list")


@admin_required
def tag_rename(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if name:
            tag.name = name
            tag.slug = slugify(name)
            tag.save()
            messages.success(request, "Tag renamed.")
    return redirect("tag_list")


@admin_required
def tag_delete(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    if request.method == "POST":
        name = tag.name
        tag.delete()  # removes it from any pages via the m2m
        messages.success(request, f"Tag “{name}” deleted.")
    return redirect("tag_list")
