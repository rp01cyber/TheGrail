"""Forms for the in-page editor."""
from django import forms

from .models import Folder, Page, VISIBILITY_CHOICES


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = ["title", "description", "visibility", "knowledge_md", "testing_md"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "in", "placeholder": "Page title"}),
            "description": forms.TextInput(attrs={"class": "in", "placeholder": "One-line description"}),
            "visibility": forms.Select(attrs={"class": "in"}),
            "knowledge_md": forms.Textarea(attrs={"class": "md-area", "data-editor": "knowledge", "rows": 18}),
            "testing_md": forms.Textarea(attrs={"class": "md-area", "data-editor": "testing", "rows": 18}),
        }


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ["name", "parent", "visibility"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "in", "placeholder": "Folder name"}),
            "parent": forms.Select(attrs={"class": "in"}),
            "visibility": forms.Select(attrs={"class": "in"}),
        }


# --- User management (admin) ---------------------------------------------
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User


class AdminUserCreateForm(UserCreationForm):
    """Admin creates a user, sets their password, and assigns a group."""
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        widget=forms.Select(attrs={"class": "in"}),
        help_text="Administrator grants global access. Senior/Junior are read-only until granted a folder.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("username", "password1", "password2"):
            self.fields[name].widget.attrs["class"] = "in"
