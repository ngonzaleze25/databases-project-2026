from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("exercises/", views.exercise_list, name="exercise_list"),
    path("exercises/<int:pk>/", views.exercise_detail, name="exercise_detail"),
    path("analytics/", views.analytics, name="analytics"),
    path("workout/", views.workout_result, name="workout_result"),
    path("workout/save/", views.save_workout, name="save_workout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("questionnaire/", views.questionnaire, name="questionnaire"),
    path("program/generate/", views.generate_program, name="generate_program"),
]