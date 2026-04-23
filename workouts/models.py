# workouts/models.py
#
# Workout Builder — Django models
# Designed for an undergraduate databases + Django course.
#
# Schema overview:
#   Lookup tables:  MuscleGroup, DifficultyLevel, MovementType, GoalType, Equipment
#   Media:          ExerciseImage
#   Core:           Exercise  (the central table)
#   Junction tables: ExerciseMuscleGroup, ExerciseEquipment, MuscleGroupRelationship,
#                    ExerciseGoalProfile
#   Persistence:    User, SavedWorkout, SavedWorkoutExercise  (stretch goal)

from django.db import models


# ---------------------------------------------------------------------------
# 1. Lookup / reference tables
# ---------------------------------------------------------------------------

class MuscleGroup(models.Model):
    """
    Stores muscle categories (e.g. Chest, Back, Quads).
    Used both as the user's selection target and as the axis for analytics.
    """
    muscle_group_id = models.AutoField(primary_key=True)
    name            = models.CharField(max_length=100)
    region          = models.CharField(max_length=100)          # e.g. "Upper Body"
    movement_category = models.CharField(max_length=100)        # e.g. "Push", "Pull", "Legs"

    class Meta:
        ordering = ['movement_category', 'name']

    def __str__(self):
        return self.name


class DifficultyLevel(models.Model):
    """
    Beginner / Intermediate / Advanced.
    order_rank lets you sort from easiest to hardest in ORM queries.
    """
    difficulty_id = models.AutoField(primary_key=True)
    name          = models.CharField(max_length=50)
    order_rank    = models.PositiveSmallIntegerField()           # 1 = easiest

    class Meta:
        ordering = ['order_rank']

    def __str__(self):
        return self.name


class MovementType(models.Model):
    """
    Classifies the movement pattern: Press, Row, Squat, Hinge, etc.
    One-to-many with Exercise.
    """
    movement_type_id = models.AutoField(primary_key=True)
    name             = models.CharField(max_length=100)
    description      = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class GoalType(models.Model):
    """
    Training goal: Strength, Hypertrophy, Endurance.
    Optional FK on Exercise; can later power ExerciseGoalProfile if needed.
    """
    goal_type_id = models.AutoField(primary_key=True)
    name         = models.CharField(max_length=100)
    description  = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Equipment(models.Model):
    """
    Equipment types: Bodyweight, Dumbbell, Barbell, Cable, Machine, etc.
    Connected to Exercise through the ExerciseEquipment junction table.
    """
    equipment_id = models.AutoField(primary_key=True)
    name         = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 2. Media table
# ---------------------------------------------------------------------------

class ExerciseImage(models.Model):
    """
    Stores a reference (file path) to an exercise image, NOT the binary file.
    The app reads image_path and uses it as a static file URL.
    """
    image_id        = models.AutoField(primary_key=True)
    image_path      = models.CharField(max_length=300)          # e.g. "images/exercises/pushup.png"
    caption         = models.CharField(max_length=200, blank=True)
    style_type      = models.CharField(max_length=100, blank=True)    # e.g. "anatomical_bw_red"
    highlight_notes = models.TextField(blank=True)

    def __str__(self):
        return self.caption or self.image_path


# ---------------------------------------------------------------------------
# 3. Core exercise table
# ---------------------------------------------------------------------------

class Exercise(models.Model):
    """
    The central table of the entire project.
    Every page — workout generator, exercise browser, detail, analytics — queries this.

    Relationships:
      - difficulty    → DifficultyLevel (one-to-many)
      - movement_type → MovementType (one-to-many)
      - image         → ExerciseImage (one-to-one-ish, nullable)
      - muscles       → MuscleGroup through ExerciseMuscleGroup (many-to-many)
      - equipment     → Equipment through ExerciseEquipment (many-to-many)
      - goal profiles → GoalType through ExerciseGoalProfile (many-to-many)
                        Each profile stores the sets/reps/duration for that goal.

    Note: goal_type is NOT stored directly on Exercise.
    The same exercise can have different prescriptions for different goals,
    so that data belongs in ExerciseGoalProfile.
    """
    exercise_id   = models.AutoField(primary_key=True)
    name          = models.CharField(max_length=200)
    description   = models.TextField(blank=True)
    difficulty    = models.ForeignKey(
                        DifficultyLevel,
                        on_delete=models.PROTECT,
                        related_name='exercises'
                    )
    movement_type = models.ForeignKey(
                        MovementType,
                        on_delete=models.PROTECT,
                        related_name='exercises'
                    )
    image         = models.ForeignKey(
                        ExerciseImage,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='exercises'
                    )
    is_compound   = models.BooleanField(default=False)
    default_sets  = models.PositiveSmallIntegerField(default=3)
    default_reps  = models.PositiveSmallIntegerField(default=10)
    instructions  = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 4. Junction tables  (many-to-many relationships)
# ---------------------------------------------------------------------------

class ExerciseMuscleGroup(models.Model):
    """
    Links an exercise to a muscle group and specifies its role.
    This is the most important junction table in the project.

    Examples:
      Push-Up → Chest (primary), Triceps (secondary), Core (stabilizer)
      Barbell Row → Back (primary), Biceps (secondary), Rear Delts (secondary)

    The 'role' field is critical for workout generation:
      - primary   → used to match the user's selected muscle
      - secondary → displayed on the detail page
      - stabilizer → displayed on the detail page
    """

    class Role(models.TextChoices):
        PRIMARY    = 'primary',    'Primary'
        SECONDARY  = 'secondary',  'Secondary'
        STABILIZER = 'stabilizer', 'Stabilizer'

    exercise     = models.ForeignKey(
                       Exercise,
                       on_delete=models.CASCADE,
                       related_name='exercise_muscle_groups'
                   )
    muscle_group = models.ForeignKey(
                       MuscleGroup,
                       on_delete=models.CASCADE,
                       related_name='exercise_muscle_groups'
                   )
    role         = models.CharField(
                       max_length=20,
                       choices=Role.choices,
                       default=Role.PRIMARY
                   )

    class Meta:
        # An exercise can only be linked to the same muscle once per role.
        # This prevents duplicate rows like (Push-Up, Chest, primary) twice.
        constraints = [
            models.UniqueConstraint(
                fields=['exercise', 'muscle_group', 'role'],
                name='unique_exercise_muscle_role'
            )
        ]

    def __str__(self):
        return f"{self.exercise.name} — {self.muscle_group.name} ({self.role})"


class ExerciseEquipment(models.Model):
    """
    Links an exercise to every equipment type it is compatible with.
    This is a proper many-to-many design:
      Push-Up → Bodyweight
      Dumbbell Bench Press → Dumbbell
      Cable Row → Cable
      Barbell Row → Barbell, Cable  (two rows, same exercise)

    The workout generator uses this table to filter exercises by the user's
    available equipment selection.
    """
    exercise  = models.ForeignKey(
                    Exercise,
                    on_delete=models.CASCADE,
                    related_name='exercise_equipment'
                )
    equipment = models.ForeignKey(
                    Equipment,
                    on_delete=models.CASCADE,
                    related_name='exercise_equipment'
                )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['exercise', 'equipment'],
                name='unique_exercise_equipment'
            )
        ]

    def __str__(self):
        return f"{self.exercise.name} — {self.equipment.name}"


class MuscleGroupRelationship(models.Model):
    """
    Stores relationships between muscle groups.
    This is the table that enables the 'supporting slot' logic in workout generation.

    Examples:
      Chest → Triceps   (supporting)
      Chest → Shoulders (supporting)
      Back  → Biceps    (supporting)
      Quads → Core      (stabilizer)

    Without this table, supporting muscle logic would be hardcoded in Python.
    With this table, the database carries the relationship data — more academic,
    more database-appropriate, and easier to explain in a presentation.
    """

    class RelationshipType(models.TextChoices):
        SUPPORTING = 'supporting', 'Supporting'
        STABILIZER = 'stabilizer', 'Stabilizer'
        SYNERGIST  = 'synergist',  'Synergist'

    source_muscle_group  = models.ForeignKey(
                               MuscleGroup,
                               on_delete=models.CASCADE,
                               related_name='outgoing_relationships'
                           )
    related_muscle_group = models.ForeignKey(
                               MuscleGroup,
                               on_delete=models.CASCADE,
                               related_name='incoming_relationships'
                           )
    relationship_type    = models.CharField(
                               max_length=20,
                               choices=RelationshipType.choices,
                               default=RelationshipType.SUPPORTING
                           )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['source_muscle_group', 'related_muscle_group', 'relationship_type'],
                name='unique_muscle_relationship'
            )
        ]

    def __str__(self):
        return (
            f"{self.source_muscle_group.name} → "
            f"{self.related_muscle_group.name} ({self.relationship_type})"
        )


class ExerciseGoalProfile(models.Model):
    """
    Junction table between Exercise and GoalType.

    This replaces the simple nullable goal_type FK that would have sat on Exercise.
    That approach broke down because the SAME exercise can appear under multiple goals
    with completely different prescriptions:

      Barbell Bench Press + Strength   → 5 sets × 3-5 reps, 180s rest
      Barbell Bench Press + Hypertrophy → 4 sets × 8-12 reps, 90s rest
      Barbell Bench Press + Endurance  → 3 sets × 15-20 reps, 45s rest

    By using a junction table, all three rows can exist independently.
    The workout generator picks the right profile based on the user's selected goal,
    then uses its sets/reps/duration to populate the result page.

    For cardio exercises, rep_low/rep_high will be null and duration_seconds
    will be set instead.
    """
    exercise         = models.ForeignKey(
                           Exercise,
                           on_delete=models.CASCADE,
                           related_name='goal_profiles'
                       )
    goal_type        = models.ForeignKey(
                           GoalType,
                           on_delete=models.CASCADE,
                           related_name='exercise_profiles'
                       )
    default_sets     = models.PositiveSmallIntegerField()
    rep_low          = models.PositiveSmallIntegerField(null=True, blank=True)   # null for cardio/timed
    rep_high         = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)        # null for rep-based
    rest_seconds     = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        # One prescription per exercise per goal. No duplicates.
        constraints = [
            models.UniqueConstraint(
                fields=['exercise', 'goal_type'],
                name='unique_exercise_goal_profile'
            )
        ]

    def __str__(self):
        return f"{self.exercise.name} — {self.goal_type.name}"

    def rep_display(self):
        """
        Helper used in templates to show either 'X-Y reps' or 'Xs' cleanly.
        Call it like: {{ profile.rep_display }}
        """
        if self.duration_seconds:
            return f"{self.duration_seconds}s"
        if self.rep_low and self.rep_high:
            return f"{self.rep_low}–{self.rep_high} reps"
        return f"{self.rep_low or self.rep_high} reps"


# ---------------------------------------------------------------------------
# 5. Persistence models (stretch goal — include only if time allows)
# ---------------------------------------------------------------------------

from django.contrib.auth.models import User as AuthUser

class UserProfile(models.Model):
    """
    Extended user profile for the questionnaire and program generation.
    """
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE, related_name='profile')
    age = models.PositiveIntegerField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    fitness_level = models.ForeignKey(DifficultyLevel, on_delete=models.SET_NULL, null=True, blank=True)
    primary_goal = models.ForeignKey(GoalType, on_delete=models.SET_NULL, null=True, blank=True)
    available_equipment = models.ManyToManyField(Equipment, blank=True)
    preferred_split = models.CharField(max_length=50, null=True, blank=True)
    days_per_week = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.user.username

class WorkoutProgram(models.Model):
    """
    Represents an 8-week or custom multi-day workout plan.
    """
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='programs')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} for {self.user.username}"


class SavedWorkout(models.Model):
    """
    Records a generated workout session or a day in a WorkoutProgram.
    """
    user                  = models.ForeignKey(
                                AuthUser,
                                on_delete=models.CASCADE,
                                related_name='saved_workouts'
                            )
    program               = models.ForeignKey(
                                WorkoutProgram,
                                on_delete=models.CASCADE,
                                null=True, blank=True,
                                related_name='workouts'
                            )
    day_number            = models.PositiveIntegerField(null=True, blank=True)
    day_name              = models.CharField(max_length=50, null=True, blank=True)

    target_muscle_group   = models.ForeignKey(
                                MuscleGroup,
                                on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='saved_workouts'
                            )
    difficulty            = models.ForeignKey(
                                DifficultyLevel,
                                on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='saved_workouts'
                            )
    num_exercises         = models.PositiveSmallIntegerField()
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['program', 'day_number', '-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.day_name or self.target_muscle_group} ({self.created_at.date()})"


class SavedWorkoutExercise(models.Model):
    """
    Each row is one exercise inside a saved workout, in order.
    slot_type records the generation role that exercise was assigned.
    """

    class SlotType(models.TextChoices):
        COMPOUND   = 'compound',   'Compound'
        TARGETED   = 'targeted',   'Targeted'
        SUPPORTING = 'supporting', 'Supporting'

    saved_workout  = models.ForeignKey(
                         SavedWorkout,
                         on_delete=models.CASCADE,
                         related_name='workout_exercises'
                     )
    exercise       = models.ForeignKey(
                         Exercise,
                         on_delete=models.CASCADE,
                         related_name='saved_workout_exercises'
                     )
    exercise_order = models.PositiveSmallIntegerField()
    slot_type      = models.CharField(
                         max_length=20,
                         choices=SlotType.choices,
                         default=SlotType.TARGETED
                     )

    class Meta:
        ordering = ['exercise_order']
        constraints = [
            models.UniqueConstraint(
                fields=['saved_workout', 'exercise_order'],
                name='unique_workout_exercise_order'
            )
        ]

    def __str__(self):
        return f"#{self.exercise_order} {self.exercise.name} ({self.slot_type})"
        
    def primary_muscle(self):
        emg = self.exercise.exercise_muscle_groups.filter(role='primary').first()
        return emg.muscle_group.name if emg else "Mixed"
        
    def recommended_sets_reps(self):
        goal = None
        if self.saved_workout.user:
            profile = getattr(self.saved_workout.user, 'profile', None)
            if profile: goal = profile.primary_goal
            
        if goal:
            egp = self.exercise.exercise_goal_profiles.filter(goal_type=goal).first()
            if egp:
                if egp.duration_seconds:
                    return f"{egp.default_sets} sets x {egp.duration_seconds}s"
                return f"{egp.default_sets} sets of {egp.rep_low}-{egp.rep_high}"
                
        # Fallback
        return "3 sets of 8-12"


# ---------------------------------------------------------------------------
# 6. Nutrition Data Source (Ambition Project)
# ---------------------------------------------------------------------------

class FoodItem(models.Model):
    """
    Nutrition data source to combine with the workout builder.
    Provides post-workout meal recommendations based on the user's fitness goal.
    This demonstrates joining two distinct data domains (Workouts + Nutrition) to add value.
    """
    food_id           = models.AutoField(primary_key=True)
    name              = models.CharField(max_length=200)
    calories_per_100g = models.PositiveIntegerField()
    protein_g         = models.FloatField()
    carbs_g           = models.FloatField()
    fat_g             = models.FloatField()
    category          = models.CharField(max_length=100)  # e.g., 'Protein', 'Carb', 'Fat'
    
    # The crucial link between the Workout domain and Nutrition domain
    ideal_for_goal    = models.ForeignKey(
                            GoalType,
                            on_delete=models.SET_NULL,
                            null=True, blank=True,
                            related_name='recommended_foods'
                        )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

