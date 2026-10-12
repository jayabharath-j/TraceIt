# TRACEIT — Track, Train, Transform 🏋️

**TraceIt is a fitness tracking web application built with Flask and PostgreSQL that helps users manage fitness goals, track nutrition, record workouts, and monitor their progress through a single platform.

🌐 **Live Demo:** [TraceIt](https://traceit-r8e0.onrender.com/)

---

## 📌 About the Project

Maintaining fitness goals requires consistency and a clear understanding of daily activities. TraceIt provides a centralized platform for tracking fitness goals, monitoring nutritional intake, recording workouts, and reviewing progress.

The application combines fitness and nutrition tracking with a user-friendly interface, helping users organize their fitness journey in one place.

## ✨ Features

- **User Authentication** — Register and log in to access a personal account.
- **Fitness Goal Management** — Set and manage weight and nutritional goals.
- **Nutrition Tracking** — Monitor daily calories, protein, carbohydrates, and fat.
- **Food Logging** — Record food intake based on cooked food weight.
- **Progress Tracking** — Add, view, edit, and delete progress records.
- **Workout Tracking** — Record workout activities and maintain workout history.
- **Dashboard** — Access fitness information and tracking features from one place.
- **Dark and Light Mode** — Switch between themes for a comfortable viewing experience.
- **Admin Dashboard** — Provide administrative features and activity charts for authorized administrators.

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Backend Framework | Flask |
| Frontend | HTML5, CSS3, JavaScript |
| UI Framework | Bootstrap |
| Database | PostgreSQL |
| Form Handling | Flask-WTF |
| Data Processing | Pandas, NumPy |
| Deployment | Render, Gunicorn |
| Version Control | Git, GitHub |

## 🏗️ Application Overview

TraceIt follows a web application architecture in which:

1. Users interact with the application through a responsive web interface.
2. Flask handles application routes, business logic, and user requests.
3. PostgreSQL stores application data.
4. The application retrieves and updates records to display fitness goals, nutrition information, workouts, and progress.

## 🚀 Getting Started

Follow these instructions to run TraceIt locally.

### Prerequisites

Make sure you have the following installed:

- Python 3.x
- PostgreSQL
- Git
- A code editor such as Visual Studio Code

### 1. Clone the Repository

```bash
git clone https://github.com/jayabharath-j/TraceIt.git
cd TraceIt
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and add the configuration variables required by your application.

For example:

```env
SECRET_KEY=your_secret_key
DATABASE_URL=your_postgresql_connection_url
```

Replace the example values with your actual configuration. The variable names must match those read by your application.

**Security:** Never commit your `.env` file, database credentials, or production secret keys to GitHub.

### 5. Set Up PostgreSQL

1. Start PostgreSQL.
2. Create a database for TraceIt.
3. Configure the database connection using your environment variables.
4. Create the required tables using your application's existing schema or database initialization process.

Ensure that your local PostgreSQL database and connection settings match the application's configuration.

### 6. Run the Application

Start the Flask application using its configured entry point. If the entry point is `app.py`, run:

```bash
python app.py
```

Open the local address shown in the terminal. If the application uses Flask's default development port, the address is:

```text
http://127.0.0.1:5000/
```

## 🌍 Deployment

TraceIt is deployed on Render.

**Live Application:** https://traceit-r8e0.onrender.com/

The deployed application requires its production environment variables and PostgreSQL connection to be configured correctly.

## 🔒 Security Considerations

- Store credentials and secret keys in environment variables.
- Protect authenticated routes from unauthorized access.
- Restrict administrative functionality to authorized users.
- Avoid exposing sensitive user information.
- Keep production credentials out of source control.

## 📚 Future Improvements

Potential enhancements for TraceIt include:

- Visual progress reports and historical trend analysis.
- More detailed workout statistics.
- Improved mobile experience.
- Additional nutrition insights and goal recommendations.

## 👨‍💻 Developer

**Jayabharath J**

- **GitHub:** [jayabharath-j](https://github.com/jayabharath-j)
- **LinkedIn:** [mejayabharath](https://www.linkedin.com/in/mejayabharath/)

## 📄 License

This project was developed as a personal portfolio project to practise and demonstrate web development skills. Contact the author before redistributing or reusing the project.
