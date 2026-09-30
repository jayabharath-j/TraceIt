from werkzeug.security import generate_password_hash
import mysql.connector
from getpass import getpass

print("=== Fitness Tracker Admin Creation ===")

name = input("Admin name: ")
email = "adminofft@gmail.com"
password = getpass("Admin password: ")

hashed_password = generate_password_hash(password)

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="7716",
    database="fitness_tracker"
)

cursor = connection.cursor()

cursor.execute(
    """
    INSERT INTO users (name, email, password, role)
    VALUES (%s, %s, %s, 'admin')
    """,
    (name, email, hashed_password)
)

connection.commit()

cursor.close()
connection.close()

print()
print("Admin account created successfully!")
print("Email:", email)