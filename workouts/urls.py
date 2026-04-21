from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("exercises/", views.exercise_list, name="exercise_list"),
    path("exercises/<int:pk>/", views.exercise_detail, name="exercise_detail"),
    path("analytics/", views.analytics, name="analytics"),
    path("workout/", views.workout_result, name="workout_result"),
]