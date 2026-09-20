"""
Export pages as Markdown files.

  * Single page  -> one .md file (both tabs + metadata).
  * Whole space  -> a .zip mirroring the folder tree, one .md per page.

Only content the user is allowed to view is exported. No new dependencies —
uses Python's standard library zipfile/io.
"""
import io
import zipfile

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from . import permissions
from .models import Folder, Page


def _page_to_markdown(page):
    """Render one page to a self-contained Markdown document."""
    lines = [f"# {page.title}", ""]
    if page.description:
        lines += [f"> {page.description}", ""]

    tags = list(page.tags.values_list("name", flat=True))
    if tags:
        lines += ["**Tags:** " + ", ".join(tags), ""]

    lines += ["## Knowledge", "", (page.knowledge_md or "_(empty)_"), ""]
    lines += ["## Testing", "", (page.testing_md or "_(empty)_"), ""]

    links = list(page.external_links.all())
    if links:
        lines += ["## Further reading", ""]
        lines += [f"- [{l.label}]({l.url})" for l in links]
        lines += [""]

    return "\n".join(lines)


def _safe_name(text):
    name = slugify(text) or "untitled"
    return name[:80]


def export_page(request, pk):
    page = get_object_or_404(Page, pk=pk)
    if not permissions.can_view(request.user, page):
        raise Http404()
    md = _page_to_markdown(page)
    resp = HttpResponse(md, content_type="text/markdown; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{_safe_name(page.title)}.md"'
    return resp


def _folder_path(folder):
    return "/".join(_safe_name(f.name) for f in folder.ancestors())


@login_required
def export_all(request):
    """Zip every viewable page as .md, mirroring the folder tree."""
    buffer = io.BytesIO()
    used = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        pages = Page.objects.select_related("folder").all()
        count = 0
        for page in pages:
            if not permissions.can_view(request.user, page):
                continue
            folder_path = _folder_path(page.folder) if page.folder else ""
            base = _safe_name(page.title)
            path = f"{folder_path}/{base}.md" if folder_path else f"{base}.md"
            # de-duplicate identical paths
            n, unique = 1, path
            while unique in used:
                n += 1
                unique = path[:-3] + f"-{n}.md"
            used.add(unique)
            zf.writestr(unique, _page_to_markdown(page))
            count += 1
        if count == 0:
            zf.writestr("README.txt", "No pages available to export.")

    buffer.seek(0)
    resp = HttpResponse(buffer.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = 'attachment; filename="pentestnotes-export.zip"'
    return resp
