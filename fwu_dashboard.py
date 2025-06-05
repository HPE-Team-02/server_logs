import gradio as gr
import pandas as pd
import plotly.express as px
import json
import random

# Load JSON data
try:
    with open('extracted_info.json') as f:
        json_data = json.load(f)
except FileNotFoundError:
    print("Warning: 'extracted_info.json' not found. Using dummy data.")
    json_data = {
        "OneView": {"OV version": "N/A"},
        "Server": {"Gen": "N/A", "OS": "N/A"},
        "Firmware Update": {"SPP Used": "N/A", "Install state": "N/A"},
        "Components": [
            {"Installed Version": "1.0", "To Version": "1.1", "FileName": "comp1.rpm"},
            {"Installed Version": "2.0", "To Version": "2.1", "FileName": "comp2.exe"}
        ],
        "Install set Response": {"SUM Version": "N/A"}
    }

# Simulated job stats
total_jobs = 282
succeeded = 263
failed = 15
success_rate = round((succeeded / total_jobs) * 100, 1)

# Dummy tables
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
        "Failed Component": [random.choice(json_data.get("Components", [{"FileName": "N/A"}]))["FileName"] for _ in range(failed)],
        "Details": [f"Investigation needed for JOB_{str(i).zfill(3)}." for i in range(1, failed + 1)]
    })

# Donut chart
fig = px.pie(
    error_df,
    names="FWE Code",
    values="Occurrences",
    hole=0.5,
    title="FWE Error Distribution"
)
fig.update_traces(textinfo='percent+label')

# Gradio layout
with gr.Blocks(theme=gr.themes.Soft()) as dashboard:
    gr.Markdown("# 🔧 Firmware Update Summary Dashboard")

    # Job Overview and OneView Info side by side
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 📊 Job Overview")
            gr.Label(f"{success_rate}%", label="✅ Success Rate")
            gr.Label(str(total_jobs), label="📁 Total Jobs")
            gr.Label(str(succeeded), label="✔️ Succeeded")
            gr.Label(str(failed), label="❌ Failed")

        with gr.Column(scale=1):
            gr.Markdown("## 🛠️ OneView Info")
            gr.Textbox(value=json_data["OneView"].get("OV version", "N/A"), label="OV Version")
            gr.Textbox(value=json_data["Firmware Update"].get("SPP Used", "N/A"), label="SPP Used")
            gr.Textbox(value=json_data["Firmware Update"].get("Install state", "N/A"), label="Install State")
            gr.Textbox(value=json_data["Install set Response"].get("SUM Version", "N/A"), label="SUM Version")
            gr.Textbox(value=json_data["Server"].get("Gen", "N/A"), label="Server Gen")
            gr.Textbox(value=json_data["Server"].get("OS", "N/A"), label="OS")

    # Failed Job Details as collapsible full-width accordion
    with gr.Accordion("🚨 Failed Job Details (click to expand)", open=False):
        gr.Dataframe(failed_jobs_df, wrap=True)

    # Components
    gr.Markdown("## 🧩 Component Versions")
    component_df = pd.DataFrame(json_data.get("Components", []))
    gr.Dataframe(component_df, wrap=True)

    # Error Distribution
    gr.Markdown("## 📈 Error Distribution")
    gr.Plot(fig)

    # Customer Success Overview
    gr.Markdown("## 🧑‍💻 Customer Success Overview")
    gr.Dataframe(customer_success_df, wrap=True)

    # FWE Occurrences
    gr.Markdown("## ❗ FWE Occurrences")
    gr.Dataframe(error_df, wrap=True)

dashboard.launch()
