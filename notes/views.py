"""
Views. The read surface is public and input-free; the only public form is
search (a read-only query). Everything that changes data requires login and
passes through the permission engine.
"""
from django.contrib.auth import views as auth_views
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from . import permissions
from .models import Page, Folder, PageFile, GROUP_ADMIN


def _role_label(user):
    if not user.is_authenticated:
        return None
    if permissions.is_admin(user):
        return "admin"
    g = user.groups.exclude(name=GROUP_ADMIN).values_list("name", flat=True).first()
    return (g or "member").lower()


def home(request):
    roots = permissions.visible_root_folders(request.user)
    recent = permissions.visible_pages(
        request.user, Page.objects.order_by("-updated_at")[:20]
    )[:8]
    return render(request, "notes/home.html", {"roots": roots, "recent": recent})


def page_detail(request, pk, slug=None):
    page = get_object_or_404(Page, pk=pk)
    # Enforce on the real object — not just nav hiding.
    if not permissions.can_view(request.user, page):
        raise Http404()

    caps = permissions.effective_capabilities(request.user, page)
    ctx = {
        "page": page,
        "breadcrumbs": page.breadcrumbs(),
        "files": page.files.all(),
        "links": page.external_links.all(),
        "tags": page.tags.all(),
        "contributors": page.contributors.all(),
        "can_edit": "edit" in caps,
        "can_upload": "upload" in caps,
        "can_create": "create_child" in caps,
        "role_label": _role_label(request.user),
    }
    return render(request, "notes/page_detail.html", ctx)


def download_file(request, pk):
    """Serve an attachment, honoring the parent page's visibility."""
    pf = get_object_or_404(PageFile, pk=pk)
    if not permissions.can_view(request.user, pf.page):
        raise Http404()
    return FileResponse(pf.f.open("rb"), as_attachment=True, filename=pf.original_name)


def search(request):
    q = (request.GET.get("q") or "").strip()
    results = []
    if q:
        matches = Page.objects.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(knowledge_md__icontains=q)
            | Q(testing_md__icontains=q)
            | Q(tags__name__icontains=q)
        ).distinct()
        results = permissions.visible_pages(request.user, matches)
    return render(request, "notes/search.html", {"q": q, "results": results})


class Login(auth_views.LoginView):
    template_name = "notes/login.html"
    redirect_authenticated_user = True
