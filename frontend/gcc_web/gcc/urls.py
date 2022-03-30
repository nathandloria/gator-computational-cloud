from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="sign in"),
    path("signup", views.signup, name="sign up"),
    path("signup-error", views.signup_error, name="sign up error"),
    path("user-logout", views.user_logout, name="user logout"),
    path("user-home", views.user_home, name="user home"),
    path("user-workflows", views.user_workflows, name="user workflows"),
    path(
        "user-workflows-validated",
        views.user_workflows_validated,
        name="user workflows validated",
    ),
    path(
        "execute-workflow/<str:workflow_name>",
        views.execute_workflow,
        name="execute workflow",
    ),
    path("user-credentials", views.user_credentials, name="user credentials"),
    path("user-dropbox-oauth", views.user_dropbox_oauth, name="user dropbox oauth"),
    path("user-machine-pool", views.user_machine_pool, name="user machine pool"),
    path(
        "user-machine-pool/delete/<str:id>",
        views.user_machine_pool_delete,
        name="delete user machine",
    ),
]
