def calculate_bmi(weight_kg, height_cm):
    height_m = height_cm / 100

    if height_m <= 0:
        return 0

    bmi = weight_kg / (height_m ** 2)

    return round(bmi, 2)


def get_bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"

    elif bmi < 25:
        return "Normal weight"

    elif bmi < 30:
        return "Overweight"

    else:
        return "Obesity"


def calculate_bmr(age, sex, weight_kg, height_cm):
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.
    """

    if sex.lower() == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5

    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    return round(bmr, 2)


def calculate_tdee(bmr, activity_level):
    """
    Calculate Total Daily Energy Expenditure.
    """

    activity_multipliers = {
        "sedentary": 1.2,
        "lightly_active": 1.375,
        "moderately_active": 1.55,
        "very_active": 1.725,
        "extra_active": 1.9
    }

    multiplier = activity_multipliers.get(activity_level, 1.2)

    return round(bmr * multiplier, 2)


def calculate_calorie_target(tdee, goal_type):
    """
    Adjust calories based on fitness goal.
    """

    if goal_type == "Lose Weight":
        calories = tdee - 500

    elif goal_type == "Gain Weight":
        calories = tdee + 300

    else:
        calories = tdee

    # Prevent extremely low calorie targets
    calories = max(calories, 1200)

    return round(calories)


def calculate_macros(calories, weight_kg):
    """
    Calculate daily protein, fat and carbohydrate targets.
    """

    # Protein: approximately 1.6g per kg body weight
    protein_g = weight_kg * 1.6

    # Fat: approximately 25% of total calories
    fat_calories = calories * 0.25
    fat_g = fat_calories / 9

    # Remaining calories come from carbohydrates
    protein_calories = protein_g * 4
    carb_calories = calories - protein_calories - fat_calories

    carb_g = carb_calories / 4

    return {
        "protein": round(protein_g, 2),
        "fat": round(fat_g, 2),
        "carbs": round(carb_g, 2)
    }


def calculate_fitness_targets(
    age,
    sex,
    weight_kg,
    height_cm,
    activity_level,
    goal_type
):
    """
    Calculate BMR, TDEE, calories and macros together.
    """

    bmr = calculate_bmr(
        age,
        sex,
        weight_kg,
        height_cm
    )

    tdee = calculate_tdee(
        bmr,
        activity_level
    )

    calories = calculate_calorie_target(
        tdee,
        goal_type
    )

    macros = calculate_macros(
        calories,
        weight_kg
    )

    return {
        "bmr": bmr,
        "tdee": tdee,
        "calories": calories,
        "protein": macros["protein"],
        "fat": macros["fat"],
        "carbs": macros["carbs"]
    }