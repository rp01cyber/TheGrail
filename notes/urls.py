from django.contrib.auth import views as auth_views
from django.urls import path
from . import views, editor_views as ed, user_views as uv, manage_views as mg, export_views as ex, tag_views as tg

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("preview/", ed.preview, name="preview"),

    # Editor — literal suffixes MUST precede the <slug> detail route
    path("page/<int:pk>/edit/", ed.page_edit, name="page_edit"),
    path("page/<int:pk>/upload/", ed.file_upload, name="file_upload"),
    path("folder/<int:folder_pk>/new-page/", ed.page_create, name="page_create"),
    path("folder/new/", ed.folder_create, name="folder_create"),
    path("file/<int:pk>/download/", views.download_file, name="download_file"),

    # Repository management
    path("repo/pages/", mg.manage_pages, name="manage_pages"),
    path("repo/page/new/", mg.page_new, name="page_new"),
    path("repo/folder/new/", mg.folder_new, name="folder_new"),
    path("repo/page/<int:pk>/clone/", mg.page_clone, name="page_clone"),
    path("repo/page/<int:pk>/move/", mg.page_move, name="page_move"),
    path("repo/folder/<int:pk>/move/", mg.folder_move, name="folder_move"),
    path("repo/folder/<int:pk>/edit/", mg.folder_edit, name="folder_edit"),
    path("repo/folder/<int:pk>/delete/", mg.folder_delete, name="folder_delete"),
    path("repo/page/<int:pk>/delete/", mg.page_delete, name="page_delete"),
    path("repo/file/<int:pk>/delete/", mg.file_delete, name="file_delete"),

    # Export
    path("page/<int:pk>/export.md", ex.export_page, name="export_page"),
    path("repo/export.zip", ex.export_all, name="export_all"),

    # Read views (generic slug route comes last)
    path("page/<int:pk>/", views.page_detail, name="page_detail"),
    path("page/<int:pk>/<slug:slug>/", views.page_detail, name="page_detail"),

    # User management
    path("users/", uv.user_list, name="user_list"),
    path("users/new/", uv.user_create, name="user_create"),
    path("users/<int:pk>/reset-password/", uv.user_reset_password, name="user_reset_password"),
    path("users/<int:pk>/unlock/", uv.user_unlock, name="user_unlock"),
    path("account/password/", uv.password_change, name="password_change"),

    # Tags (admin-managed repository)
    path("tags/", tg.tag_list, name="tag_list"),
    path("tags/new/", tg.tag_create, name="tag_create"),
    path("tags/<int:pk>/rename/", tg.tag_rename, name="tag_rename"),
    path("tags/<int:pk>/delete/", tg.tag_delete, name="tag_delete"),

    # Auth
    path("login/", views.Login.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
