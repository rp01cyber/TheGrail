"""
Permission resolution — the single source of truth for "who can do what."

Rules, in order:
  * Administrators (or Django superusers) can do everything, everywhere, and
    can see all private content.
  * The item's owner has full capabilities on their own item.
  * Otherwise, capabilities come from Grants on the item's folder and every
    ancestor folder (inheritance), matching the user directly or via a group.
  * Public content is readable by anyone, including anonymous visitors.
  * Private content requires the VIEW capability (or admin / owner).

Enforcement always runs against the real object per request — never rely on
merely hiding something from the navigation tree.
"""
from .models import (
    ALL_CAPS,
    CAP_VIEW,
    GROUP_ADMIN,
    VISIBILITY_PRIVATE,
    Folder,
    Page,
)


def is_admin(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return user.is_superuser or user.groups.filter(name=GROUP_ADMIN).exists()


def _target_folder(obj):
    """The folder whose grant-chain governs obj (a Folder governs itself)."""
    if isinstance(obj, Folder):
        return obj
    if isinstance(obj, Page):
        return obj.folder
    return None


def effective_capabilities(user, obj):
    """Return the set of capability keys `user` holds on `obj`."""
    if is_admin(user):
        return set(ALL_CAPS)

    caps = set()
    if getattr(user, "is_authenticated", False) and getattr(obj, "owner_id", None) == user.id:
        caps.update(ALL_CAPS)

    if not getattr(user, "is_authenticated", False):
        return caps

    folder = _target_folder(obj)
    if folder is None:
        return caps

    group_ids = set(user.groups.values_list("id", flat=True))
    # Walk this folder and all ancestors, unioning matching grants.
    for f in folder.ancestors():
        for grant in f.grants.all():
            if grant.user_id == user.id or (grant.group_id and grant.group_id in group_ids):
                caps.update(grant.capabilities or [])
    return caps


def can_view(user, obj):
    # Public content: always viewable.
    effectively_private = getattr(obj, "is_effectively_private", False)
    if not effectively_private:
        return True
    # Private content: admin, owner, or an explicit VIEW capability.
    if is_admin(user):
        return True
    return CAP_VIEW in effective_capabilities(user, obj)


def can_edit(user, obj):
    from .models import CAP_EDIT
    return CAP_EDIT in effective_capabilities(user, obj)


def can_upload(user, obj):
    from .models import CAP_UPLOAD
    return CAP_UPLOAD in effective_capabilities(user, obj)


def can_delete(user, obj):
    from .models import CAP_DELETE
    return CAP_DELETE in effective_capabilities(user, obj)


def visible_pages(user, queryset):
    """Filter a Page queryset to those `user` may view (used for nav/search)."""
    return [p for p in queryset if can_view(user, p)]


def visible_root_folders(user):
    """Top-level folders the user may see, for building the workspace tree."""
    roots = Folder.objects.filter(parent__isnull=True)
    return [f for f in roots if can_view(user, f)]
