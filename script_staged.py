import os
import re
import json
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

LOG_FILE_PATH_STAGED = os.getenv("LOG_FILE_PATH_STAGED")

# Ensure the path is properly loaded
if not LOG_FILE_PATH_STAGED:
    print("Error: Log file path is not set in the .env file.")
else:
    def connect_to_db():
        """Establish a connection to the MySQL database."""
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                print("Connected to MySQL database")
            return connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None

    def insert_error_log(server_uuid):
        """Insert extracted server UUID into MySQL database with error state."""
        connection = connect_to_db()
        if not connection:
            return
        
        cursor = connection.cursor()
        query = """
            INSERT INTO server_logs (server_uuid, name, filename, updatableBy, component, state, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            timestamp = datetime.now(datetime.timezone.utc) # Current timestamp
            cursor.execute(query, (server_uuid, "NA", "NA", "NA", "NA", "ERROR in staging", timestamp))
            connection.commit()
            print(f"Inserted error log for server UUID: {server_uuid}")
        except Error as e:
            print(f"Error inserting data: {e}")
        finally:
            cursor.close()
            connection.close()

    def parse_log_file(log_file_path):
        """Parse the log file to find server UUIDs with the specific error message."""
        error_pattern = re.compile(r"Install set response is empty for server ([\w-]+)")
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as log_file:
                for line in log_file:
                    match = error_pattern.search(line)
                    if match:
                        server_uuid = match.group(1)
                        insert_error_log(server_uuid)
        except FileNotFoundError:
            print("Log file not found.")
        except Exception as e:
            print(f"Error reading log file: {e}")

    parse_log_file(LOG_FILE_PATH_STAGED)
