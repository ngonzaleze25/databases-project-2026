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

    workout_items = []
    recommended_foods = None
    goal_type_name = None
    muscle_group_name = None
    difficulty_name = None

    if request.method == 'POST' and form.is_valid():
        muscle_group = form.cleaned_data.get('muscle_group')
        difficulty = form.cleaned_data.get('difficulty')
        equipment = form.cleaned_data.get('equipment')
        goal_type = form.cleaned_data.get('goal_type')
        num_exercises = form.cleaned_data.get('num_exercises') or 5
        
        if muscle_group:
            muscle_group_name = muscle_group.name
        if difficulty:
            difficulty_name = difficulty.name
            
        base_qs = Exercise.objects.all()
        if difficulty:
            base_qs = base_qs.filter(difficulty=difficulty)
        if equipment:
            base_qs = base_qs.filter(exercise_equipment__equipment__in=equipment).distinct()

        if muscle_group:
            used_ids = []
            
            # 1. Primary Compound Exercise
            compounds = base_qs.filter(
                is_compound=True,
                exercise_muscle_groups__muscle_group=muscle_group,
                exercise_muscle_groups__role='primary'
            ).order_by('?')
            
            compound_ex = compounds.first()
            if compound_ex:
                workout_items.append({'exercise': compound_ex, 'slot': 'compound'})
                used_ids.append(compound_ex.pk)

            # 2. Supporting Muscle logic
            from .models import MuscleGroupRelationship
            supporting_rel = MuscleGroupRelationship.objects.filter(
                source_muscle_group=muscle_group,
                relationship_type='supporting'
            ).order_by('?').first()
            
            supporting_muscle = supporting_rel.related_muscle_group if supporting_rel else None
            
            remaining_slots = num_exercises - len(workout_items)
            supporting_count = 1 if (remaining_slots >= 2 and supporting_muscle) else 0
            targeted_count = remaining_slots - supporting_count

            # 3. Targeted Exercises
            targeted_qs = base_qs.filter(
                exercise_muscle_groups__muscle_group=muscle_group,
                exercise_muscle_groups__role='primary'
            ).exclude(pk__in=used_ids).order_by('?')
            
            for ex in targeted_qs[:targeted_count]:
                workout_items.append({'exercise': ex, 'slot': 'targeted'})
                used_ids.append(ex.pk)

            # 4. Supporting Exercise
            if supporting_count > 0 and supporting_muscle:
                supporting_qs = base_qs.filter(
                    exercise_muscle_groups__muscle_group=supporting_muscle,
                    exercise_muscle_groups__role='primary'
                ).exclude(pk__in=used_ids).order_by('?')
                
                for ex in supporting_qs[:supporting_count]:
                    workout_items.append({'exercise': ex, 'slot': 'supporting'})
                    used_ids.append(ex.pk)

            # 5. Pad if necessary (strict constraints)
            if len(workout_items) < num_exercises:
                pad_qs = base_qs.filter(
                    exercise_muscle_groups__muscle_group=muscle_group
                ).exclude(pk__in=used_ids).order_by('?')
                for ex in pad_qs[:num_exercises - len(workout_items)]:
                    workout_items.append({'exercise': ex, 'slot': 'targeted'})
                    used_ids.append(ex.pk)
                    
            # 6. Ultimate Pad: ignore difficulty and equipment if still empty
            if len(workout_items) < num_exercises:
                ultimate_pad_qs = Exercise.objects.filter(
                    exercise_muscle_groups__muscle_group=muscle_group
                ).exclude(pk__in=used_ids).order_by('?')
                for ex in ultimate_pad_qs[:num_exercises - len(workout_items)]:
                    workout_items.append({'exercise': ex, 'slot': 'targeted'})
                    used_ids.append(ex.pk)
        else:
            # Fallback if no muscle group selected
            exercises_fallback = base_qs.order_by('?')[:num_exercises]
            for ex in exercises_fallback:
                workout_items.append({'exercise': ex, 'slot': 'targeted'})

        # Get nutrition recommendations based on goal
        if goal_type:
            goal_type_name = goal_type.name
            from .models import FoodItem
            recommended_foods = FoodItem.objects.filter(ideal_for_goal=goal_type)

    context = {
        "form": form,
        "workout_items": workout_items,
        "recommended_foods": recommended_foods,
        "goal_type_name": goal_type_name,
        "muscle_group": muscle_group_name,
        "difficulty": difficulty_name,
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
    exercises_by_muscle = [
        {"name": row["muscle_group__name"], "total": row["total"]}
        for row in ExerciseMuscleGroup.objects.filter(role="primary")
        .values("muscle_group__name")
        .annotate(total=Count("exercise"))
        .order_by("muscle_group__name")
    ]

    exercises_by_difficulty = [
        {"name": row["difficulty__name"], "total": row["total"]}
        for row in Exercise.objects.values("difficulty__name")
        .annotate(total=Count("exercise_id"))
        .order_by("difficulty__name")
    ]

    exercises_by_equipment = [
        {"name": row["equipment__name"], "total": row["total"]}
        for row in ExerciseEquipment.objects.values("equipment__name")
        .annotate(total=Count("exercise"))
        .order_by("equipment__name")
    ]

    compound_total = Exercise.objects.filter(is_compound=True).count()
    isolation_total = Exercise.objects.filter(is_compound=False).count()

    exercises_by_movement = [
        {"name": row["movement_type__name"], "total": row["total"]}
        for row in Exercise.objects.values("movement_type__name")
        .annotate(total=Count("exercise_id"))
        .order_by("movement_type__name")
    ]

    context = {
        "exercises_by_muscle": exercises_by_muscle,
        "exercises_by_difficulty": exercises_by_difficulty,
        "exercises_by_equipment": exercises_by_equipment,
        "compound_total": compound_total,
        "isolation_total": isolation_total,
        "exercises_by_movement": exercises_by_movement,
    }

    return render(request, "workouts/analytics.html", context)