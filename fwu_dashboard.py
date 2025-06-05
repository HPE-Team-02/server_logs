import os
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote_plus
import gradio as gr
import pandas as pd
import plotly.express as px
import random

# Load .env values
load_dotenv()

username = quote_plus(os.getenv("MONGO_USER"))
password = quote_plus(os.getenv("MONGO_PASS"))
host = os.getenv("MONGO_HOST")
port = os.getenv("MONGO_PORT")
db_name = os.getenv("MONGO_DB")

uri = f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin"
client = MongoClient(uri)
db = client[db_name]
collection = db["extracted_info"]

def fetch_data_from_mongo():
    doc = collection.find_one()
    if not doc:
        return {}
    doc["_id"] = str(doc["_id"])
    return doc

def dict_to_df(data: dict):
    # Converts dictionary to a DataFrame with columns: Key | Value
    if not data:
        return pd.DataFrame(columns=["Key", "Value"])
    df = pd.DataFrame(list(data.items()), columns=["Key", "Value"])
    return df

def build_dashboard():
    mongo_data = fetch_data_from_mongo()

    total_tasks = 282
    succeeded = 263
    failed = 19

    # MongoDB Sections as DataFrames
    oneview_df = dict_to_df(mongo_data.get("OneView", {}))
    server_df = dict_to_df(mongo_data.get("Server", {}))
    firmware_df = dict_to_df(mongo_data.get("Firmware Update", {}))
    install_set_df = dict_to_df(mongo_data.get("Install set Response", {}))

    # Error Table (static SHFW errors)
    error_df = pd.DataFrame({
        "SHFW Code": ["SHFW_036", "SHFW_001", "SHFW_007", "SHFW_012"],
        "Occurrences": [7, 5, 2, 1],
        "Error Description": [
            "Component failure",
            "Online firmware update failed",
            "Dependency on newer driver versions",
            "SUT hung for over 2 hours"
        ]
    })

    # Failed Tasks Table
    failed_tasks_df = pd.DataFrame({
        "Task ID": [f"TASK_{str(i).zfill(3)}" for i in range(1, failed + 1)],
        "Error Code": [random.choice(error_df["SHFW Code"]) for _ in range(failed)],
        "Timestamp": pd.to_datetime(['2023-01-01 00:00:00'] * failed) +
                     pd.to_timedelta([f'{i*2}h {i*15}m' for i in range(failed)]),
        "Failed Component": [f"comp_{random.randint(1,3)}.rpm" for _ in range(failed)],
        "Details": [f"Investigation needed for TASK_{str(i).zfill(3)}." for i in range(1, failed + 1)]
    })

    # Pie Chart (Success vs Component Failure)
    pie_fig = px.pie(
        names=["Success", "Component Failure"],
        values=[succeeded, failed],
        hole=0.5,
        title="Task Outcome Breakdown"
    )
    pie_fig.update_traces(textinfo='percent+label')

    return oneview_df, server_df, firmware_df, install_set_df, pie_fig, failed_tasks_df, error_df

with gr.Blocks(theme=gr.themes.Soft()) as dashboard:
    gr.Markdown("## Firmware Update Dashboard ")

    refresh_btn = gr.Button("Refresh Data", variant="primary", elem_id="refresh_button")

    # MongoDB info tables
    with gr.Row():
        oneview_table = gr.Dataframe(label="OneView Info", interactive=False)
        server_table = gr.Dataframe(label="Server Info", interactive=False)
    with gr.Row():
        firmware_table = gr.Dataframe(label="Firmware Update Info", interactive=False)
        install_set_table = gr.Dataframe(label="Install Set Response", interactive=False)

    chart_output = gr.Plot()
    failed_table = gr.Dataframe(label="Failed Tasks (Component Failures Only)", interactive=False)
    error_table = gr.Dataframe(label="SHFW Component Error Log", interactive=False)

    def refresh_data():
        return build_dashboard()

    refresh_btn.click(
        refresh_data,
        outputs=[
            oneview_table, server_table,
            firmware_table, install_set_table,
            chart_output, failed_table, error_table
        ]
    )

    dashboard.load(
        build_dashboard,
        outputs=[
            oneview_table, server_table,
            firmware_table, install_set_table,
            chart_output, failed_table, error_table
        ]
    )

dashboard.launch()
