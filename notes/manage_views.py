"""
Repository management: a single screen listing the whole tree with per-item
actions (edit, clone, move, delete), plus the endpoints behind them.

Deletion always requires the user to type the item's exact name — enforced on
the server, not just in the browser — so a stray click can't destroy content.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from . import permissions
from .forms import FolderForm
from .models import ExternalLink, Folder, Page, PageFile, Tag


def _forbidden(msg="You don't have permission to do that."):
    return HttpResponseForbidden(msg)


# ---- Tree assembly for the manage screen ----------------------------------

def _manage_node(folder, user, depth=0):
    caps = permissions.effective_capabilities(user, folder)
    node = {
        "folder": folder,
        "depth": depth,
        "private": folder.visibility == "private",
        "can_edit_folder": permissions.is_admin(user) or "edit" in caps,
        "can_delete_folder": permissions.is_admin(user) or "delete" in caps,
        "can_add": permissions.is_admin(user) or "create_child" in caps,
        "pages": [],
        "children": [],
    }
    for p in folder.pages.all():
        if permissions.can_view(user, p):
            pc = permissions.effective_capabilities(user, p)
            node["pages"].append({
                "page": p,
                "depth": depth + 1,
                "can_edit": "edit" in pc,
                "can_delete": "delete" in pc,
                "can_clone": "create_child" in permissions.effective_capabilities(user, folder),
            })
    for c in folder.children.all():
        if permissions.can_view(user, c):
            node["children"].append(_manage_node(c, user, depth + 1))
    return node


@login_required
def manage_pages(request):
    roots = [
        _manage_node(f, request.user)
        for f in Folder.objects.filter(parent__isnull=True)
        if permissions.can_view(request.user, f)
    ]
    # Folders the user may create inside (destination options for move/new).
    dest_folders = [
        f for f in Folder.objects.all()
        if permissions.is_admin(request.user)
        or "create_child" in permissions.effective_capabilities(request.user, f)
    ]
    return render(request, "notes/manage_pages.html", {
        "roots": roots,
        "dest_folders": dest_folders,
        "is_admin": permissions.is_admin(request.user),
    })


# ---- Create (from modals) --------------------------------------------------

@login_required
@require_POST
def page_new(request):
    """Create an empty page from the New Page modal, then open its editor."""
    folder = get_object_or_404(Folder, pk=request.POST.get("folder"))
    if not (permissions.is_admin(request.user)
            or "create_child" in permissions.effective_capabilities(request.user, folder)):
        return _forbidden()
    title = (request.POST.get("title") or "").strip()
    if not title:
        return HttpResponseBadRequest("Title required.")
    page = Page.objects.create(
        folder=folder, title=title, owner=request.user,
        visibility=request.POST.get("visibility", "public"),
    )
    page.contributors.add(request.user)
    messages.success(request, f"Page “{title}” created — add your content.")
    return redirect("page_edit", pk=page.pk)


@login_required
@require_POST
def folder_new(request):
    """Create a folder from the New Folder modal."""
    parent_pk = request.POST.get("parent") or None
    parent = Folder.objects.filter(pk=parent_pk).first() if parent_pk else None
    if parent is None:
        if not permissions.is_admin(request.user):
            return _forbidden("Only administrators can create top-level folders.")
    else:
        if not (permissions.is_admin(request.user)
                or "create_child" in permissions.effective_capabilities(request.user, parent)):
            return _forbidden()
    name = (request.POST.get("name") or "").strip()
    if not name:
        return HttpResponseBadRequest("Name required.")
    Folder.objects.create(
        name=name, parent=parent, owner=request.user,
        visibility=request.POST.get("visibility", "public"),
    )
    messages.success(request, f"Folder “{name}” created.")
    return redirect(request.POST.get("next") or "manage_pages")


# ---- Clone -----------------------------------------------------------------

@login_required
@require_POST
def page_clone(request, pk):
    page = get_object_or_404(Page, pk=pk)
    if not (permissions.is_admin(request.user)
            or "create_child" in permissions.effective_capabilities(request.user, page.folder)):
        return _forbidden()
    clone = Page.objects.create(
        folder=page.folder,
        title=f"{page.title} (copy)",
        description=page.description,
        knowledge_md=page.knowledge_md,
        testing_md=page.testing_md,
        visibility=page.visibility,
        owner=request.user,
    )
    clone.tags.set(page.tags.all())
    clone.contributors.add(request.user)
    for link in page.external_links.all():
        ExternalLink.objects.create(page=clone, label=link.label, url=link.url, order=link.order)
    messages.success(request, f"Cloned to “{clone.title}”.")
    return redirect("manage_pages")


# ---- Move ------------------------------------------------------------------

@login_required
@require_POST
def page_move(request, pk):
    page = get_object_or_404(Page, pk=pk)
    if "edit" not in permissions.effective_capabilities(request.user, page) and not permissions.is_admin(request.user):
        return _forbidden()
    dest = get_object_or_404(Folder, pk=request.POST.get("dest"))
    if not (permissions.is_admin(request.user)
            or "create_child" in permissions.effective_capabilities(request.user, dest)):
        return _forbidden("You can't move items into that folder.")
    page.folder = dest
    page.slug = ""  # regenerate to avoid collisions in the new folder
    page.save()
    messages.success(request, f"Moved “{page.title}” to {dest.name}.")
    return redirect("manage_pages")


def _descendant_ids(folder):
    ids = {folder.pk}
    for c in folder.children.all():
        ids |= _descendant_ids(c)
    return ids


@login_required
@require_POST
def folder_move(request, pk):
    folder = get_object_or_404(Folder, pk=pk)
    if not (permissions.is_admin(request.user)
            or "edit" in permissions.effective_capabilities(request.user, folder)):
        return _forbidden()
    dest_pk = request.POST.get("dest") or None
    dest = Folder.objects.filter(pk=dest_pk).first() if dest_pk else None
    if dest is None and not permissions.is_admin(request.user):
        return _forbidden("Only administrators can move a folder to the top level.")
    if dest and dest.pk in _descendant_ids(folder):
        return HttpResponseBadRequest("Can't move a folder into itself or its own subfolder.")
    folder.parent = dest
    folder.save()
    messages.success(request, f"Moved “{folder.name}”.")
    return redirect("manage_pages")


# ---- Rename / edit a folder ------------------------------------------------

@login_required
def folder_edit(request, pk):
    folder = get_object_or_404(Folder, pk=pk)
    if not (permissions.is_admin(request.user)
            or "edit" in permissions.effective_capabilities(request.user, folder)):
        return _forbidden()
    if request.method == "POST":
        form = FolderForm(request.POST, instance=folder)
        if form.is_valid():
            form.save()
            messages.success(request, "Folder updated.")
            return redirect("manage_pages")
    else:
        form = FolderForm(instance=folder)
    return render(request, "notes/folder_form.html", {"form": form, "editing": folder})


# ---- Delete (type-the-name confirmation, enforced server-side) -------------

def _check_name(request, expected):
    typed = (request.POST.get("confirm_name") or "").strip()
    return typed == (expected or "").strip()


@login_required
@require_POST
def folder_delete(request, pk):
    folder = get_object_or_404(Folder, pk=pk)
    if not (permissions.is_admin(request.user)
            or "delete" in permissions.effective_capabilities(request.user, folder)):
        return _forbidden()
    if not _check_name(request, folder.name):
        return HttpResponseBadRequest("Name confirmation did not match. Nothing was deleted.")
    name = folder.name
    folder.delete()  # cascades to sub-folders and pages
    messages.success(request, f"Deleted folder “{name}” and everything inside it.")
    return redirect("manage_pages")


@login_required
@require_POST
def page_delete(request, pk):
    page = get_object_or_404(Page, pk=pk)
    if not (permissions.is_admin(request.user)
            or "delete" in permissions.effective_capabilities(request.user, page)):
        return _forbidden()
    if not _check_name(request, page.title):
        return HttpResponseBadRequest("Name confirmation did not match. Nothing was deleted.")
    title = page.title
    page.delete()
    messages.success(request, f"Deleted page “{title}”.")
    return redirect("manage_pages")


@login_required
@require_POST
def file_delete(request, pk):
    pf = get_object_or_404(PageFile, pk=pk)
    if not (permissions.can_delete(request.user, pf.page)
            or permissions.can_upload(request.user, pf.page)):
        return _forbidden()
    if not _check_name(request, pf.original_name):
        return HttpResponseBadRequest("Name confirmation did not match. Nothing was deleted.")
    page_pk = pf.page.pk
    pf.f.delete(save=False)
    pf.delete()
    messages.success(request, "File removed.")
    return redirect("page_edit", pk=page_pk)
