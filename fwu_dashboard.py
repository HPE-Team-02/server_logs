import os
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote_plus
import gradio as gr
import pandas as pd
import plotly.express as px
import random

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
        return None
    doc["_id"] = str(doc["_id"])
    return doc


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
        "firmware_spp_used": mongo_data.get("Firmware Update", {}).get("SPP Used", "N/A"),
        "firmware_install_state": mongo_data.get("Firmware Update", {}).get("Install state", "N/A"),
        "install_sum_version": mongo_data.get("Install set Response", {}).get("SUM Version", "N/A"),
        "server_gen": mongo_data.get("Server", {}).get("Gen", "N/A"),
        "server_os": mongo_data.get("Server", {}).get("OS", "N/A"),
        "failed_jobs_df": failed_jobs_df,
        "components_df": pd.DataFrame(mongo_data.get("Components", [])),
        "error_pie_fig": fig,
        "customer_success_df": customer_success_df,
        "error_df": error_df
    }


def refresh_dashboard():
    mongo_data = fetch_data_from_mongo()
    data = build_dashboard_data(mongo_data)
    # Return all UI elements in order of output
    return (
        data["success_rate"],
        data["total_jobs"],
        data["succeeded"],
        data["failed"],
        data["oneview_ov_version"],
        data["firmware_spp_used"],
        data["firmware_install_state"],
        data["install_sum_version"],
        data["server_gen"],
        data["server_os"],
        data["failed_jobs_df"],
        data["components_df"],
        data["error_pie_fig"],
        data["customer_success_df"],
        data["error_df"]
    )


with gr.Blocks(theme=gr.themes.Soft()) as dashboard:
    gr.Markdown("# 🔧 Firmware Update Summary Dashboard")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 📊 Job Overview")
            success_label = gr.Label(label="✅ Success Rate")
            total_jobs_label = gr.Label(label="📁 Total Jobs")
            succeeded_label = gr.Label(label="✔️ Succeeded")
            failed_label = gr.Label(label="❌ Failed")

        with gr.Column(scale=1):
            gr.Markdown("## 🛠️ OneView Info")
            ov_version = gr.Textbox(label="OV Version", interactive=False)
            spp_used = gr.Textbox(label="SPP Used", interactive=False)
            install_state = gr.Textbox(label="Install State", interactive=False)
            sum_version = gr.Textbox(label="SUM Version", interactive=False)
            server_gen = gr.Textbox(label="Server Gen", interactive=False)
            server_os = gr.Textbox(label="OS", interactive=False)

    refresh_btn = gr.Button("🔄 Refresh Data")

    with gr.Accordion("🚨 Failed Job Details (click to expand)", open=False):
        failed_jobs_df = gr.Dataframe(headers=["Job ID", "Customer Name", "Error Code", "Timestamp", "Failed Component", "Details"])

    gr.Markdown("## 🧩 Component Versions")
    components_df = gr.Dataframe(headers=["Installed Version", "To Version", "DeviceClass", "TargetGUID", "FileName"])

    gr.Markdown("## 📈 Error Distribution")
    error_pie = gr.Plot()

    gr.Markdown("## 🧑‍💻 Customer Success Overview")
    customer_success_table = gr.Dataframe()

    gr.Markdown("## ❗ FWE Occurrences")
    error_table = gr.Dataframe()

    # Hook up refresh button to update all outputs
    refresh_btn.click(
        fn=refresh_dashboard,
        inputs=[],
        outputs=[
            success_label,
            total_jobs_label,
            succeeded_label,
            failed_label,
            ov_version,
            spp_used,
            install_state,
            sum_version,
            server_gen,
            server_os,
            failed_jobs_df,
            components_df,
            error_pie,
            customer_success_table,
            error_table
        ],
        queue=True
    )

dashboard.launch()
