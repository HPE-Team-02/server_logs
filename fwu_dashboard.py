import os
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote_plus
import gradio as gr
import pandas as pd
import plotly.express as px
import random

# Load environment variables
load_dotenv()

# Setup MongoDB connection
username = quote_plus(os.getenv("MONGO_USER") or "")
password = quote_plus(os.getenv("MONGO_PASS") or "")
host = os.getenv("MONGO_HOST") or "localhost"
port = os.getenv("MONGO_PORT") or "27017"
db_name = os.getenv("MONGO_DB") or "mydb"

uri = f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin"
client = MongoClient(uri)
db = client[db_name]
collection = db["extracted_info"]

# Fetch data from MongoDB
def fetch_data_from_mongo():
    doc = collection.find_one()
    if not doc:
        return None
    doc["_id"] = str(doc["_id"])  # Convert ObjectId to str
    return doc

# Process and build dashboard data
def build_dashboard_data(mongo_data):
    if mongo_data is None:
        mongo_data = {
            "OneView": {"OV version": "N/A"},
            "Server": {"Gen": "N/A", "OS": "N/A"},
            "Firmware Update": {"SPP Used": "N/A", "Install state": "N/A"},
            "Components": [
                {"Installed Version": "1.0", "To Version": "1.1", "FileName": "comp1.rpm"},
                {"Installed Version": "2.0", "To Version": "2.1", "FileName": "comp2.exe"}
            ],
            "Install set Response": {"SUM Version": "N/A"}
        }

    total_jobs = 282
    succeeded = 263
    failed = 15
    success_rate = round((succeeded / total_jobs) * 100, 1)

    customer_success_df = pd.DataFrame({
        "Customer Name": ["Customer A", "Customer B", "Customer C"],
        "Jobs Created": [40, 15, 10],
        "Failures": [2, 1, 0],
        "Success Rate (%)": [95, 93.3, 100]
    })

    error_df = pd.DataFrame({
        "FWE Code": ["FWE-102", "FWE-109", "FWE-108", "FWE-155"],
        "Occurrences": [7, 5, 2, 1],
        "Error Description": [
            "COMPONENT_UPDATE_FAILURE",
            "ISO_INSTALLER_CREATION_FAILURE",
            "COMPONENT_DOWNLOAD_FAILURE",
            "INITIAL_POWER_ON_FAILURE"
        ]
    })

    failed_jobs_df = pd.DataFrame()
    if failed > 0 and not error_df.empty:
        failed_jobs_df = pd.DataFrame({
            "Job ID": [f"JOB_{str(i).zfill(3)}" for i in range(1, failed + 1)],
            "Customer Name": [random.choice(customer_success_df["Customer Name"]) for _ in range(failed)],
            "Error Code": [random.choice(error_df["FWE Code"]) for _ in range(failed)],
            "Timestamp": pd.to_datetime(['2023-01-01 00:00:00'] * failed) + pd.to_timedelta([f'{i*2}h {i*15}m' for i in range(failed)]),
            "Failed Component": [random.choice(mongo_data.get("Components", [{"FileName": "N/A"}]))["FileName"] for _ in range(failed)],
            "Details": [f"Investigation needed for JOB_{str(i).zfill(3)}." for i in range(1, failed + 1)]
        })

    fig = px.pie(
        error_df,
        names="FWE Code",
        values="Occurrences",
        hole=0.5,
        title="FWE Error Distribution"
    )
    fig.update_traces(textinfo='percent+label')

    return {
        "success_rate": f"{success_rate}%",
        "total_jobs": str(total_jobs),
        "succeeded": str(succeeded),
        "failed": str(failed),
        "oneview_ov_version": mongo_data.get("OneView", {}).get("OV version", "N/A"),
        "oneview_type": mongo_data.get("OneView", {}).get("OV Type", "N/A"),
        "firmware_spp_used": mongo_data.get("Firmware Update", {}).get("SPP Used", "N/A"),
        "firmware_install_state": mongo_data.get("Firmware Update", {}).get("Install state", "N/A"),
        "sum_version": mongo_data.get("Install set Response", {}).get("SUM Version", "N/A"),
        "fig": fig,
        "failed_jobs_df": failed_jobs_df,
        "error_df": error_df,
        "customer_success_df": customer_success_df
    }

# Fetch and build data
mongo_data = fetch_data_from_mongo()
dashboard_data = build_dashboard_data(mongo_data)

# Gradio Dashboard
with gr.Blocks(theme=gr.themes.Soft()) as dashboard:
    gr.Markdown("# 🔧 Firmware Update Summary Dashboard")

    with gr.Row():
        with gr.Column():
            gr.Markdown("## 📊 Job Overview")
            gr.Label(value=dashboard_data["success_rate"], label="✅ Success Rate")
            gr.Label(value=dashboard_data["total_jobs"], label="📁 Total Jobs")
            gr.Label(value=dashboard_data["succeeded"], label="✔️ Succeeded")
            gr.Label(value=dashboard_data["failed"], label="❌ Failed")

        with gr.Column():
            gr.Markdown("## 🛠️ OneView Info")
            gr.Textbox(value=dashboard_data["oneview_ov_version"], label="OV Version")
            gr.Textbox(value=dashboard_data["oneview_type"], label="OV Type")
            gr.Textbox(value=dashboard_data["firmware_spp_used"], label="SPP Used")
            gr.Textbox(value=dashboard_data["firmware_install_state"], label="Install State")
            gr.Textbox(value=dashboard_data["sum_version"], label="SUM Version")

    gr.Markdown("### 📉 Error Distribution")
    gr.Plot(value=dashboard_data["fig"])

    gr.Markdown("### 🔁 Customer Success Summary")
    gr.Dataframe(value=dashboard_data["customer_success_df"])

    gr.Markdown("### ❌ Failed Jobs Log")
    gr.Dataframe(value=dashboard_data["failed_jobs_df"])

# Launch dashboard
dashboard.launch()
