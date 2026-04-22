from django.shortcuts import render, get_object_or_404

from django.db.models import Count, F

from .models import (
    Exercise,
    MuscleGroup,
    DifficultyLevel,
    Equipment,
    MovementType,
    ExerciseMuscleGroup,
    ExerciseEquipment,
)
from .forms import WorkoutBuilderForm, ExerciseFilterForm

def home(request):
    form = WorkoutBuilderForm()
    return render(request, "workouts/home.html", {"form": form})


def workout_result(request):
    form = WorkoutBuilderForm(request.POST or None)

    exercises = Exercise.objects.all()
    recommended_foods = None
    goal_type_name = None

    if request.method == 'POST' and form.is_valid():
        muscle_group = form.cleaned_data.get('muscle_group')
        difficulty = form.cleaned_data.get('difficulty')
        equipment = form.cleaned_data.get('equipment')
        goal_type = form.cleaned_data.get('goal_type')
        num_exercises = form.cleaned_data.get('num_exercises') or 5
        
        # Basic filtering logic
        if muscle_group:
            exercises = exercises.filter(exercise_muscle_groups__muscle_group=muscle_group)
        if difficulty:
            exercises = exercises.filter(difficulty=difficulty)
        if equipment:
            exercises = exercises.filter(exercise_equipment__equipment__in=equipment).distinct()
        
        # Get nutrition recommendations based on goal
        if goal_type:
            goal_type_name = goal_type.name
            from .models import FoodItem
            recommended_foods = FoodItem.objects.filter(ideal_for_goal=goal_type)

        exercises = exercises[:num_exercises] # Limit for display

    context = {
        "form": form,
        "exercises": exercises,
        "recommended_foods": recommended_foods,
        "goal_type_name": goal_type_name,
    }
    return render(request, "workouts/workout_result.html", context)


def exercise_list(request):
    form = ExerciseFilterForm(request.GET or None)
    exercises = Exercise.objects.all()

    if form.is_valid():
        muscle_group = form.cleaned_data.get("muscle_group")
        difficulty = form.cleaned_data.get("difficulty")
        equipment = form.cleaned_data.get("equipment")
        movement_type = form.cleaned_data.get("movement_type")
        goal_type = form.cleaned_data.get("goal_type")

        if muscle_group:
            exercises = exercises.filter(
                exercise_muscle_groups__muscle_group=muscle_group
            )

        if difficulty:
            exercises = exercises.filter(difficulty=difficulty)

        if equipment:
            exercises = exercises.filter(
                exercise_equipment__equipment=equipment
            )

        if movement_type:
            exercises = exercises.filter(movement_type=movement_type)

        if goal_type:
            exercises = exercises.filter(
                exercise_goal_profiles__goal_type=goal_type
            )

    exercises = exercises.distinct()

    return render(
        request,
        "workouts/exercise_list.html",
        {"form": form, "exercises": exercises},
    )


def exercise_detail(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk)

    muscles_worked = exercise.exercise_muscle_groups.select_related("muscle_group").all()
    compatible_equipment = exercise.exercise_equipment.select_related("equipment").all()

    context = {
        "exercise": exercise,
        "muscles_worked": muscles_worked,
        "compatible_equipment": compatible_equipment,
    }

    return render(request, "workouts/exercise_detail.html", context)


def analytics(request):
    exercises_by_muscle = (
        ExerciseMuscleGroup.objects.filter(role="primary")
        .annotate(name=F("muscle_group__name"))
        .values("name")
        .annotate(total=Count("exercise"))
        .order_by("name")
    )

    exercises_by_difficulty = (
        Exercise.objects.annotate(name=F("difficulty__name"))
        .values("name")
        .annotate(total=Count("exercise_id"))
        .order_by("name")
    )

    exercises_by_equipment = (
        ExerciseEquipment.objects.annotate(name=F("equipment__name"))
        .values("name")
        .annotate(total=Count("exercise"))
        .order_by("name")
    )

    compound_total = Exercise.objects.filter(is_compound=True).count()
    isolation_total = Exercise.objects.filter(is_compound=False).count()

    exercises_by_movement = (
        Exercise.objects.annotate(name=F("movement_type__name"))
        .values("name")
        .annotate(total=Count("exercise_id"))
        .order_by("name")
    )

    context = {
        "exercises_by_muscle": exercises_by_muscle,
        "exercises_by_difficulty": exercises_by_difficulty,
        "exercises_by_equipment": exercises_by_equipment,
        "compound_total": compound_total,
        "isolation_total": isolation_total,
        "exercises_by_movement": exercises_by_movement,
    }

    return render(request, "workouts/analytics.html", context)