import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dbproject.settings')
django.setup()

from workouts.models import FoodItem, GoalType

def run():
    print("Seeding Nutrition Data...")
    
    # Get goal types
    hypertrophy = GoalType.objects.filter(name__icontains='Hypertrophy').first()
    strength = GoalType.objects.filter(name__icontains='Strength').first()
    endurance = GoalType.objects.filter(name__icontains='Endurance').first()
    
    foods = [
        # Hypertrophy (Muscle Building - High Protein, Mod Carbs)
        {"name": "Chicken Breast", "calories_per_100g": 165, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6, "category": "Protein", "goal": hypertrophy},
        {"name": "Greek Yogurt", "calories_per_100g": 59, "protein_g": 10.0, "carbs_g": 3.6, "fat_g": 0.4, "category": "Dairy", "goal": hypertrophy},
        {"name": "Cottage Cheese", "calories_per_100g": 98, "protein_g": 11.0, "carbs_g": 3.4, "fat_g": 4.3, "category": "Dairy", "goal": hypertrophy},
        {"name": "Whey Protein Shake", "calories_per_100g": 350, "protein_g": 70.0, "carbs_g": 10.0, "fat_g": 3.0, "category": "Supplement", "goal": hypertrophy},
        {"name": "Lean Beef", "calories_per_100g": 250, "protein_g": 26.0, "carbs_g": 0.0, "fat_g": 15.0, "category": "Protein", "goal": hypertrophy},

        # Strength (High Calorie, High Protein, Mod Fat/Carbs)
        {"name": "Steak", "calories_per_100g": 271, "protein_g": 25.0, "carbs_g": 0.0, "fat_g": 19.0, "category": "Protein", "goal": strength},
        {"name": "Eggs", "calories_per_100g": 155, "protein_g": 13.0, "carbs_g": 1.1, "fat_g": 11.0, "category": "Protein", "goal": strength},
        {"name": "Peanut Butter", "calories_per_100g": 588, "protein_g": 25.0, "carbs_g": 20.0, "fat_g": 50.0, "category": "Fat", "goal": strength},
        {"name": "Whole Milk", "calories_per_100g": 61, "protein_g": 3.2, "carbs_g": 4.8, "fat_g": 3.3, "category": "Dairy", "goal": strength},
        {"name": "Avocado", "calories_per_100g": 160, "protein_g": 2.0, "carbs_g": 8.5, "fat_g": 14.7, "category": "Fat", "goal": strength},

        # Endurance (High Carb for Glycogen Replenishment)
        {"name": "Oatmeal", "calories_per_100g": 68, "protein_g": 2.4, "carbs_g": 12.0, "fat_g": 1.4, "category": "Carb", "goal": endurance},
        {"name": "Brown Rice", "calories_per_100g": 111, "protein_g": 2.6, "carbs_g": 23.0, "fat_g": 0.9, "category": "Carb", "goal": endurance},
        {"name": "Sweet Potato", "calories_per_100g": 86, "protein_g": 1.6, "carbs_g": 20.0, "fat_g": 0.1, "category": "Carb", "goal": endurance},
        {"name": "Banana", "calories_per_100g": 89, "protein_g": 1.1, "carbs_g": 23.0, "fat_g": 0.3, "category": "Fruit", "goal": endurance},
        {"name": "Quinoa", "calories_per_100g": 120, "protein_g": 4.4, "carbs_g": 21.3, "fat_g": 1.9, "category": "Carb", "goal": endurance},
    ]

    FoodItem.objects.all().delete()
    for item in foods:
        FoodItem.objects.create(
            name=item["name"],
            calories_per_100g=item["calories_per_100g"],
            protein_g=item["protein_g"],
            carbs_g=item["carbs_g"],
            fat_g=item["fat_g"],
            category=item["category"],
            ideal_for_goal=item["goal"]
        )
    print(f"Seeded {FoodItem.objects.count()} food items.")

if __name__ == '__main__':
    run()
