import os
import re
import json
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from dotenv import load_dotenv

# Define the paths
TARGET_DIR = r"D:\sem-6\HPE\SupportDump-20250323T053844Z-001\SupportDump\CSFE-64399_ilo_component_failure\CN7544043XX_appliance_bay_1-corpus-cristi.proto.lab-CI-2025_02_13-10_52_27\sumservice\ci\var\fwdrivers\installsets"
LOG_FILE_PATH = r"D:\sem-6\HPE\SupportDump-20250323T053844Z-001\SupportDump\CSFE-64399_ilo_component_failure\appliance\ci\logs\ciDebug.log"

# Load environment variables from .env file
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

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

def insert_into_db(server_details):
    """Insert extracted server details into MySQL database."""
    connection = connect_to_db()
    if not connection:
        return
    
    cursor = connection.cursor()
    query = """
        INSERT INTO server_logs (server_uuid, name, filename, updatableBy, component, state, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    for details in server_details:
        try:
            # Convert timestamp from string to datetime
            timestamp = datetime.strptime(details["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
            updatable_by = json.dumps(details["updatableBy"])  # Store as JSON text

            cursor.execute(query, (
                details["server_uuid"], 
                details["name"], 
                details["filename"], 
                updatable_by, 
                details["component"], 
                details["state"], 
                timestamp
            ))
        except Error as e:
            print(f"Error inserting data: {e}")

    connection.commit()
    cursor.close()
    connection.close()
    print("Data successfully inserted into MySQL.")

def fetch_folders(directory):
    """Fetch all folder names from the given directory."""
    try:
        return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]
    except FileNotFoundError:
        print(f"Error: Directory '{directory}' not found.")
        return []

def filter_valid_matches(matches):
    """Filter out matches that contain 'Members' as an empty array."""
    return [line for line in matches if not re.search(r'"Members"\s*:\s*\[\s*\]', line)]

def clean_incomplete_members(parsed_data):
    """Remove incomplete or malformed entries from the 'Members' array."""
    if "Members" not in parsed_data:
        return parsed_data  # Return as-is if 'Members' key is missing

    cleaned_members = []
    for member in parsed_data.get("Members", []):
        if isinstance(member, dict) and all(key in member for key in ["Name", "Filename", "UpdatableBy", "Component", "State", "Modified"]):
            cleaned_members.append(member)
        else:
            print(f"Warning: Incomplete or malformed member skipped: {member}")
    
    parsed_data["Members"] = cleaned_members
    return parsed_data

def parse_members_from_match(match_line):
    """Extract details from the 'Members' key in the match line and return as a list of dictionaries."""
    details_list = []
    try:
        server_uuid = re.search(r"server (\S+)", match_line).group(1)
        json_start = match_line.find("is {") + 3
        json_data = match_line[json_start:].strip()
        parsed_data = json.loads(json_data)

        parsed_data = clean_incomplete_members(parsed_data)

        for member in parsed_data.get("Members", []):
            details = {
                "server_uuid": server_uuid,
                "name": member.get("Name"),
                "filename": member.get("Filename"),
                "updatableBy": member.get("UpdatableBy"),
                "component": member.get("Component"),
                "state": member.get("State"),
                "timestamp": member.get("Modified"),
            }
            details_list.append(details)
    except (AttributeError, json.JSONDecodeError) as e:
        print(f"Warning: Could not extract details from line: {match_line}. Error: {e}")
    return details_list

def search_log_for_uuid(log_file, uuids):
    """Search the log file for occurrences of 'task queue details of the firmware update on server <uuid>' and filter results."""
    if not os.path.exists(log_file):
        print(f"Error: Log file '{log_file}' not found.")
        return []
    
    with open(log_file, 'r', encoding='utf-8') as file:
        log_content = file.readlines()
    
    pattern = re.compile(r"task queue details of the firmware update on server (\S+)")
    matches = []

    for line in log_content:
        match = pattern.search(line)
        if match and match.group(1) in uuids:
            matches.append(line.strip())

    filtered_matches = filter_valid_matches(matches)
    
    server_details = []
    for match in filtered_matches:
        details = parse_members_from_match(match)
        if details:
            server_details.extend(details)

    return server_details

def main():
    folders = fetch_folders(TARGET_DIR)
    if not folders:
        print("No folders found in the directory.")
        return
    
    print(f"Fetched {len(folders)} folder names from '{TARGET_DIR}'")
    server_details = search_log_for_uuid(LOG_FILE_PATH, folders)

    if server_details:
        insert_into_db(server_details)
    else:
        print("No relevant server details found in logs.")

if __name__ == "__main__":
    main()
