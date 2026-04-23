# workouts/admin.py
#
# Register all models with the Django admin panel.
# This lets you browse, add, and edit records directly through /admin/.
# Extremely useful during development and for the class demo.

from django.contrib import admin
from .models import (
    MuscleGroup,
    DifficultyLevel,
    MovementType,
    GoalType,
    Equipment,
    ExerciseImage,
    Exercise,
    ExerciseMuscleGroup,
    ExerciseEquipment,
    ExerciseGoalProfile,
    MuscleGroupRelationship,
    UserProfile,
    WorkoutProgram,
    SavedWorkout,
    SavedWorkoutExercise,
)


# ---------------------------------------------------------------------------
# Inline classes — show related records inside the Exercise admin page
# ---------------------------------------------------------------------------

class ExerciseMuscleGroupInline(admin.TabularInline):
    """Shows all muscle group links directly on the Exercise edit page."""
    model = ExerciseMuscleGroup
    extra = 1                   # number of empty rows shown for quick adding


class ExerciseEquipmentInline(admin.TabularInline):
    """Shows all equipment links directly on the Exercise edit page."""
    model = ExerciseEquipment
    extra = 1


class ExerciseGoalProfileInline(admin.TabularInline):
    """Shows all goal profiles (sets/reps by goal) on the Exercise edit page."""
    model = ExerciseGoalProfile
    extra = 1


# ---------------------------------------------------------------------------
# Main model admin registrations
# ---------------------------------------------------------------------------

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display  = ('name', 'difficulty', 'movement_type', 'is_compound')
    list_filter   = ('difficulty', 'is_compound', 'movement_type')
    search_fields = ('name', 'description')
    inlines       = [ExerciseMuscleGroupInline, ExerciseEquipmentInline, ExerciseGoalProfileInline]


@admin.register(MuscleGroup)
class MuscleGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'movement_category')
    list_filter  = ('region', 'movement_category')


@admin.register(DifficultyLevel)
class DifficultyLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'order_rank')


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(MovementType)
class MovementTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(GoalType)
class GoalTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(ExerciseImage)
class ExerciseImageAdmin(admin.ModelAdmin):
    list_display = ('caption', 'image_path', 'style_type')


@admin.register(MuscleGroupRelationship)
class MuscleGroupRelationshipAdmin(admin.ModelAdmin):
    list_display = ('source_muscle_group', 'related_muscle_group', 'relationship_type')
    list_filter  = ('relationship_type',)


@admin.register(ExerciseGoalProfile)
class ExerciseGoalProfileAdmin(admin.ModelAdmin):
    list_display = ('exercise', 'goal_type', 'default_sets', 'rep_low', 'rep_high', 'duration_seconds')
    list_filter  = ('goal_type',)


# Simple registrations for junction tables (useful for data inspection)
admin.site.register(ExerciseMuscleGroup)
admin.site.register(ExerciseEquipment)

# Persistence models (stretch goal)
admin.site.register(UserProfile)
admin.site.register(WorkoutProgram)
admin.site.register(SavedWorkout)
admin.site.register(SavedWorkoutExercise)
