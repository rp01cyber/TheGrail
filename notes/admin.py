"""
Admin = the management surface. It gives you a working way to create folders,
write pages (both tabs), attach files, add external links, and manage grants
from day one. A friendlier in-page rich-text editor comes in the next layer;
the admin remains the durable fallback for full control.
"""
from django import forms
from django.contrib import admin

from .models import (
    ExternalLink,
    Folder,
    Grant,
    GROUP_DEFAULT_LOADOUTS,
    Page,
    PageFile,
    Tag,
)


class ExternalLinkInline(admin.TabularInline):
    model = ExternalLink
    extra = 1


class PageFileInline(admin.TabularInline):
    model = PageFile
    extra = 0
    fields = ("f", "original_name", "human_size", "uploaded_by")
    readonly_fields = ("original_name", "human_size")


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "visibility", "owner", "updated_at")
    list_filter = ("visibility",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "folder", "visibility", "version", "updated_at")
    list_filter = ("visibility", "folder", "tags")
    search_fields = ("title", "description", "knowledge_md", "testing_md")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags", "contributors")
    inlines = [ExternalLinkInline, PageFileInline]
    fieldsets = (
        (None, {"fields": ("folder", "title", "slug", "description")}),
        ("Knowledge tab", {"fields": ("knowledge_md",)}),
        ("Testing tab", {"fields": ("testing_md",)}),
        ("Access & meta", {"fields": ("visibility", "owner", "tags", "contributors", "version")}),
    )


class GrantForm(forms.ModelForm):
    class Meta:
        model = Grant
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill capabilities from the group's default loadout for new grants.
        if not self.instance.pk and "capabilities" in self.fields:
            self.fields["capabilities"].help_text = (
                "Leave blank to accept the group's default loadout on save. "
                "Defaults: " + "; ".join(f"{g}={','.join(c)}" for g, c in GROUP_DEFAULT_LOADOUTS.items())
            )


@admin.register(Grant)
class GrantAdmin(admin.ModelAdmin):
    form = GrantForm
    list_display = ("folder", "group", "user", "caps_display", "created_by", "created_at")
    list_filter = ("folder", "group")

    @admin.display(description="capabilities")
    def caps_display(self, obj):
        return ", ".join(obj.capabilities or [])

    def save_model(self, request, obj, form, change):
        if not obj.capabilities and obj.group and obj.group.name in GROUP_DEFAULT_LOADOUTS:
            obj.capabilities = list(GROUP_DEFAULT_LOADOUTS[obj.group.name])
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
