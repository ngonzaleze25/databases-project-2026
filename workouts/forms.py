# workouts/forms.py
#
# Two forms used across the app:
#   WorkoutBuilderForm  — the main form on the home page
#   ExerciseFilterForm  — the filter bar on the exercise browser page

from django import forms
from .models import MuscleGroup, DifficultyLevel, Equipment, MovementType, GoalType


class WorkoutBuilderForm(forms.Form):
    """
    The main workout generation form.
    Submitted via POST to /workout/.
    All fields except goal_type are required.
    """

    muscle_group = forms.ModelChoiceField(
        queryset=MuscleGroup.objects.all(),
        empty_label='— Select muscle group —',
        label='Target Muscle Group',
    )

    difficulty = forms.ModelChoiceField(
        queryset=DifficultyLevel.objects.all().order_by('order_rank'),
        empty_label='— Select difficulty —',
        label='Difficulty Level',
    )

    equipment = forms.ModelMultipleChoiceField(
        queryset=Equipment.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Available Equipment',
        help_text='Check all equipment you have access to.',
    )

    num_exercises = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=5,
        label='Number of Exercises',
    )

    goal_type = forms.ModelChoiceField(
        queryset=GoalType.objects.all(),
        required=False,
        empty_label='— Optional: select goal —',
        label='Training Goal',
    )


class ExerciseFilterForm(forms.Form):
    """
    GET-based filter form on the exercise browser page.
    All fields are optional — blank means 'show all'.
    """

    muscle_group = forms.ModelChoiceField(
        queryset=MuscleGroup.objects.all(),
        required=False,
        empty_label='All muscle groups',
        label='Muscle Group',
    )

    difficulty = forms.ModelChoiceField(
        queryset=DifficultyLevel.objects.all().order_by('order_rank'),
        required=False,
        empty_label='All difficulties',
        label='Difficulty',
    )

    equipment = forms.ModelChoiceField(
        queryset=Equipment.objects.all(),
        required=False,
        empty_label='All equipment',
        label='Equipment',
    )

    movement_type = forms.ModelChoiceField(
        queryset=MovementType.objects.all(),
        required=False,
        empty_label='All movement types',
        label='Movement Type',
    )

    IS_COMPOUND_CHOICES = [
        ('', 'All types'),
        ('true', 'Compound only'),
        ('false', 'Isolation only'),
    ]
    is_compound = forms.ChoiceField(
        choices=IS_COMPOUND_CHOICES,
        required=False,
        label='Exercise Type',
    )

    def clean_is_compound(self):
        """Convert string 'true'/'false' to Python bool or None."""
        val = self.cleaned_data.get('is_compound')
        if val == 'true':
            return True
        if val == 'false':
            return False
        return None
