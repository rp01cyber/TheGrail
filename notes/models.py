"""
Data model for PentestNotes.

Content is a tree of Folders holding Pages. Each Page has two independent
bodies — Knowledge and Testing — stored as Markdown. Access is governed by:

  * Visibility   : public (anyone reads) or private (restricted).
  * Group        : Administrator / Senior / Junior — the baseline role.
  * Grant        : gives a user or group capabilities on a Folder; grants
                   INHERIT down the tree. Capabilities default from the
                   group's loadout but can be overridden per grant.

Permission resolution lives in notes/permissions.py.
"""
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


# --- Constants --------------------------------------------------------------
GROUP_ADMIN = "Administrator"
GROUP_SENIOR = "Senior"
GROUP_JUNIOR = "Junior"

# Capabilities a grant can carry.
CAP_VIEW = "view"
CAP_EDIT = "edit"
CAP_CREATE = "create_child"
CAP_UPLOAD = "upload"
CAP_DELETE = "delete"

CAPABILITIES = [
    (CAP_VIEW, "View"),
    (CAP_EDIT, "Edit content"),
    (CAP_CREATE, "Create pages / sub-folders"),
    (CAP_UPLOAD, "Upload files"),
    (CAP_DELETE, "Delete"),
]
ALL_CAPS = [c[0] for c in CAPABILITIES]

# Default loadouts pre-filled when a grant is created for a group.
GROUP_DEFAULT_LOADOUTS = {
    GROUP_ADMIN: list(ALL_CAPS),
    GROUP_SENIOR: [CAP_VIEW, CAP_EDIT, CAP_CREATE, CAP_UPLOAD],
    GROUP_JUNIOR: [CAP_VIEW, CAP_EDIT],
}

VISIBILITY_PUBLIC = "public"
VISIBILITY_PRIVATE = "private"
VISIBILITY_CHOICES = [
    (VISIBILITY_PUBLIC, "Public — anyone can read"),
    (VISIBILITY_PRIVATE, "Private — restricted"),
]


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Folder(TimeStamped):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    visibility = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES, default=VISIBILITY_PUBLIC
    )
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_folders"
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["parent", "slug"], name="uniq_folder_slug_per_parent")
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def ancestors(self):
        """Return [root, ..., self] — used for breadcrumbs and inheritance."""
        chain, node = [], self
        while node is not None:
            chain.append(node)
            node = node.parent
        return list(reversed(chain))

    @property
    def is_effectively_private(self):
        return any(f.visibility == VISIBILITY_PRIVATE for f in self.ancestors())


class Page(TimeStamped):
    folder = models.ForeignKey(
        Folder, null=True, blank=True, on_delete=models.CASCADE, related_name="pages"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    description = models.CharField(max_length=400, blank=True)

    # The two tabs — independent Markdown bodies on one page.
    knowledge_md = models.TextField(blank=True, verbose_name="Knowledge (Markdown)")
    testing_md = models.TextField(blank=True, verbose_name="Testing (Markdown)")

    visibility = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES, default=VISIBILITY_PUBLIC
    )
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_pages"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="pages")
    contributors = models.ManyToManyField(
        User, blank=True, related_name="contributed_pages"
    )
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(fields=["folder", "slug"], name="uniq_page_slug_per_folder")
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("page_detail", args=[self.pk, self.slug])

    def breadcrumbs(self):
        return self.folder.ancestors() if self.folder else []

    @property
    def is_effectively_private(self):
        if self.visibility == VISIBILITY_PRIVATE:
            return True
        return bool(self.folder and self.folder.is_effectively_private)


def upload_path(instance, filename):
    return f"pages/{instance.page_id}/{filename}"


class PageFile(TimeStamped):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="files")
    f = models.FileField(upload_to=upload_path)
    original_name = models.CharField(max_length=255, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="uploads"
    )

    class Meta:
        ordering = ["original_name"]

    def save(self, *args, **kwargs):
        if self.f and not self.original_name:
            self.original_name = self.f.name.rsplit("/", 1)[-1]
        if self.f and hasattr(self.f, "size"):
            self.size = self.f.size or 0
        super().save(*args, **kwargs)

    @property
    def human_size(self):
        n = float(self.size)
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024 or unit == "GB":
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024

    @property
    def kind(self):
        return (self.original_name.rsplit(".", 1)[-1] if "." in self.original_name else "file").upper()[:4]

    def __str__(self):
        return self.original_name


class ExternalLink(models.Model):
    """Further Reading — external URLs only. A URLField rejects internal paths."""
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="external_links")
    label = models.CharField(max_length=200)
    url = models.URLField(max_length=500)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "label"]

    def __str__(self):
        return f"{self.label} -> {self.url}"


class Grant(models.Model):
    """
    Access to a Folder for a group OR a single user. Grants inherit down the
    tree. `capabilities` is a list of capability keys; it pre-fills from the
    group's default loadout but can be trimmed or extended per grant.
    """
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="grants")
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    capabilities = models.JSONField(default=list)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="grants_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="grant_group_xor_user",
                check=(
                    models.Q(group__isnull=False, user__isnull=True)
                    | models.Q(group__isnull=True, user__isnull=False)
                ),
            )
        ]

    def __str__(self):
        subject = self.group or self.user
        return f"{subject} @ {self.folder}: {', '.join(self.capabilities)}"
