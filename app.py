from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime

from config import Config
from werkzeug.security import generate_password_hash, check_password_hash

from utils.calculations import (
    calculate_bmi,
    get_bmi_category,
    calculate_fitness_targets
)
from utils.food_data import FOOD_DATA


app = Flask(__name__)
app.config.from_object(Config)


# =========================
# DATABASE CONNECTION
# =========================

def get_db_connection():

    connection = psycopg2.connect(
        host=app.config["DB_HOST"],
        port=app.config.get("DB_PORT", 5432),
        user=app.config["DB_USER"],
        password=app.config["DB_PASSWORD"],
        dbname=app.config["DB_NAME"]
    )

    return connection

# ========================================
# ADMIN DASHBOARD
# ========================================

@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    if session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        # Total users
        cursor.execute(
            """
            SELECT COUNT(*) AS total_users
            FROM users
            WHERE role = 'user'
            """
        )
        total_users = cursor.fetchone()["total_users"]

        # Total progress records
        cursor.execute(
            """
            SELECT COUNT(*) AS total_progress
            FROM daily_progress
            """
        )
        total_progress = cursor.fetchone()["total_progress"]

        # Total food records
        cursor.execute(
            """
            SELECT COUNT(*) AS total_food_logs
            FROM food_logs
            """
        )
        total_food_logs = cursor.fetchone()["total_food_logs"]

        # Total workouts
        cursor.execute(
            """
            SELECT COUNT(*) AS total_workouts
            FROM workouts
            """
        )
        total_workouts = cursor.fetchone()["total_workouts"]

        # Registered users
        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                role,
                created_at
            FROM users
            ORDER BY created_at DESC
            """
        )
        users = cursor.fetchall()

    except psycopg2.Error:

        cursor.close()
        connection.close()

        flash(
            "Unable to load admin dashboard.",
            "danger"
        )

        return redirect(url_for("dashboard"))

    cursor.close()
    connection.close()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_progress=total_progress,
        total_food_logs=total_food_logs,
        total_workouts=total_workouts,
        users=users
    )


# ========================================
# ADMIN DELETE USER
# ========================================

@app.route(
    "/admin/delete-user/<int:user_id>",
    methods=["POST"]
)
def admin_delete_user(user_id):

    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    if session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard"))

    # Prevent admin from deleting themselves
    if user_id == session["user_id"]:
        flash(
            "You cannot delete your own admin account.",
            "danger"
        )
        return redirect(url_for("admin_dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            DELETE FROM users
            WHERE id = %s
            AND role = 'user'
            """,
            (user_id,)
        )

        connection.commit()

        if cursor.rowcount == 0:
            flash(
                "User not found.",
                "warning"
            )
        else:
            flash(
                "User deleted successfully.",
                "success"
            )

    except psycopg2.Error:

        connection.rollback()

        flash(
            "Unable to delete user.",
            "danger"
        )

    cursor.close()
    connection.close()

    return redirect(url_for("admin_dashboard"))

# ==================================================
# ADMIN - USER ACTIVITY
# ==================================================

@app.route("/admin/user/<int:user_id>")
def admin_user_activity(user_id):

    # --------------------------------------------------
    # ADMIN AUTHENTICATION
    # --------------------------------------------------

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(
            url_for("login")
        )

    if session.get("user_role") != "admin":

        flash(
            "Admin access required.",
            "danger"
        )

        return redirect(
            url_for("dashboard")
        )


    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)


    try:

        # ==================================================
        # USER INFORMATION
        # ==================================================

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                role,
                created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()


        if not user:

            cursor.close()
            connection.close()

            flash(
                "User not found.",
                "warning"
            )

            return redirect(
                url_for("admin_dashboard")
            )


        # ==================================================
        # FITNESS GOAL
        # ==================================================

        cursor.execute(
            """
            SELECT
                age,
                sex,
                height_cm,
                starting_weight,
                target_weight,
                goal_type,
                activity_level,
                daily_calorie_target,
                daily_protein_target,
                daily_fat_target,
                daily_carb_target
            FROM fitness_goals
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,)
        )

        goal = cursor.fetchone()


        # ==================================================
        # DAILY PROGRESS
        # ==================================================

        cursor.execute(
            """
            SELECT
                id,
                date,
                weight_kg,
                bmi,
                water_liters,
                sleep_hours,
                steps,
                waist_cm,
                chest_cm
            FROM daily_progress
            WHERE user_id = %s
            ORDER BY date DESC
            """,
            (user_id,)
        )

        progress_records = cursor.fetchall()


        # ==================================================
        # NUTRITION LOGS
        # ==================================================

        cursor.execute(
            """
            SELECT
                id,
                date,
                food_name,
                quantity_g,
                calories,
                carbs_g,
                protein_g,
                fat_g,
                fiber_g
            FROM food_logs
            WHERE user_id = %s
            ORDER BY date DESC, id DESC
            """,
            (user_id,)
        )

        food_logs = cursor.fetchall()


        # ==================================================
        # WORKOUTS + EXERCISES + SETS
        # ==================================================

        cursor.execute(
            """
            SELECT
                workouts.id AS workout_id,
                workouts.workout_date,
                workouts.workout_name,
                workouts.duration_minutes,

                exercises.id AS exercise_id,
                exercises.exercise_name,

                exercise_sets.id AS set_id,
                exercise_sets.set_number,
                exercise_sets.reps,
                exercise_sets.weight_kg

            FROM workouts

            LEFT JOIN exercises
                ON workouts.id = exercises.workout_id

            LEFT JOIN exercise_sets
                ON exercises.id = exercise_sets.exercise_id

            WHERE workouts.user_id = %s

            ORDER BY
                workouts.workout_date DESC,
                workouts.id DESC,
                exercises.id ASC,
                exercise_sets.set_number ASC,
                exercise_sets.id ASC
            """,
            (user_id,)
        )

        workout_rows = cursor.fetchall()


        # ==================================================
        # BUILD NESTED WORKOUT DATA
        # ==================================================

        workouts = []

        workout_map = {}


        for row in workout_rows:

            workout_id = row["workout_id"]


            # Create workout if it doesn't exist

            if workout_id not in workout_map:

                workout = {
                    "id": workout_id,
                    "workout_date": row["workout_date"],
                    "workout_name": row["workout_name"],
                    "duration_minutes": row["duration_minutes"],
                    "exercises": []
                }

                workout_map[workout_id] = workout

                workouts.append(workout)


            workout = workout_map[workout_id]


            # Add exercise

            exercise_id = row["exercise_id"]


            if exercise_id is not None:

                existing_exercise = None


                for exercise in workout["exercises"]:

                    if exercise["id"] == exercise_id:

                        existing_exercise = exercise
                        break


                if existing_exercise is None:

                    existing_exercise = {
                        "id": exercise_id,
                        "exercise_name": row["exercise_name"],
                        "sets": []
                    }

                    workout["exercises"].append(
                        existing_exercise
                    )


                # Add set

                if row["set_id"] is not None:

                    existing_exercise["sets"].append(
                        {
                            "id": row["set_id"],
                            "set_number": row["set_number"],
                            "reps": row["reps"],
                            "weight_kg": row["weight_kg"]
                        }
                    )


        # ==================================================
        # CHART DATA
        # ==================================================

        # Progress charts

        progress_chart_records = list(
            reversed(progress_records)
        )


        progress_dates = [
            row["date"].strftime("%Y-%m-%d")
            for row in progress_chart_records
        ]


        weights = [
            float(row["weight_kg"])
            for row in progress_chart_records
        ]


        water = [
            float(row["water_liters"] or 0)
            for row in progress_chart_records
        ]


        steps = [
            int(row["steps"] or 0)
            for row in progress_chart_records
        ]


        # Nutrition chart data

        cursor.execute(
            """
            SELECT
                date,
                SUM(calories) AS calories,
                SUM(protein_g) AS protein
            FROM food_logs
            WHERE user_id = %s
            GROUP BY date
            ORDER BY date ASC
            """,
            (user_id,)
        )

        food_chart_records = cursor.fetchall()


        food_dates = [
            row["date"].strftime("%Y-%m-%d")
            for row in food_chart_records
        ]


        calories = [
            float(row["calories"] or 0)
            for row in food_chart_records
        ]


        protein = [
            float(row["protein"] or 0)
            for row in food_chart_records
        ]


        # Workout frequency chart

        cursor.execute(
            """
            SELECT
                workout_date AS date,
                COUNT(*) AS workout_count
            FROM workouts
            WHERE user_id = %s
            GROUP BY workout_date
            ORDER BY workout_date ASC
            """,
            (user_id,)
        )

        workout_chart_records = cursor.fetchall()


        workout_dates = [
            row["date"].strftime("%Y-%m-%d")
            for row in workout_chart_records
        ]


        workout_counts = [
            int(row["workout_count"])
            for row in workout_chart_records
        ]


    except psycopg2.Error:

        cursor.close()
        connection.close()

        flash(
            "Unable to load user activity.",
            "danger"
        )

        return redirect(
            url_for("admin_dashboard")
        )


    cursor.close()
    connection.close()


    # ==================================================
    # RENDER PAGE
    # ==================================================

    return render_template(
        "admin_user_activity.html",

        user=user,

        goal=goal,

        progress_records=progress_records,

        food_logs=food_logs,

        workouts=workouts,

        progress_dates=progress_dates,

        weights=weights,

        water=water,

        steps=steps,

        food_dates=food_dates,

        calories=calories,

        protein=protein,

        workout_dates=workout_dates,

        workout_counts=workout_counts
    )

# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template("home.html")


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "danger"
            )

            return redirect(url_for("register"))

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            connection.close()

            flash(
                "Email already registered.",
                "warning"
            )

            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (
                name,
                email,
                hashed_password
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            "Registration successful. Please login.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        if not email or not password:

            flash(
                "Email and password are required.",
                "danger"
            )

            return redirect(url_for("login"))

        connection = get_db_connection()

        cursor = connection.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password,
                role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            session["user_role"] = user["role"]

            flash(
                "Login successful.",
                "success"
            )

            return redirect(url_for("dashboard"))

        flash(
            "Invalid email or password.",
            "danger"
        )

        return redirect(url_for("login"))

    return render_template("login.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        # ==================================================
        # FITNESS GOALS
        # ==================================================

        cursor.execute(
            """
            SELECT
                age,
                sex,
                height_cm,
                starting_weight,
                target_weight,
                goal_type,
                daily_calorie_target,
                daily_protein_target,
                daily_fat_target,
                daily_carb_target

            FROM fitness_goals

            WHERE user_id = %s
            """,
            (user_id,)
        )

        goal = cursor.fetchone()

        # ==================================================
        # LATEST DAILY PROGRESS
        # ==================================================

        cursor.execute(
            """
            SELECT
                date,
                weight_kg,
                bmi,
                water_liters,
                sleep_hours,
                steps

            FROM daily_progress

            WHERE user_id = %s

            ORDER BY date DESC

            LIMIT 1
            """,
            (user_id,)
        )

        latest_progress = cursor.fetchone()

        # ==================================================
        # TODAY'S NUTRITION
        # ==================================================

        today = date.today().isoformat()

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(calories), 0)
                    AS total_calories,

                COALESCE(SUM(protein_g), 0)
                    AS total_protein

            FROM food_logs

            WHERE user_id = %s
            AND date = %s
            """,
            (user_id, today)
        )

        nutrition = cursor.fetchone()

        # ==================================================
        # RECENT WORKOUTS
        # ==================================================

        cursor.execute(
            """
            SELECT
                id,
                workout_date,
                workout_name,
                duration_minutes

            FROM workouts

            WHERE user_id = %s

            ORDER BY workout_date DESC, id DESC

            LIMIT 5
            """,
            (user_id,)
        )

        recent_workouts = cursor.fetchall()

    except psycopg2.Error:

        cursor.close()
        connection.close()

        flash(
            "Unable to load dashboard. Please try again.",
            "danger"
        )

        return redirect(url_for("home"))

    cursor.close()
    connection.close()

    # ==================================================
    # DEFAULT VALUES
    # ==================================================

    current_weight = None
    target_weight = None
    weight_remaining = None

    bmi = None

    water = 0
    sleep = 0
    steps = 0

    calorie_target = 0
    protein_target = 0

    calories_consumed = float(
        nutrition["total_calories"] or 0
    )

    protein_consumed = float(
        nutrition["total_protein"] or 0
    )

    # ==================================================
    # GOAL DATA
    # ==================================================

    if goal:

        target_weight = float(
            goal["target_weight"]
        )

        calorie_target = float(
            goal["daily_calorie_target"]
        )

        protein_target = float(
            goal["daily_protein_target"]
        )

    # ==================================================
    # LATEST PROGRESS DATA
    # ==================================================

    if latest_progress:

        current_weight = float(
            latest_progress["weight_kg"]
        )

        if latest_progress["bmi"] is not None:

            bmi = float(
                latest_progress["bmi"]
            )

        water = float(
            latest_progress["water_liters"] or 0
        )

        sleep = float(
            latest_progress["sleep_hours"] or 0
        )

        steps = int(
            latest_progress["steps"] or 0
        )

    elif goal:

        current_weight = float(
            goal["starting_weight"]
        )

        bmi = calculate_bmi(
            current_weight,
            float(goal["height_cm"])
        )

    # ==================================================
    # WEIGHT REMAINING
    # ==================================================

    if (
        current_weight is not None
        and target_weight is not None
    ):

        weight_remaining = abs(
            current_weight - target_weight
        )

    # ==================================================
    # CALORIE PROGRESS
    # ==================================================

    calorie_percent = 0

    if calorie_target > 0:

        calorie_percent = (
            float(calories_consumed)
            / float(calorie_target)
        ) * 100

    calorie_percent = min(
        max(calorie_percent, 0),
        100
    )

    # ==================================================
    # PROTEIN PROGRESS
    # ==================================================

    protein_percent = 0

    if protein_target > 0:

        protein_percent = (
            float(protein_consumed)
            / float(protein_target)
        ) * 100

    protein_percent = min(
        max(protein_percent, 0),
        100
    )

    # ==================================================
    # GOAL PROGRESS
    # ==================================================

    goal_progress = 0

    if (
        goal
        and current_weight is not None
    ):

        starting_weight = float(
            goal["starting_weight"]
        )

        target_weight_value = float(
            goal["target_weight"]
        )

        total_difference = abs(
            starting_weight
            - target_weight_value
        )

        completed_difference = abs(
            starting_weight
            - current_weight
        )

        if total_difference > 0:

            goal_progress = (
                completed_difference
                / total_difference
            ) * 100

            goal_progress = min(
                max(goal_progress, 0),
                100
            )

    # ==================================================
    # RENDER DASHBOARD
    # ==================================================

    return render_template(
        "dashboard.html",

        user_name=session["user_name"],

        goal=goal,

        latest_progress=latest_progress,

        recent_workouts=recent_workouts,

        current_weight=current_weight,

        target_weight=target_weight,

        weight_remaining=weight_remaining,

        bmi=bmi,

        water=water,

        sleep=sleep,

        steps=steps,

        calorie_target=calorie_target,

        calories_consumed=calories_consumed,

        calorie_percent=round(
            calorie_percent,
            1
        ),

        protein_target=protein_target,

        protein_consumed=protein_consumed,

        protein_percent=round(
            protein_percent,
            1
        ),

        goal_progress=round(
            goal_progress,
            1
        )
    )

@app.route("/charts")
def charts():

    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        # ----------------------------------------
        # WEIGHT + WATER + STEPS DATA
        # ----------------------------------------

        cursor.execute(
            """
            SELECT
                date,
                weight_kg,
                water_liters,
                steps
            FROM daily_progress
            WHERE user_id = %s
            ORDER BY date ASC
            """,
            (user_id,)
        )

        progress_data = cursor.fetchall()


        # ----------------------------------------
        # FOOD DATA
        # ----------------------------------------

        cursor.execute(
            """
            SELECT
                date,
                SUM(calories) AS calories,
                SUM(protein_g) AS protein
            FROM food_logs
            WHERE user_id = %s
            GROUP BY date
            ORDER BY date ASC
            """,
            (user_id,)
        )

        food_data = cursor.fetchall()


        # ----------------------------------------
        # WORKOUT DATA
        # ----------------------------------------

        cursor.execute(
            """
            SELECT
                workout_date AS date,
                COUNT(*) AS workout_count
            FROM workouts
            WHERE user_id = %s
            GROUP BY workout_date
            ORDER BY workout_date ASC
            """,
            (user_id,)
        )

        workout_data = cursor.fetchall()


    except psycopg2.Error:

        flash(
            "Unable to load chart data. Please try again.",
            "danger"
        )

        cursor.close()
        connection.close()

        return redirect(url_for("dashboard"))


    cursor.close()
    connection.close()


    # ----------------------------------------
    # PREPARE DATA FOR JAVASCRIPT
    # ----------------------------------------

    progress_dates = [
        row["date"].strftime("%Y-%m-%d")
        for row in progress_data
    ]

    weights = [
        float(row["weight_kg"])
        for row in progress_data
    ]

    water = [
        float(row["water_liters"] or 0)
        for row in progress_data
    ]

    steps = [
        int(row["steps"] or 0)
        for row in progress_data
    ]


    food_dates = [
        row["date"].strftime("%Y-%m-%d")
        for row in food_data
    ]

    calories = [
        float(row["calories"] or 0)
        for row in food_data
    ]

    protein = [
        float(row["protein"] or 0)
        for row in food_data
    ]


    workout_dates = [
        row["date"].strftime("%Y-%m-%d")
        for row in workout_data
    ]

    workout_counts = [
        int(row["workout_count"])
        for row in workout_data
    ]


    return render_template(
        "charts.html",

        progress_dates=progress_dates,
        weights=weights,
        water=water,
        steps=steps,

        food_dates=food_dates,
        calories=calories,
        protein=protein,

        workout_dates=workout_dates,
        workout_counts=workout_counts
    )


# =========================
# FITNESS GOALS
# =========================

@app.route("/goals", methods=["GET", "POST"])
def goals():

    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    # =========================
    # SAVE / UPDATE GOALS
    # =========================

    if request.method == "POST":

        try:
            age = int(request.form["age"])
            sex = request.form["sex"].strip().lower()

            height_cm = float(request.form["height_cm"])
            starting_weight = float(
                request.form["starting_weight"]
            )
            target_weight = float(
                request.form["target_weight"]
            )

            activity_level = request.form[
                "activity_level"
            ].strip().lower()

            goal_type = request.form[
                "goal_type"
            ].strip()

        except (ValueError, TypeError, KeyError):

            cursor.close()
            connection.close()

            flash(
                "Please enter valid values.",
                "danger"
            )

            return redirect(url_for("goals"))

        # =========================
        # VALIDATION
        # =========================

        allowed_sex = [
            "male",
            "female"
        ]

        allowed_activity_levels = [
            "sedentary",
            "lightly_active",
            "moderately_active",
            "very_active",
            "extra_active"
        ]

        allowed_goals = [
            "Lose Weight",
            "Maintain Weight",
            "Gain Weight"
        ]

        if age < 13 or age > 100:

            cursor.close()
            connection.close()

            flash(
                "Age must be between 13 and 100.",
                "danger"
            )

            return redirect(url_for("goals"))

        if sex not in allowed_sex:

            cursor.close()
            connection.close()

            flash(
                "Please select a valid sex.",
                "danger"
            )

            return redirect(url_for("goals"))

        if activity_level not in allowed_activity_levels:

            cursor.close()
            connection.close()

            flash(
                "Please select a valid activity level.",
                "danger"
            )

            return redirect(url_for("goals"))

        if goal_type not in allowed_goals:

            cursor.close()
            connection.close()

            flash(
                "Please select a valid fitness goal.",
                "danger"
            )

            return redirect(url_for("goals"))

        if (
            height_cm <= 0
            or starting_weight <= 0
            or target_weight <= 0
        ):

            cursor.close()
            connection.close()

            flash(
                "Height and weights must be greater than zero.",
                "danger"
            )

            return redirect(url_for("goals"))

        # =========================
        # CALCULATE FITNESS TARGETS
        # =========================

        targets = calculate_fitness_targets(
            age=age,
            sex=sex,
            weight_kg=starting_weight,
            height_cm=height_cm,
            activity_level=activity_level,
            goal_type=goal_type
        )

        daily_calorie_target = targets["calories"]

        daily_protein_target = targets["protein"]

        daily_fat_target = targets["fat"]

        daily_carb_target = targets["carbs"]

        # =========================
        # CHECK EXISTING GOAL
        # =========================

        cursor.execute(
            """
            SELECT id
            FROM fitness_goals
            WHERE user_id = %s
            """,
            (user_id,)
        )

        existing_goal = cursor.fetchone()

        # =========================
        # UPDATE EXISTING GOAL
        # =========================

        if existing_goal:

            cursor.execute(
                """
                UPDATE fitness_goals
                SET
                    age = %s,
                    sex = %s,
                    activity_level = %s,
                    height_cm = %s,
                    starting_weight = %s,
                    target_weight = %s,
                    daily_calorie_target = %s,
                    daily_protein_target = %s,
                    daily_fat_target = %s,
                    daily_carb_target = %s,
                    goal_type = %s

                WHERE user_id = %s
                """,
                (
                    age,
                    sex,
                    activity_level,
                    height_cm,
                    starting_weight,
                    target_weight,
                    daily_calorie_target,
                    daily_protein_target,
                    daily_fat_target,
                    daily_carb_target,
                    goal_type,
                    user_id
                )
            )

            message = (
                "Fitness goals updated successfully."
            )

        # =========================
        # INSERT NEW GOAL
        # =========================

        else:

            cursor.execute(
                """
                INSERT INTO fitness_goals
                (
                    user_id,
                    age,
                    sex,
                    activity_level,
                    height_cm,
                    starting_weight,
                    target_weight,
                    daily_calorie_target,
                    daily_protein_target,
                    daily_fat_target,
                    daily_carb_target,
                    goal_type
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    user_id,
                    age,
                    sex,
                    activity_level,
                    height_cm,
                    starting_weight,
                    target_weight,
                    daily_calorie_target,
                    daily_protein_target,
                    daily_fat_target,
                    daily_carb_target,
                    goal_type
                )
            )

            message = (
                "Fitness goals saved successfully."
            )

        connection.commit()

        cursor.close()
        connection.close()

        flash(
            message,
            "success"
        )

        return redirect(
            url_for("goals")
        )

    # =========================
    # GET SAVED GOAL
    # =========================

    cursor.execute(
        """
        SELECT
            age,
            sex,
            activity_level,
            height_cm,
            starting_weight,
            target_weight,
            daily_calorie_target,
            daily_protein_target,
            daily_fat_target,
            daily_carb_target,
            goal_type

        FROM fitness_goals

        WHERE user_id = %s
        """,
        (user_id,)
    )

    goal = cursor.fetchone()

    cursor.close()
    connection.close()

    # =========================
    # BMI
    # =========================

    bmi = None
    bmi_category = None

    if goal:

        bmi = calculate_bmi(
            float(goal["starting_weight"]),
            float(goal["height_cm"])
        )

        bmi_category = get_bmi_category(
            bmi
        )

    # =========================
    # RENDER PAGE
    # =========================

    return render_template(
        "goals.html",
        goal=goal,
        bmi=bmi,
        bmi_category=bmi_category
    )


# ==================================================
# DAILY PROGRESS - VIEW
# ==================================================

@app.route("/progress")
def progress():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT
            id,
            date,
            weight_kg,
            bmi,
            water_liters,
            sleep_hours,
            steps,
            waist_cm,
            chest_cm

        FROM daily_progress

        WHERE user_id = %s

        ORDER BY date DESC
        """,
        (user_id,)
    )

    progress_records = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "progress.html",
        progress_records=progress_records
    )


# ==================================================
# DAILY PROGRESS - ADD
# ==================================================

@app.route("/progress/add", methods=["GET", "POST"])
def add_progress():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":

        date = request.form["date"]

        try:

            weight_kg = float(
                request.form["weight_kg"]
            )

            water_liters = float(
                request.form.get("water_liters") or 0
            )

            sleep_hours = float(
                request.form.get("sleep_hours") or 0
            )

            steps = int(
                request.form.get("steps") or 0
            )

            waist_cm = request.form.get("waist_cm")
            chest_cm = request.form.get("chest_cm")

            waist_cm = (
                float(waist_cm)
                if waist_cm
                else None
            )

            chest_cm = (
                float(chest_cm)
                if chest_cm
                else None
            )

        except (ValueError, TypeError):

            flash(
                "Please enter valid values.",
                "danger"
            )

            return redirect(url_for("add_progress"))

        if weight_kg <= 0:

            flash(
                "Weight must be greater than zero.",
                "danger"
            )

            return redirect(url_for("add_progress"))

        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        # Get user's height

        cursor.execute(
            """
            SELECT height_cm
            FROM fitness_goals
            WHERE user_id = %s
            """,
            (user_id,)
        )

        goal = cursor.fetchone()

        if not goal:

            cursor.close()
            connection.close()

            flash(
                "Please set your fitness goals first.",
                "warning"
            )

            return redirect(url_for("goals"))

        height_cm = float(
            goal["height_cm"]
        )

        # Calculate BMI

        bmi = calculate_bmi(
            weight_kg,
            height_cm
        )

        # Insert progress

        try:

            cursor.execute(
                """
                INSERT INTO daily_progress
                (
                    user_id,
                    date,
                    weight_kg,
                    bmi,
                    water_liters,
                    sleep_hours,
                    steps,
                    waist_cm,
                    chest_cm
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    user_id,
                    date,
                    weight_kg,
                    bmi,
                    water_liters,
                    sleep_hours,
                    steps,
                    waist_cm,
                    chest_cm
                )
            )

            connection.commit()

        except psycopg2.IntegrityError:

            connection.rollback()

            cursor.close()
            connection.close()

            flash(
                "A progress record already exists for this date.",
                "warning"
            )

            return redirect(url_for("add_progress"))

        cursor.close()
        connection.close()

        flash(
            "Daily progress added successfully.",
            "success"
        )

        return redirect(url_for("progress"))

    return render_template(
        "progress_form.html",
        record=None,
        page_title="Add Daily Progress"
    )


# ==================================================
# DAILY PROGRESS - EDIT
# ==================================================

@app.route(
    "/progress/edit/<int:progress_id>",
    methods=["GET", "POST"]
)
def edit_progress(progress_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    # IMPORTANT:
    # progress_id AND user_id are checked together.
    # This prevents one user from editing another user's record.

    cursor.execute(
        """
        SELECT *
        FROM daily_progress

        WHERE id = %s
        AND user_id = %s
        """,
        (
            progress_id,
            user_id
        )
    )

    record = cursor.fetchone()

    if not record:

        cursor.close()
        connection.close()

        flash(
            "Progress record not found.",
            "danger"
        )

        return redirect(url_for("progress"))

    if request.method == "POST":

        try:

            date = request.form["date"]

            weight_kg = float(
                request.form["weight_kg"]
            )

            water_liters = float(
                request.form.get("water_liters") or 0
            )

            sleep_hours = float(
                request.form.get("sleep_hours") or 0
            )

            steps = int(
                request.form.get("steps") or 0
            )

            waist_cm = request.form.get("waist_cm")
            chest_cm = request.form.get("chest_cm")

            waist_cm = (
                float(waist_cm)
                if waist_cm
                else None
            )

            chest_cm = (
                float(chest_cm)
                if chest_cm
                else None
            )

        except (ValueError, TypeError):

            cursor.close()
            connection.close()

            flash(
                "Please enter valid values.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_progress",
                    progress_id=progress_id
                )
            )

        if weight_kg <= 0:

            cursor.close()
            connection.close()

            flash(
                "Weight must be greater than zero.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_progress",
                    progress_id=progress_id
                )
            )

        # Get height

        cursor.execute(
            """
            SELECT height_cm
            FROM fitness_goals
            WHERE user_id = %s
            """,
            (user_id,)
        )

        goal = cursor.fetchone()

        if not goal:

            cursor.close()
            connection.close()

            flash(
                "Please set your fitness goals first.",
                "warning"
            )

            return redirect(url_for("goals"))

        height_cm = float(
            goal["height_cm"]
        )

        bmi = calculate_bmi(
            weight_kg,
            height_cm
        )

        try:

            cursor.execute(
                """
                UPDATE daily_progress

                SET
                    date = %s,
                    weight_kg = %s,
                    bmi = %s,
                    water_liters = %s,
                    sleep_hours = %s,
                    steps = %s,
                    waist_cm = %s,
                    chest_cm = %s

                WHERE id = %s
                AND user_id = %s
                """,
                (
                    date,
                    weight_kg,
                    bmi,
                    water_liters,
                    sleep_hours,
                    steps,
                    waist_cm,
                    chest_cm,
                    progress_id,
                    user_id
                )
            )

            connection.commit()

        except psycopg2.IntegrityError:

            connection.rollback()

            cursor.close()
            connection.close()

            flash(
                "Another progress record already exists for this date.",
                "warning"
            )

            return redirect(
                url_for(
                    "edit_progress",
                    progress_id=progress_id
                )
            )

        cursor.close()
        connection.close()

        flash(
            "Daily progress updated successfully.",
            "success"
        )

        return redirect(url_for("progress"))

    cursor.close()
    connection.close()

    return render_template(
        "progress_form.html",
        record=record,
        page_title="Edit Daily Progress"
    )

# ==================================================
# DAILY PROGRESS - DELETE
# ==================================================

@app.route(
    "/progress/delete/<int:progress_id>",
    methods=["POST"]
)
def delete_progress(progress_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    # Delete only the progress record
    # belonging to the logged-in user.

    cursor.execute(
        """
        DELETE FROM daily_progress

        WHERE id = %s
        AND user_id = %s
        """,
        (
            progress_id,
            user_id
        )
    )

    connection.commit()

    deleted_rows = cursor.rowcount

    cursor.close()
    connection.close()

    if deleted_rows == 0:

        flash(
            "Progress record not found.",
            "danger"
        )

    else:

        flash(
            "Daily progress deleted successfully.",
            "success"
        )

    return redirect(url_for("progress"))


## ==================================================
# FOOD / NUTRITION - VIEW
# ==================================================

@app.route("/food")
def food():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    selected_date = request.args.get(
        "date",
        date.today().isoformat()
    )

    # Validate selected date

    try:

        datetime.strptime(
            selected_date,
            "%Y-%m-%d"
        )

    except ValueError:

        selected_date = date.today().isoformat()

        flash(
            "Invalid date selected. Showing today's nutrition.",
            "warning"
        )

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    # Get food entries for selected date

    cursor.execute(
        """
        SELECT
            id,
            date,
            food_name,
            quantity_g,
            calories,
            carbs_g,
            protein_g,
            fat_g,
            fiber_g

        FROM food_logs

        WHERE user_id = %s
        AND date = %s

        ORDER BY id DESC
        """,
        (
            user_id,
            selected_date
        )
    )

    food_logs = cursor.fetchall()

    # Get daily totals

    cursor.execute(
        """
        SELECT

            COALESCE(SUM(calories), 0)
                AS total_calories,

            COALESCE(SUM(carbs_g), 0)
                AS total_carbs,

            COALESCE(SUM(protein_g), 0)
                AS total_protein,

            COALESCE(SUM(fat_g), 0)
                AS total_fat,

            COALESCE(SUM(fiber_g), 0)
                AS total_fiber

        FROM food_logs

        WHERE user_id = %s
        AND date = %s
        """,
        (
            user_id,
            selected_date
        )
    )

    totals = cursor.fetchone()

    # Get user's nutrition targets

    cursor.execute(
        """
        SELECT
            daily_calorie_target,
            daily_protein_target,
            daily_carb_target,
            daily_fat_target

        FROM fitness_goals

        WHERE user_id = %s
        """,
        (user_id,)
    )

    goal = cursor.fetchone()

    cursor.close()
    connection.close()

    total_calories = totals["total_calories"]
    total_carbs = totals["total_carbs"]
    total_protein = totals["total_protein"]
    total_fat = totals["total_fat"]
    total_fiber = totals["total_fiber"]

    return render_template(
        "food.html",
        food_logs=food_logs,
        selected_date=selected_date,
        total_calories=total_calories,
        total_carbs=total_carbs,
        total_protein=total_protein,
        total_fat=total_fat,
        total_fiber=total_fiber,
        goal=goal,
        food_data=FOOD_DATA
    )


# ==================================================
# FOOD / NUTRITION - ADD
# ==================================================

@app.route(
    "/food/add",
    methods=["GET", "POST"]
)
def add_food():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":

        food_date = request.form.get(
            "date",
            ""
        ).strip()

        food_name = request.form.get(
            "food_name",
            ""
        ).strip()

        try:

            quantity_g = float(
                request.form.get("quantity_g", "")
            )

        except (ValueError, TypeError):

            flash(
                "Please enter a valid food quantity.",
                "danger"
            )

            return redirect(url_for("add_food"))

        # Validate date

        try:

            datetime.strptime(
                food_date,
                "%Y-%m-%d"
            )

        except ValueError:

            flash(
                "Please select a valid date.",
                "danger"
            )

            return redirect(url_for("add_food"))

        # Validate food name

        if food_name not in FOOD_DATA:

            flash(
                "Please select a valid food item.",
                "danger"
            )

            return redirect(url_for("add_food"))

        # Validate quantity

        if quantity_g <= 0:

            flash(
                "Food quantity must be greater than zero.",
                "danger"
            )

            return redirect(url_for("add_food"))

        # Get nutrition data per 100g

        nutrition = FOOD_DATA[food_name]

        multiplier = quantity_g / 100

        calories = round(
            nutrition["calories"] * multiplier,
            2
        )

        carbs_g = round(
            nutrition["carbs"] * multiplier,
            2
        )

        protein_g = round(
            nutrition["protein"] * multiplier,
            2
        )

        fat_g = round(
            nutrition["fat"] * multiplier,
            2
        )

        fiber_g = round(
            nutrition["fiber"] * multiplier,
            2
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO food_logs
                (
                    user_id,
                    date,
                    food_name,
                    quantity_g,
                    calories,
                    carbs_g,
                    protein_g,
                    fat_g,
                    fiber_g
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    user_id,
                    food_date,
                    food_name,
                    quantity_g,
                    calories,
                    carbs_g,
                    protein_g,
                    fat_g,
                    fiber_g
                )
            )

            connection.commit()

        except psycopg2.Error:

            connection.rollback()

            cursor.close()
            connection.close()

            flash(
                "Unable to save food entry. Please try again.",
                "danger"
            )

            return redirect(url_for("add_food"))

        cursor.close()
        connection.close()

        flash(
            "Food entry added successfully.",
            "success"
        )

        return redirect(
            url_for(
                "food",
                date=food_date
            )
        )

    return render_template(
        "food_form.html",
        food=None,
        page_title="Add Food",
        food_data=FOOD_DATA
    )


# ==================================================
# FOOD / NUTRITION - EDIT
# ==================================================

@app.route(
    "/food/edit/<int:food_id>",
    methods=["GET", "POST"]
)
def edit_food(food_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    # IMPORTANT:
    # food_id AND user_id are checked together.
    # This prevents one user from editing another
    # user's food entry.

    cursor.execute(
        """
        SELECT
            id,
            date,
            food_name,
            quantity_g,
            calories,
            carbs_g,
            protein_g,
            fat_g,
            fiber_g

        FROM food_logs

        WHERE id = %s
        AND user_id = %s
        """,
        (
            food_id,
            user_id
        )
    )

    food = cursor.fetchone()

    if not food:

        cursor.close()
        connection.close()

        flash(
            "Food entry not found.",
            "danger"
        )

        return redirect(url_for("food"))

    if request.method == "POST":

        food_date = request.form.get(
            "date",
            ""
        ).strip()

        food_name = request.form.get(
            "food_name",
            ""
        ).strip()

        try:

            quantity_g = float(
                request.form.get("quantity_g", "")
            )

        except (ValueError, TypeError):

            cursor.close()
            connection.close()

            flash(
                "Please enter a valid food quantity.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_food",
                    food_id=food_id
                )
            )

        # Validate date

        try:

            datetime.strptime(
                food_date,
                "%Y-%m-%d"
            )

        except ValueError:

            cursor.close()
            connection.close()

            flash(
                "Please select a valid date.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_food",
                    food_id=food_id
                )
            )

        # Validate food

        if food_name not in FOOD_DATA:

            cursor.close()
            connection.close()

            flash(
                "Please select a valid food item.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_food",
                    food_id=food_id
                )
            )

        # Validate quantity

        if quantity_g <= 0:

            cursor.close()
            connection.close()

            flash(
                "Food quantity must be greater than zero.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_food",
                    food_id=food_id
                )
            )

        # Calculate nutrition

        nutrition = FOOD_DATA[food_name]

        multiplier = quantity_g / 100

        calories = round(
            nutrition["calories"] * multiplier,
            2
        )

        carbs_g = round(
            nutrition["carbs"] * multiplier,
            2
        )

        protein_g = round(
            nutrition["protein"] * multiplier,
            2
        )

        fat_g = round(
            nutrition["fat"] * multiplier,
            2
        )

        fiber_g = round(
            nutrition["fiber"] * multiplier,
            2
        )

        try:

            cursor.execute(
                """
                UPDATE food_logs

                SET
                    date = %s,
                    food_name = %s,
                    quantity_g = %s,
                    calories = %s,
                    carbs_g = %s,
                    protein_g = %s,
                    fat_g = %s,
                    fiber_g = %s

                WHERE id = %s
                AND user_id = %s
                """,
                (
                    food_date,
                    food_name,
                    quantity_g,
                    calories,
                    carbs_g,
                    protein_g,
                    fat_g,
                    fiber_g,
                    food_id,
                    user_id
                )
            )

            connection.commit()

        except psycopg2.Error:

            connection.rollback()

            cursor.close()
            connection.close()

            flash(
                "Unable to update food entry. Please try again.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_food",
                    food_id=food_id
                )
            )

        cursor.close()
        connection.close()

        flash(
            "Food entry updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "food",
                date=food_date
            )
        )

    cursor.close()
    connection.close()

    return render_template(
        "food_form.html",
        food=food,
        page_title="Edit Food",
        food_data=FOOD_DATA
    )


# ==================================================
# FOOD / NUTRITION - DELETE
# ==================================================

@app.route(
    "/food/delete/<int:food_id>",
    methods=["POST"]
)
def delete_food(food_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    # Delete only if this food entry belongs
    # to the currently logged-in user.

    cursor.execute(
        """
        DELETE FROM food_logs

        WHERE id = %s
        AND user_id = %s
        """,
        (
            food_id,
            user_id
        )
    )

    connection.commit()

    deleted_rows = cursor.rowcount

    cursor.close()
    connection.close()

    if deleted_rows == 0:

        flash(
            "Food entry not found.",
            "danger"
        )

    else:

        flash(
            "Food entry deleted successfully.",
            "success"
        )

    return redirect(url_for("food"))


# ==================================================
# WORKOUTS - VIEW
# ==================================================

@app.route("/workouts")
def workouts():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        cursor.execute(
            """
            SELECT
                id,
                workout_date,
                workout_name,
                duration_minutes

            FROM workouts

            WHERE user_id = %s

            ORDER BY workout_date DESC, id DESC
            """,
            (user_id,)
        )

        workout_list = cursor.fetchall()

    except psycopg2.Error:

        flash(
            "Unable to load workouts. Please try again.",
            "danger"
        )

        workout_list = []

    cursor.close()
    connection.close()

    return render_template(
        "workouts.html",
        workouts=workout_list
    )


# ==================================================
# WORKOUTS - ADD
# ==================================================

@app.route(
    "/workouts/add",
    methods=["GET", "POST"]
)
def add_workout():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":

        workout_date = request.form.get(
            "workout_date",
            ""
        ).strip()

        workout_name = request.form.get(
            "workout_name",
            ""
        ).strip()

        duration_text = request.form.get(
            "duration_minutes",
            ""
        ).strip()

        # Validate date

        try:

            datetime.strptime(
                workout_date,
                "%Y-%m-%d"
            )

        except ValueError:

            flash(
                "Please select a valid workout date.",
                "danger"
            )

            return redirect(
                url_for("add_workout")
            )

        # Validate workout name

        if not workout_name:

            flash(
                "Workout name is required.",
                "danger"
            )

            return redirect(
                url_for("add_workout")
            )

        if len(workout_name) > 100:

            flash(
                "Workout name is too long.",
                "danger"
            )

            return redirect(
                url_for("add_workout")
            )

        # Validate duration

        try:

            duration_minutes = int(
                duration_text
            )

        except (ValueError, TypeError):

            flash(
                "Please enter a valid workout duration.",
                "danger"
            )

            return redirect(
                url_for("add_workout")
            )

        if duration_minutes <= 0:

            flash(
                "Workout duration must be greater than zero.",
                "danger"
            )

            return redirect(
                url_for("add_workout")
            )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO workouts
                (
                    user_id,
                    workout_date,
                    workout_name,
                    duration_minutes
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    user_id,
                    workout_date,
                    workout_name,
                    duration_minutes
                )
            )

            cursor.execute("SELECT LASTVAL() AS id")
            workout_id = cursor.fetchone()["id"]

            connection.commit()

        except psycopg2.Error:

            connection.rollback()

            cursor.close()
            connection.close()

            flash(
                "Unable to save workout. Please try again.",
                "danger"
            )

            return redirect(
                url_for("add_workout")
            )

        cursor.close()
        connection.close()

        flash(
            "Workout added successfully.",
            "success"
        )

        # After creating the workout,
        # go to the workout detail page.
        return redirect(
            url_for(
                "workout_detail",
                workout_id=workout_id
            )
        )

    return render_template(
        "workout_form.html"
    )


# ==================================================
# WORKOUTS - DETAIL
# ==================================================

@app.route(
    "/workouts/<int:workout_id>"
)
def workout_detail(workout_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        # Get workout.
        #
        # user_id is checked together with workout_id
        # so another user cannot open this workout.

        cursor.execute(
            """
            SELECT
                id,
                workout_date,
                workout_name,
                duration_minutes

            FROM workouts

            WHERE id = %s
            AND user_id = %s
            """,
            (
                workout_id,
                user_id
            )
        )

        workout = cursor.fetchone()

        if not workout:

            cursor.close()
            connection.close()

            flash(
                "Workout not found.",
                "danger"
            )

            return redirect(
                url_for("workouts")
            )

        # Get exercises belonging to this workout

        cursor.execute(
            """
            SELECT
                id,
                exercise_name

            FROM exercises

            WHERE workout_id = %s

            ORDER BY id ASC
            """,
            (workout_id,)
        )

        exercises = cursor.fetchall()

        # Get sets for all exercises

        for exercise in exercises:

            cursor.execute(
                """
                SELECT
                    id,
                    set_number,
                    reps,
                    weight_kg

                FROM exercise_sets

                WHERE exercise_id = %s

                ORDER BY set_number ASC, id ASC
                """,
                (exercise["id"],)
            )

            exercise["sets"] = cursor.fetchall()

    except psycopg2.Error:

        cursor.close()
        connection.close()

        flash(
            "Unable to load workout details.",
            "danger"
        )

        return redirect(
            url_for("workouts")
        )

    cursor.close()
    connection.close()

    return render_template(
        "workout_detail.html",
        workout=workout,
        exercises=exercises
    )


# ==================================================
# WORKOUTS - DELETE
# ==================================================

@app.route(
    "/workouts/delete/<int:workout_id>",
    methods=["POST"]
)
def delete_workout(workout_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        # Because the database has ON DELETE CASCADE,
        # deleting the workout also deletes:
        #
        # exercises
        # exercise_sets

        cursor.execute(
            """
            DELETE FROM workouts

            WHERE id = %s
            AND user_id = %s
            """,
            (
                workout_id,
                user_id
            )
        )

        connection.commit()

        deleted_rows = cursor.rowcount

    except psycopg2.Error:

        connection.rollback()

        cursor.close()
        connection.close()

        flash(
            "Unable to delete workout. Please try again.",
            "danger"
        )

        return redirect(
            url_for("workouts")
        )

    cursor.close()
    connection.close()

    if deleted_rows == 0:

        flash(
            "Workout not found.",
            "danger"
        )

    else:

        flash(
            "Workout deleted successfully.",
            "success"
        )

    return redirect(
        url_for("workouts")
    )


# ==================================================
# EXERCISES - ADD
# ==================================================

@app.route(
    "/workouts/<int:workout_id>/exercises/add",
    methods=["POST"]
)
def add_exercise(workout_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    exercise_name = request.form.get(
        "exercise_name",
        ""
    ).strip()

    if not exercise_name:

        flash(
            "Exercise name is required.",
            "danger"
        )

        return redirect(
            url_for(
                "workout_detail",
                workout_id=workout_id
            )
        )

    if len(exercise_name) > 100:

        flash(
            "Exercise name is too long.",
            "danger"
        )

        return redirect(
            url_for(
                "workout_detail",
                workout_id=workout_id
            )
        )

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        # Make sure this workout belongs to
        # the currently logged-in user.

        cursor.execute(
            """
            SELECT id

            FROM workouts

            WHERE id = %s
            AND user_id = %s
            """,
            (
                workout_id,
                user_id
            )
        )

        workout = cursor.fetchone()

        if not workout:

            cursor.close()
            connection.close()

            flash(
                "Workout not found.",
                "danger"
            )

            return redirect(
                url_for("workouts")
            )

        cursor.execute(
            """
            INSERT INTO exercises
            (
                workout_id,
                exercise_name
            )

            VALUES
            (
                %s,
                %s
            )
            """,
            (
                workout_id,
                exercise_name
            )
        )

        connection.commit()

    except psycopg2.Error:

        connection.rollback()

        cursor.close()
        connection.close()

        flash(
            "Unable to add exercise. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "workout_detail",
                workout_id=workout_id
            )
        )

    cursor.close()
    connection.close()

    flash(
        "Exercise added successfully.",
        "success"
    )

    return redirect(
        url_for(
            "workout_detail",
            workout_id=workout_id
        )
    )


# ==================================================
# EXERCISES - DELETE
# ==================================================

@app.route(
    "/exercises/delete/<int:exercise_id>",
    methods=["POST"]
)
def delete_exercise(exercise_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        # Find exercise and verify ownership
        # through the workout.

        cursor.execute(
            """
            SELECT
                exercises.id,
                exercises.workout_id

            FROM exercises

            INNER JOIN workouts
                ON exercises.workout_id = workouts.id

            WHERE exercises.id = %s
            AND workouts.user_id = %s
            """,
            (
                exercise_id,
                user_id
            )
        )

        exercise = cursor.fetchone()

        if not exercise:

            cursor.close()
            connection.close()

            flash(
                "Exercise not found.",
                "danger"
            )

            return redirect(
                url_for("workouts")
            )

        workout_id = exercise["workout_id"]

        cursor.execute(
            """
            DELETE FROM exercises

            WHERE id = %s
            """,
            (exercise_id,)
        )

        connection.commit()

    except psycopg2.Error:

        connection.rollback()

        cursor.close()
        connection.close()

        flash(
            "Unable to delete exercise. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "workout_detail",
                workout_id=workout_id
            )
        )

    cursor.close()
    connection.close()

    flash(
        "Exercise deleted successfully.",
        "success"
    )

    return redirect(
        url_for(
            "workout_detail",
            workout_id=workout_id
        )
    )


# ==================================================
# EXERCISE SETS - ADD
# ==================================================

@app.route(
    "/exercises/<int:exercise_id>/sets/add",
    methods=["POST"]
)
def add_exercise_set(exercise_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    try:

        reps = int(
            request.form.get(
                "reps",
                ""
            )
        )

        weight_kg = float(
            request.form.get(
                "weight_kg",
                ""
            )
        )

    except (ValueError, TypeError):

        flash(
            "Please enter valid reps and weight.",
            "danger"
        )

        return redirect(
            url_for(
                "workouts"
            )
        )

    if reps <= 0:

        flash(
            "Reps must be greater than zero.",
            "danger"
        )

        return redirect(
            url_for(
                "workouts"
            )
        )

    if weight_kg < 0:

        flash(
            "Weight cannot be negative.",
            "danger"
        )

        return redirect(
            url_for(
                "workouts"
            )
        )

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        # Verify that this exercise belongs
        # to the logged-in user.

        cursor.execute(
            """
            SELECT
                exercises.id,
                exercises.workout_id

            FROM exercises

            INNER JOIN workouts
                ON exercises.workout_id = workouts.id

            WHERE exercises.id = %s
            AND workouts.user_id = %s
            """,
            (
                exercise_id,
                user_id
            )
        )

        exercise = cursor.fetchone()

        if not exercise:

            cursor.close()
            connection.close()

            flash(
                "Exercise not found.",
                "danger"
            )

            return redirect(
                url_for("workouts")
            )

        workout_id = exercise["workout_id"]

        # Find the next set number.

        cursor.execute(
            """
            SELECT
                COALESCE(
                    MAX(set_number),
                    0
                ) + 1 AS next_set

            FROM exercise_sets

            WHERE exercise_id = %s
            """,
            (exercise_id,)
        )

        result = cursor.fetchone()

        next_set = result["next_set"]

        cursor.execute(
            """
            INSERT INTO exercise_sets
            (
                exercise_id,
                set_number,
                reps,
                weight_kg
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                exercise_id,
                next_set,
                reps,
                weight_kg
            )
        )

        connection.commit()

    except psycopg2.Error:

        connection.rollback()

        cursor.close()
        connection.close()

        flash(
            "Unable to add set. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "workout_detail",
                workout_id=workout_id
            )
        )

    cursor.close()
    connection.close()

    flash(
        "Set added successfully.",
        "success"
    )

    return redirect(
        url_for(
            "workout_detail",
            workout_id=workout_id
        )
    )


# ==================================================
# EXERCISE SETS - EDIT
# ==================================================

@app.route(
    "/sets/edit/<int:set_id>",
    methods=["POST"]
)
def edit_exercise_set(set_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    try:

        reps = int(
            request.form.get(
                "reps",
                ""
            )
        )

        weight_kg = float(
            request.form.get(
                "weight_kg",
                ""
            )
        )

    except (ValueError, TypeError):

        flash(
            "Please enter valid reps and weight.",
            "danger"
        )

        return redirect(
            url_for("workouts")
        )

    if reps <= 0 or weight_kg < 0:

        flash(
            "Please enter valid set values.",
            "danger"
        )

        return redirect(
            url_for("workouts")
        )

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        # Get the set and verify ownership.

        cursor.execute(
            """
            SELECT
                exercise_sets.id,
                exercises.workout_id

            FROM exercise_sets

            INNER JOIN exercises
                ON exercise_sets.exercise_id = exercises.id

            INNER JOIN workouts
                ON exercises.workout_id = workouts.id

            WHERE exercise_sets.id = %s
            AND workouts.user_id = %s
            """,
            (
                set_id,
                user_id
            )
        )

        exercise_set = cursor.fetchone()

        if not exercise_set:

            cursor.close()
            connection.close()

            flash(
                "Set not found.",
                "danger"
            )

            return redirect(
                url_for("workouts")
            )

        workout_id = exercise_set["workout_id"]

        cursor.execute(
            """
            UPDATE exercise_sets

            SET
                reps = %s,
                weight_kg = %s

            WHERE id = %s
            """,
            (
                reps,
                weight_kg,
                set_id
            )
        )

        connection.commit()

    except psycopg2.Error:

        connection.rollback()

        cursor.close()
        connection.close()

        flash(
            "Unable to update set. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "workout_detail",
                workout_id=workout_id
            )
        )

    cursor.close()
    connection.close()

    flash(
        "Set updated successfully.",
        "success"
    )

    return redirect(
        url_for(
            "workout_detail",
            workout_id=workout_id
        )
    )


# ==================================================
# EXERCISE SETS - DELETE
# ==================================================

@app.route(
    "/sets/delete/<int:set_id>",
    methods=["POST"]
)
def delete_exercise_set(set_id):

    if "user_id" not in session:

        flash(
            "Please login first.",
            "warning"
        )

        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:

        # Get the set and verify ownership.

        cursor.execute(
            """
            SELECT
                exercise_sets.id,
                exercises.workout_id

            FROM exercise_sets

            INNER JOIN exercises
                ON exercise_sets.exercise_id = exercises.id

            INNER JOIN workouts
                ON exercises.workout_id = workouts.id

            WHERE exercise_sets.id = %s
            AND workouts.user_id = %s
            """,
            (
                set_id,
                user_id
            )
        )

        exercise_set = cursor.fetchone()

        if not exercise_set:

            cursor.close()
            connection.close()

            flash(
                "Set not found.",
                "danger"
            )

            return redirect(
                url_for("workouts")
            )

        workout_id = exercise_set["workout_id"]

        cursor.execute(
            """
            DELETE FROM exercise_sets

            WHERE id = %s
            """,
            (set_id,)
        )

        connection.commit()

    except psycopg2.Error:

        connection.rollback()

        cursor.close()
        connection.close()

        flash(
            "Unable to delete set. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "workout_detail",
                workout_id=workout_id
            )
        )

    cursor.close()
    connection.close()

    flash(
        "Set deleted successfully.",
        "success"
    )

    return redirect(
        url_for(
            "workout_detail",
            workout_id=workout_id
        )
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("login"))


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":

    app.run(debug=True)
