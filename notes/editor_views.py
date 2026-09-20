"""
Editor views. Every mutating action is gated by the permission engine and
CSRF-protected. Capabilities:
  edit         -> change a page's content/meta
  create_child -> create a page or sub-folder under a folder
  upload       -> attach/remove files on a page
  delete       -> delete a page
Root-folder creation is admin-only.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from . import permissions
from .forms import FolderForm, PageForm
from .models import ExternalLink, Folder, Page, PageFile, Tag
from .templatetags.md import render_md


def _require(cond):
    if not cond:
        raise PermissionDenied()


class PermissionDenied(Exception):
    pass


def _forbidden(request, msg="You don't have permission to do that."):
    return HttpResponseForbidden(msg)


def _apply_tag_ids(request, page):
    """Set the page's tags from selected existing-tag IDs (pick-only)."""
    ids = request.POST.getlist("tags")
    page.tags.set(Tag.objects.filter(pk__in=ids))


@login_required
def page_edit(request, pk):
    page = get_object_or_404(Page, pk=pk)
    if not permissions.can_edit(request.user, page):
        return _forbidden(request)

    conflict = None
    if request.method == "POST":
        form = PageForm(request.POST, instance=page)
        # Optimistic concurrency: the editor submits the version it loaded.
        # If the page has been saved by someone else since then, refuse to
        # overwrite — warn instead, preserving what the user typed.
        try:
            base_version = int(request.POST.get("base_version", "0"))
        except (TypeError, ValueError):
            base_version = 0

        if base_version and base_version != page.version:
            conflict = {
                "current_version": page.version,
                "your_base": base_version,
                "updated_at": page.updated_at,
                "last_editor": page.contributors.order_by("-id").values_list("username", flat=True).first(),
            }
            # Fall through to re-render the bound form (their edits are kept).
            # base_version is refreshed below so a deliberate re-save proceeds.
        elif form.is_valid():
            page = form.save(commit=False)
            page.version = (page.version or 1) + 1
            page.save()
            _apply_tag_ids(request, page)
            page.contributors.add(request.user)
            _save_links(request, page)
            messages.success(request, "Page saved.")
            return redirect(page.get_absolute_url())
    else:
        form = PageForm(instance=page)

    return render(request, "notes/page_edit.html", {
        "form": form, "page": page,
        "links": page.external_links.all(),
        "files": page.files.all(),
        "can_upload": permissions.can_upload(request.user, page),
        "can_delete": permissions.can_delete(request.user, page),
        "base_version": page.version,
        "conflict": conflict,
        "all_tags": Tag.objects.all().order_by("name"),
        "selected_tag_ids": set(page.tags.values_list("pk", flat=True)),
    })


@login_required
def page_create(request, folder_pk):
    folder = get_object_or_404(Folder, pk=folder_pk)
    caps = permissions.effective_capabilities(request.user, folder)
    if "create_child" not in caps:
        return _forbidden(request)

    if request.method == "POST":
        form = PageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            page.folder = folder
            page.owner = request.user
            page.save()
            _apply_tag_ids(request, page)
            page.contributors.add(request.user)
            messages.success(request, "Page created.")
            return redirect(page.get_absolute_url())
    else:
        form = PageForm()

    return render(request, "notes/page_edit.html", {
        "form": form, "page": None, "parent": folder,
        "links": [], "files": [], "can_upload": False, "can_delete": False,
        "all_tags": Tag.objects.all().order_by("name"),
        "selected_tag_ids": set(),
    })


@login_required
def folder_create(request):
    parent_pk = request.GET.get("parent") or request.POST.get("parent")
    parent = Folder.objects.filter(pk=parent_pk).first() if parent_pk else None

    if parent is None:
        # Root folder: admin only.
        if not permissions.is_admin(request.user):
            return _forbidden(request, "Only administrators can create top-level folders.")
    else:
        if "create_child" not in permissions.effective_capabilities(request.user, parent):
            return _forbidden(request)

    if request.method == "POST":
        form = FolderForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.owner = request.user
            folder.save()
            messages.success(request, "Folder created.")
            return redirect("home")
    else:
        form = FolderForm(initial={"parent": parent})

    return render(request, "notes/folder_form.html", {"form": form})


@login_required
@require_POST
def file_upload(request, pk):
    page = get_object_or_404(Page, pk=pk)
    if not permissions.can_upload(request.user, page):
        return _forbidden(request)
    f = request.FILES.get("file")
    if f:
        PageFile.objects.create(page=page, f=f, uploaded_by=request.user)
        messages.success(request, f"Uploaded {f.name}.")
    return redirect("page_edit", pk=page.pk)


def _save_links(request, page):
    """Rebuild Further Reading from posted rows (external URLs only)."""
    labels = request.POST.getlist("link_label")
    urls = request.POST.getlist("link_url")
    page.external_links.all().delete()
    order = 0
    for label, url in zip(labels, urls):
        label, url = label.strip(), url.strip()
        if label and url:
            ExternalLink.objects.create(page=page, label=label, url=url, order=order)
            order += 1


@login_required
@require_POST
def preview(request):
    """Render Markdown with the exact published renderer (WYSIWYG guarantee)."""
    html = render_md(request.POST.get("md", ""))
    return JsonResponse({"html": str(html)})
