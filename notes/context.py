"""Injects the permission-filtered workspace tree into all templates."""
from .models import Folder
from . import permissions


def _node(folder, user):
    kids_folders = [
        _node(c, user) for c in folder.children.all() if permissions.can_view(user, c)
    ]
    kids_pages = [
        {"page": p} for p in folder.pages.all() if permissions.can_view(user, p)
    ]
    return {
        "folder": folder,
        "folders": kids_folders,
        "pages": kids_pages,
        "private": folder.visibility == "private",
    }


def workspace_tree(request):
    roots = [
        _node(f, request.user)
        for f in Folder.objects.filter(parent__isnull=True)
        if permissions.can_view(request.user, f)
    ]
    role_label = None
    if request.user.is_authenticated:
        if permissions.is_admin(request.user):
            role_label = "admin"
        else:
            g = request.user.groups.exclude(name="Administrator").values_list("name", flat=True).first()
            role_label = (g or "member").lower()

    # Flat, indented list of folders the user can see — for modal location pickers.
    flat = []
    def _walk(folder, depth):
        if permissions.can_view(request.user, folder):
            flat.append({"folder": folder, "label": ("\u00a0\u00a0" * depth) + folder.name})
            for c in folder.children.all():
                _walk(c, depth + 1)
    for f in Folder.objects.filter(parent__isnull=True):
        _walk(f, 0)

    return {"workspace_tree": roots, "role_label": role_label, "all_folders": flat}
