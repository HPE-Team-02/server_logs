import threading
from kafka import KafkaConsumer, KafkaProducer
import json
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import time

# MySQL Database Connection Details
hostname = "localhost"
database = "server_monitoring"
username = "root"
password = "devendra@2004"

def connect_to_db():
    """Establishes a connection to the MySQL database."""   
    try:
        connection = mysql.connector.connect(
            host=hostname, database=database, user=username, password=password
        )
        if connection.is_connected():
            print("Connected to MySQL Server")
            return connection
    except Error as e:
        print("Error while connecting to MySQL", e)
        return None


def fetch_entire_table():
    """Fetches the entire 'server_logs' table and converts datetime fields to strings."""
    connection = connect_to_db()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM server_logs;")
        records = cursor.fetchall()

        # Convert datetime fields to string
        for record in records:
            for key, value in record.items():
                if isinstance(value, datetime):
                    record[key] = value.isoformat()  # Converts to "YYYY-MM-DDTHH:MM:SS"

        return records
    except Error as e:
        print(f"Error fetching data: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def kafka_consumer():
    """Kafka Consumer to process messages and insert/update MySQL."""
    consumer = KafkaConsumer(
        'user-data-topic',
        bootstrap_servers='localhost:9092',
        group_id='user-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )

    for message in consumer:
        row_data = message.value
        print(f"Received Row: {row_data}")

        log_id = row_data.get('id')
        if not log_id:
            print("Skipping record: 'id' is missing")
            continue

        # Get column names and values dynamically
        columns = ", ".join(row_data.keys())
        placeholders = ", ".join(["%s"] * len(row_data))
        update_clause = ", ".join([f"{key} = VALUES({key})" for key in row_data.keys() if key != "id"])

        insert_update_query = f"""
            INSERT INTO server_logs ({columns})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause};
        """

        connection = connect_to_db()
        if connection:
            try:
                cursor = connection.cursor()
                values = list(row_data.values())
                cursor.execute(insert_update_query, values)
                connection.commit()

                print(f"Inserted/Updated record with ID: {log_id}")

                # Fetch and send the updated table to Kafka
                entire_table = fetch_entire_table()
                if entire_table:
                    producer.send('server-data-topic', entire_table)
                    print("Sent updated table to server-data-topic")

            except Error as e:
                print(f"Error inserting/updating MySQL: {e}")

            finally:
                cursor.close()
                connection.close()
                print("MySQL connection closed")


def kafka_producer():
    """Kafka Producer that sends the entire table periodically."""
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )
    
    while True:
        records = fetch_entire_table()
        if records:
            producer.send('server-data-topic', records)
            print("Periodically sent entire table to server-data-topic")
        
        time.sleep(10)  # Send data every 60 seconds

# Running consumer and producer in separate threads
consumer_thread = threading.Thread(target=kafka_consumer)
producer_thread = threading.Thread(target=kafka_producer)

consumer_thread.start()
producer_thread.start()

consumer_thread.join()
producer_thread.join()
