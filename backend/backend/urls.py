"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from api.keyword_views import (
    InitialKeywordView,
    NewKeywordView,
    AddKnownKeywordView,
    SavePassageView,
    GetSavedPassagesView,
    DeleteSavedPassageView,
    GetAIExplanationView,
)
from api.profile import (
    SignupView,
    LoginView,
    LogoutView,
    ProfileView,
    ClearUserKeywordHistoryView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/get_keywords/", InitialKeywordView.as_view(), name="get_keywords"),
    path("api/new_keyword/", NewKeywordView.as_view(), name="new_keywords"),
    path("api/signup/", SignupView.as_view(), name="signup"),
    path("api/login/", LoginView.as_view(), name="login"),
    path("api/logout/", LogoutView.as_view(), name="logout"),
    path("api/profile/", ProfileView.as_view(), name="profile"),
    path(
        "api/add_known_word_to_passage/",
        AddKnownKeywordView.as_view(),
        name="add_known_word_to_passage",
    ),
    path("api/save_passage/", SavePassageView.as_view(), name="save_passage"),
    path(
        "api/get_all_saved_passages/",
        GetSavedPassagesView.as_view(),
        name="get_all_saved_passages",
    ),
    path(
        "api/delete_saved_passage/",
        DeleteSavedPassageView.as_view(),
        name="delete_saved_passage",
    ),
    path(
        "api/get_ai_explanation/",
        GetAIExplanationView.as_view(),
        name="get_ai_explanation",
    ),
    path(
        "api/clear_user_keyword_history/",
        ClearUserKeywordHistoryView.as_view(),
        name="clear_user_keyword_history",
    ),
]
