from django.shortcuts import render, get_object_or_404

from django.db.models import Count, F
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required

from .models import (
    Exercise,
    MuscleGroup,
    DifficultyLevel,
    Equipment,
    MovementType,
    ExerciseMuscleGroup,
    ExerciseEquipment,
    UserProfile,
    WorkoutProgram,
    SavedWorkout,
    SavedWorkoutExercise,
    GoalType
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
        calories_burned = 0
        if goal_type:
            goal_type_name = goal_type.name
            from .models import FoodItem
            foods = list(FoodItem.objects.filter(ideal_for_goal=goal_type))
            
            # Estimate calories burned
            diff_multiplier = 1.5
            if difficulty and difficulty.name == 'Beginner': diff_multiplier = 1.0
            elif difficulty and difficulty.name == 'Advanced': diff_multiplier = 2.0
            
            calories_burned = int(len(workout_items) * 45 * diff_multiplier)
            
            recommended_foods = []
            for f in foods:
                # Suggest a portion that covers ~50% of the calories burned
                target_food_calories = calories_burned * 0.5
                portion_g = int((target_food_calories / f.calories_per_100g) * 100)
                
                # Calculate exact macros for this portion
                portion_protein = round((f.protein_g / 100) * portion_g)
                portion_carbs = round((f.carbs_g / 100) * portion_g)
                portion_fat = round((f.fat_g / 100) * portion_g)
                
                recommended_foods.append({
                    'name': f.name,
                    'category': f.category,
                    'portion_g': portion_g,
                    'calories': int(target_food_calories),
                    'protein': portion_protein,
                    'carbs': portion_carbs,
                    'fat': portion_fat,
                })

    context = {
        "form": form,
        "workout_items": workout_items,
        "recommended_foods": recommended_foods,
        "goal_type_name": goal_type_name,
        "calories_burned": calories_burned,
        "muscle_group": muscle_group_name,
        "difficulty": difficulty_name,
        "muscle_group_obj": muscle_group,
        "difficulty_obj": difficulty,
    }
    return render(request, "workouts/workout_result.html", context)

from django.shortcuts import redirect

@login_required
def save_workout(request):
    if request.method == 'POST':
        muscle_group_id = request.POST.get('muscle_group_id')
        difficulty_id = request.POST.get('difficulty_id')
        num_exercises = request.POST.get('num_exercises')
        exercise_ids = request.POST.getlist('exercise_ids')
        slots = request.POST.getlist('slots')
        
        mg = MuscleGroup.objects.filter(pk=muscle_group_id).first() if muscle_group_id else None
        diff = DifficultyLevel.objects.filter(pk=difficulty_id).first() if difficulty_id else None
        
        workout = SavedWorkout.objects.create(
            user=request.user,
            target_muscle_group=mg,
            difficulty=diff,
            num_exercises=int(num_exercises) if num_exercises else len(exercise_ids)
        )
        
        for i, (ex_id, slot) in enumerate(zip(exercise_ids, slots)):
            ex = Exercise.objects.get(pk=ex_id)
            SavedWorkoutExercise.objects.create(
                saved_workout=workout,
                exercise=ex,
                exercise_order=i+1,
                slot_type=slot
            )
            
        return redirect('dashboard')
    return redirect('home')

@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    programs = WorkoutProgram.objects.filter(user=request.user, is_active=True).prefetch_related('workouts__workout_exercises__exercise')
    workouts = SavedWorkout.objects.filter(user=request.user, program__isnull=True).prefetch_related('workout_exercises__exercise')
        
    return render(request, 'workouts/dashboard.html', {
        'user_obj': request.user,
        'profile': profile,
        'programs': programs,
        'workouts': workouts
    })

def register_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        if not AuthUser.objects.filter(username=email).exists():
            user = AuthUser.objects.create_user(username=email, email=email, password=password, first_name=name)
            UserProfile.objects.create(user=user)
            login(request, user)
            return redirect('questionnaire')
    return render(request, 'workouts/register.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'workouts/login.html', {'error': 'Invalid credentials'})
    return render(request, 'workouts/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def questionnaire(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.age = request.POST.get('age')
        profile.weight_kg = request.POST.get('weight')
        profile.gender = request.POST.get('gender')
        
        diff_id = request.POST.get('difficulty')
        if diff_id: profile.fitness_level = DifficultyLevel.objects.get(pk=diff_id)
        
        goal_id = request.POST.get('goal')
        if goal_id: profile.primary_goal = GoalType.objects.get(pk=goal_id)
        
        profile.preferred_split = request.POST.get('split')
        profile.days_per_week = request.POST.get('days')
        
        equip_ids = request.POST.getlist('equipment')
        if equip_ids:
            profile.available_equipment.set(Equipment.objects.filter(pk__in=equip_ids))
            
        profile.save()
        return redirect('generate_program')
        
    difficulties = DifficultyLevel.objects.all()
    goals = GoalType.objects.all()
    equipment = Equipment.objects.all()
    return render(request, 'workouts/questionnaire.html', {
        'difficulties': difficulties,
        'goals': goals,
        'equipment': equipment
    })

@login_required
def generate_program(request):
    profile = request.user.profile
    split = profile.preferred_split or 'PPL'
    
    # Optional logic: deactivate old active programs
    WorkoutProgram.objects.filter(user=request.user, is_active=True).update(is_active=False)
    
    program = WorkoutProgram.objects.create(
        user=request.user,
        name=f"My 8-Week {split} Plan"
    )
    
    if split == 'PPL':
        days = ['Push Day', 'Pull Day', 'Legs Day']
    elif split == 'UpperLower':
        days = ['Upper Day', 'Lower Day', 'Upper Day', 'Lower Day']
    elif split == 'BroSplit':
        days = ['Chest Day', 'Back Day', 'Shoulder Day', 'Legs Day', 'Arm Day']
    else:
        days = ['Full Body', 'Full Body', 'Full Body']
        
    # Trim or loop based on days_per_week
    target_days = profile.days_per_week or 3
    final_days = [days[i % len(days)] for i in range(target_days)]
    
    base_qs = Exercise.objects.all()
    user_equipment = profile.available_equipment.all()
    if user_equipment.exists():
        base_qs = base_qs.filter(exercise_equipment__equipment__in=user_equipment)
    if profile.fitness_level:
        base_qs = base_qs.filter(difficulty=profile.fitness_level)
    
    import random
    
    def get_optimal_exercises(day_name, base_qs):
        def get_for_muscle(muscle_name, count, is_compound=None, exclude_ids=[]):
            qs = base_qs.filter(exercise_muscle_groups__muscle_group__name=muscle_name, exercise_muscle_groups__role='primary')
            if is_compound is not None:
                qs = qs.filter(is_compound=is_compound)
            qs = qs.exclude(pk__in=exclude_ids).distinct()
            lst = list(qs)
            random.shuffle(lst)
            return lst[:count]
            
        selected = []
        used_ids = []
        
        def add_ex(lst, role):
            for ex in lst:
                if ex.pk not in used_ids:
                    selected.append((ex, role))
                    used_ids.append(ex.pk)
                    
        if 'Push' in day_name or 'Chest' in day_name:
            add_ex(get_for_muscle('Chest', 1, is_compound=True), 'compound')
            add_ex(get_for_muscle('Chest', 1, is_compound=False, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Shoulders', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Triceps', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Shoulders', 1, exclude_ids=used_ids), 'targeted')
            
        elif 'Pull' in day_name or 'Back' in day_name:
            add_ex(get_for_muscle('Back', 1, is_compound=True), 'compound')
            add_ex(get_for_muscle('Back', 1, is_compound=False, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Biceps', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Rear Delts', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Core', 1, exclude_ids=used_ids), 'targeted')
            
        elif 'Legs' in day_name or 'Lower' in day_name:
            add_ex(get_for_muscle('Quads', 1, is_compound=True), 'compound')
            add_ex(get_for_muscle('Hamstrings', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Glutes', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Calves', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Quads', 1, exclude_ids=used_ids), 'targeted')
            
        elif 'Upper' in day_name:
            add_ex(get_for_muscle('Chest', 1, is_compound=True), 'compound')
            add_ex(get_for_muscle('Back', 1, is_compound=True, exclude_ids=used_ids), 'compound')
            add_ex(get_for_muscle('Shoulders', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Biceps', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Triceps', 1, exclude_ids=used_ids), 'targeted')
            
        else: # Full body or fallback
            add_ex(get_for_muscle('Quads', 1, is_compound=True), 'compound')
            add_ex(get_for_muscle('Chest', 1, is_compound=True, exclude_ids=used_ids), 'compound')
            add_ex(get_for_muscle('Back', 1, is_compound=True, exclude_ids=used_ids), 'compound')
            add_ex(get_for_muscle('Shoulders', 1, exclude_ids=used_ids), 'targeted')
            add_ex(get_for_muscle('Core', 1, exclude_ids=used_ids), 'targeted')

        # Strict padding within the day's movement category
        if len(selected) < 5:
            pad_qs = base_qs.exclude(pk__in=used_ids)
            if 'Push' in day_name or 'Chest' in day_name:
                pad_qs = pad_qs.filter(exercise_muscle_groups__muscle_group__movement_category='Push', exercise_muscle_groups__role='primary')
            elif 'Pull' in day_name or 'Back' in day_name:
                pad_qs = pad_qs.filter(exercise_muscle_groups__muscle_group__movement_category='Pull', exercise_muscle_groups__role='primary')
            elif 'Legs' in day_name or 'Lower' in day_name:
                pad_qs = pad_qs.filter(exercise_muscle_groups__muscle_group__movement_category='Legs', exercise_muscle_groups__role='primary')
            elif 'Upper' in day_name:
                pad_qs = pad_qs.filter(exercise_muscle_groups__muscle_group__region='Upper Body', exercise_muscle_groups__role='primary')
                
            pad_qs = pad_qs.distinct()
            pad_list = list(pad_qs)
            random.shuffle(pad_list)
            for ex in pad_list[:5-len(selected)]:
                selected.append((ex, 'targeted'))
                used_ids.append(ex.pk)
                
        # Loose padding (ignore user equipment/difficulty, but STRICTLY keep the correct muscle category)
        if len(selected) < 5:
            upad = Exercise.objects.exclude(pk__in=used_ids)
            if 'Push' in day_name or 'Chest' in day_name:
                upad = upad.filter(exercise_muscle_groups__muscle_group__movement_category='Push', exercise_muscle_groups__role='primary')
            elif 'Pull' in day_name or 'Back' in day_name:
                upad = upad.filter(exercise_muscle_groups__muscle_group__movement_category='Pull', exercise_muscle_groups__role='primary')
            elif 'Legs' in day_name or 'Lower' in day_name:
                upad = upad.filter(exercise_muscle_groups__muscle_group__movement_category='Legs', exercise_muscle_groups__role='primary')
            elif 'Upper' in day_name:
                upad = upad.filter(exercise_muscle_groups__muscle_group__region='Upper Body', exercise_muscle_groups__role='primary')
                
            upad = upad.distinct()
            ulist = list(upad)
            random.shuffle(ulist)
            for ex in ulist[:5-len(selected)]:
                selected.append((ex, 'targeted'))
                used_ids.append(ex.pk)
                
        return selected[:5]

    for i, day_name in enumerate(final_days):
        workout = SavedWorkout.objects.create(
            user=request.user,
            program=program,
            day_number=i+1,
            day_name=day_name,
            num_exercises=5
        )
        
        exercises_to_save = get_optimal_exercises(day_name, base_qs)
        
        for j, (ex, slot) in enumerate(exercises_to_save):
            SavedWorkoutExercise.objects.create(
                saved_workout=workout,
                exercise=ex,
                exercise_order=j+1,
                slot_type=slot
            )
        
    return redirect('dashboard')


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

@login_required
def add_workout_exercise(request, workout_id):
    workout = get_object_or_404(SavedWorkout, pk=workout_id, user=request.user)
    
    used_ids = [we.exercise.pk for we in workout.workout_exercises.all()]
    base_qs = Exercise.objects.all()
    
    profile = getattr(request.user, 'profile', None)
    if profile:
        user_equipment = profile.available_equipment.all()
        if user_equipment.exists():
            base_qs = base_qs.filter(exercise_equipment__equipment__in=user_equipment)
        if profile.fitness_level:
            base_qs = base_qs.filter(difficulty=profile.fitness_level)

    pad_qs = base_qs.exclude(pk__in=used_ids)
    
    day_name = workout.day_name or ""
    if 'Push' in day_name or 'Chest' in day_name:
        pad_qs = pad_qs.filter(exercise_muscle_groups__muscle_group__movement_category='Push', exercise_muscle_groups__role='primary')
    elif 'Pull' in day_name or 'Back' in day_name:
        pad_qs = pad_qs.filter(exercise_muscle_groups__muscle_group__movement_category='Pull', exercise_muscle_groups__role='primary')
    elif 'Legs' in day_name or 'Lower' in day_name:
        pad_qs = pad_qs.filter(exercise_muscle_groups__muscle_group__movement_category='Legs', exercise_muscle_groups__role='primary')
    elif 'Upper' in day_name:
        pad_qs = pad_qs.filter(exercise_muscle_groups__muscle_group__region='Upper Body', exercise_muscle_groups__role='primary')
        
    pad_qs = pad_qs.distinct()
    pad_list = list(pad_qs)
    
    import random
    random.shuffle(pad_list)
    new_ex = pad_list[0] if pad_list else None
    
    if not new_ex:
        # Ultimate fallback ignoring equipment/difficulty but still matching muscle group
        upad = Exercise.objects.exclude(pk__in=used_ids)
        if 'Push' in day_name or 'Chest' in day_name:
            upad = upad.filter(exercise_muscle_groups__muscle_group__movement_category='Push', exercise_muscle_groups__role='primary')
        elif 'Pull' in day_name or 'Back' in day_name:
            upad = upad.filter(exercise_muscle_groups__muscle_group__movement_category='Pull', exercise_muscle_groups__role='primary')
        elif 'Legs' in day_name or 'Lower' in day_name:
            upad = upad.filter(exercise_muscle_groups__muscle_group__movement_category='Legs', exercise_muscle_groups__role='primary')
        elif 'Upper' in day_name:
            upad = upad.filter(exercise_muscle_groups__muscle_group__region='Upper Body', exercise_muscle_groups__role='primary')
            
        upad = upad.distinct()
        ulist = list(upad)
        random.shuffle(ulist)
        new_ex = ulist[0] if ulist else None
        
    if new_ex:
        order = workout.workout_exercises.count() + 1
        SavedWorkoutExercise.objects.create(
            saved_workout=workout,
            exercise=new_ex,
            exercise_order=order,
            slot_type='targeted'
        )
        
    return redirect('dashboard')

@login_required
def swap_workout_exercise(request, we_id):
    we = get_object_or_404(SavedWorkoutExercise, pk=we_id, saved_workout__user=request.user)
    workout = we.saved_workout
    
    used_ids = [w.exercise.pk for w in workout.workout_exercises.all()]
    primary_muscle_name = we.primary_muscle()
    
    base_qs = Exercise.objects.exclude(pk__in=used_ids)
    profile = getattr(request.user, 'profile', None)
    if profile:
        user_equipment = profile.available_equipment.all()
        if user_equipment.exists():
            base_qs = base_qs.filter(exercise_equipment__equipment__in=user_equipment)
        if profile.fitness_level:
            base_qs = base_qs.filter(difficulty=profile.fitness_level)

    swap_qs = base_qs.filter(
        exercise_muscle_groups__muscle_group__name=primary_muscle_name,
        exercise_muscle_groups__role='primary',
        is_compound=(we.slot_type == 'compound')
    ).distinct()
    
    import random
    swap_list = list(swap_qs)
    random.shuffle(swap_list)
    new_ex = swap_list[0] if swap_list else None
    
    # If no strict match, drop the compound requirement
    if not new_ex:
        swap_qs = base_qs.filter(
            exercise_muscle_groups__muscle_group__name=primary_muscle_name,
            exercise_muscle_groups__role='primary'
        ).distinct()
        swap_list = list(swap_qs)
        random.shuffle(swap_list)
        new_ex = swap_list[0] if swap_list else None
        
    # If still no match, drop user constraints
    if not new_ex:
        upad = Exercise.objects.exclude(pk__in=used_ids).filter(
            exercise_muscle_groups__muscle_group__name=primary_muscle_name,
            exercise_muscle_groups__role='primary'
        ).distinct()
        ulist = list(upad)
        random.shuffle(ulist)
        new_ex = ulist[0] if ulist else None
        
    if new_ex:
        we.exercise = new_ex
        we.save()
        
    return redirect('dashboard')

@login_required
def remove_workout_exercise(request, we_id):
    we = get_object_or_404(SavedWorkoutExercise, pk=we_id, saved_workout__user=request.user)
    we.delete()
    return redirect('dashboard')