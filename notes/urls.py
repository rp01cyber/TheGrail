from django.contrib.auth import views as auth_views
from django.urls import path
from . import views, editor_views as ed, user_views as uv

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("preview/", ed.preview, name="preview"),

    # Editor — literal suffixes MUST precede the <slug> detail route
    # so "edit"/"upload"/"delete" aren't mistaken for a page slug.
    path("page/<int:pk>/edit/", ed.page_edit, name="page_edit"),
    path("page/<int:pk>/upload/", ed.file_upload, name="file_upload"),
    path("page/<int:pk>/delete/", ed.page_delete, name="page_delete"),
    path("folder/<int:folder_pk>/new-page/", ed.page_create, name="page_create"),
    path("folder/new/", ed.folder_create, name="folder_create"),
    path("file/<int:pk>/download/", views.download_file, name="download_file"),
    path("file/<int:pk>/delete/", ed.file_delete, name="file_delete"),

    # Read views (generic slug route comes last)
    path("page/<int:pk>/", views.page_detail, name="page_detail"),
    path("page/<int:pk>/<slug:slug>/", views.page_detail, name="page_detail"),

    # User management
    path("users/", uv.user_list, name="user_list"),
    path("users/new/", uv.user_create, name="user_create"),
    path("users/<int:pk>/reset-password/", uv.user_reset_password, name="user_reset_password"),
    path("account/password/", uv.password_change, name="password_change"),

    # Auth
    path("login/", views.Login.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
