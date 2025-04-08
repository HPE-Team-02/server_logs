from kafka import KafkaProducer, KafkaConsumer
import pandas as pd
import json
import os
import threading

# Kafka Producer Setup
def produce_messages():
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )
    
    # CSV File Path
    csv_file_path = "/home/devendra/Projects/HPE/server_logs/firmware_data.csv"
    
    # Define which columns to send
    columns_to_send = ['id', 'server_uuid', 'name']  # Modify as needed
    
    # Read CSV File
    df = pd.read_csv(csv_file_path, usecols=columns_to_send)
    
    # Send each row as a Kafka message
    for _, row in df.iterrows():
        message = row.to_dict()  # Convert selected columns to dictionary
        producer.send('user-data-topic', value=message)
        print(f"Sent: {message}")
    
    # Flush and close Kafka producer
    producer.flush()
    producer.close()
    print("Kafka producer closed")

# Function to process received messages
def process_message(data, existing_df):
    if not isinstance(data, dict) or 'id' not in data:
        print(f"Skipping malformed data: {data}")
        return existing_df
    
    if data['id'] in existing_df['id'].values:
        existing_df.loc[existing_df['id'] == data['id'], ['server_uuid', 'name']] = data['server_uuid'], data['name']
    else:
        existing_df = pd.concat([existing_df, pd.DataFrame([data])], ignore_index=True)
    
    return existing_df

# Kafka Consumer Setup
def consume_and_save():
    consumer = KafkaConsumer(
        'server-data-topic',
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True
    )
    
    output_file = "/home/devendra/Projects/HPE/server_logs/firmware_data.csv"
    
    # Load existing data if file exists
    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)
    else:
        existing_df = pd.DataFrame(columns=['id', 'server_uuid', 'name'])
    
    for message in consumer:
        data = message.value
        print(f"Received raw message: {data}")
        
        if isinstance(data, list):  # Handle batched messages
            for entry in data:
                existing_df = process_message(entry, existing_df)
        else:  # Single message
            existing_df = process_message(data, existing_df)
        
        existing_df.to_csv(output_file, index=False)
        print("Data updated in CSV.")

# Run producer and consumer in separate threads
producer_thread = threading.Thread(target=produce_messages)
consumer_thread = threading.Thread(target=consume_and_save)

producer_thread.start()
consumer_thread.start()

producer_thread.join()
consumer_thread.join()