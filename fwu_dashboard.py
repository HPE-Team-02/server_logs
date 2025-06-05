import gradio as gr
import pandas as pd
import plotly.express as px
import json
import random # For generating dummy failed job data

# ✅ Load JSON from file
# Ensure 'extracted_info.json' is in the same directory as this script,
# or provide the full path to the file.
# For demonstration, let's create a dummy json_data if the file is not found,
# so the script can run.
try:
    with open('extracted_info.json') as f:
        json_data = json.load(f)
except FileNotFoundError:
    print("Warning: 'extracted_info.json' not found. Using dummy data for demonstration.")
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


# Simulated Job Stats
total_jobs = 282
succeeded = 263
failed = 15
success_rate = round((succeeded / total_jobs) * 100, 1) if total_jobs > 0 else 0

# Dummy Tables
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

# Dummy data for failed jobs
if failed > 0 and not error_df.empty:
    failed_jobs_data = {
        "Job ID": [f"JOB_{str(i).zfill(3)}" for i in range(1, failed + 1)],
        "Customer Name": [random.choice(customer_success_df["Customer Name"]) if not customer_success_df.empty else f"Customer {chr(65 + i % 3)}" for i in range(failed)],
        "Error Code": [random.choice(error_df["FWE Code"]) for _ in range(failed)],
        "Timestamp": pd.to_datetime(['2023-01-01 00:00:00'] * failed) + pd.to_timedelta([f'{i*2}h {i*15}m' for i in range(failed)]),
        "Failed Component": [random.choice(json_data.get("Components", [{"FileName": "N/A"}]))["FileName"] for _ in range(failed)],
        "Details": [f"Further investigation needed for error on component X related to job JOB_{str(i).zfill(3)}." for i in range(1, failed + 1)]
    }
    failed_jobs_df = pd.DataFrame(failed_jobs_data)
else:
    failed_jobs_df = pd.DataFrame(columns=["Job ID", "Customer Name", "Error Code", "Timestamp", "Failed Component", "Details"])


# Donut Chart
fig = px.pie(error_df, names='FWE Code', values='Occurrences', hole=0.5, title='FWE Occurrences')
fig.update_traces(textinfo='percent+label', pull=[0.05, 0, 0, 0])
fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))

# Gradio Dashboard
with gr.Blocks(theme=gr.themes.Soft(), css="body {background: #f7f9fa;}") as dashboard:
    gr.Markdown("""
    <div style='text-align:center; margin-bottom: 1.5em;'>
        <h2 style='color:#2d3748;'>🔧 FWU Summary Dashboard</h2>
        <p style='color:#4a5568;'>Firmware Update Job Overview & Insights</p>
    </div>
    """)

    with gr.Group(): # Group for overall stats
        with gr.Row():
            gr.HTML(f"""
                <div style='background:#e6fffa; border-radius:10px; padding:1em; text-align:center; width:100%; height:100%; display: flex; flex-direction: column; justify-content: center;'>
                    <span style='font-size:2.2em; color:#319795; font-weight:bold;'>{success_rate}%</span><br>
                    <span style='color:#4a5568;'>Overall Success Rate</span>
                </div>
            """)
            gr.HTML(f"""
                <div style='background:#ebf8ff; border-radius:10px; padding:1em; text-align:center; width:100%; height:100%; display: flex; flex-direction: column; justify-content: center;'>
                    <span style='font-size:2em; color:#3182ce; font-weight:bold;'>{total_jobs}</span><br>
                    <span style='color:#4a5568;'>Total Jobs</span>
                </div>
            """)
            gr.HTML(f"""
                <div style='background:#f0fff4; border-radius:10px; padding:1em; text-align:center; width:100%; height:100%; display: flex; flex-direction: column; justify-content: center;'>
                    <span style='font-size:2em; color:#38a169; font-weight:bold;'>{succeeded}</span><br>
                    <span style='color:#4a5568;'>Succeeded</span>
                </div>
            """)
            gr.HTML(f"""
                <div style='background:#fff5f5; border-radius:10px; padding:1em; text-align:center; width:100%; height:100%; display: flex; flex-direction: column; justify-content: center;'>
                    <span style='font-size:2em; color:#e53e3e; font-weight:bold;'>{failed}</span><br>
                    <span style='color:#4a5568;'>Failed</span>
                </div>
            """)
    
    # Accordion for Failed Job Details - placed after the main stats
    if failed > 0:
        with gr.Accordion(f"Failed Job Details ({failed} occurrences) - Click to expand", open=False):
            gr.Dataframe(
                failed_jobs_df, 
                label="Detailed Failure Report", 
                interactive=False, 
                wrap=True
            )
    else:
        gr.Markdown("<p style='text-align:center; color:#38a169;'>No failed jobs to report. Great job!</p>")


    gr.Markdown("---")

    with gr.Group():
        gr.Markdown("### System & Firmware Details")
        with gr.Row():
            # Wrapping each Label in a Column with scale=1 for equal width distribution
            with gr.Column(scale=1):
                gr.Label(json_data["OneView"]["OV version"], label="OV Version", elem_id="ov-version")
            with gr.Column(scale=1):
                gr.Label(json_data["Server"]["Gen"], label="Server Gen", elem_id="server-gen")
            with gr.Column(scale=1):
                gr.Label(json_data["Server"]["OS"], label="Server OS", elem_id="server-os")
            with gr.Column(scale=1):
                gr.Label(json_data["Firmware Update"]["SPP Used"], label="SPP Used", elem_id="spp-used")
            with gr.Column(scale=1):
                gr.Label(json_data["Firmware Update"]["Install state"], label="Install State", elem_id="install-state")

    gr.Markdown("---")

    with gr.Group():
        gr.Markdown("### Component Versions")
        if "Components" in json_data and isinstance(json_data["Components"], list):
            for component in json_data["Components"]:
                if isinstance(component, dict):
                    with gr.Row(): 
                        gr.Label(component.get("To Version", "N/A"), label="To Ver")
                        gr.Label(component.get("FileName", "N/A"), label="Firmware File")
                else:
                    with gr.Row():
                        gr.Label("Invalid component data", label="Error")
        else:
            gr.Markdown("No component data available or incorrect format.")

    with gr.Row(): 
        gr.Label(json_data["Install set Response"]["SUM Version"], label="SUM Ver")

    gr.Markdown("---")

    with gr.Group():
        gr.Markdown("### Error Distribution")
        with gr.Row():
            gr.Plot(fig)

    gr.Markdown("---")

    with gr.Group():
        with gr.Row():
            gr.Dataframe(customer_success_df, label="Customer Success Rate", interactive=True, wrap=True)
            gr.Dataframe(error_df, label="FWE Occurrences by Error Code", interactive=True, wrap=True)

    gr.HTML("<div style='text-align:center; color:#a0aec0; margin-top:2em;'>© 2025 HPE FWU Dashboard</div>")

# To run the dashboard:
if __name__ == "__main__":
    dashboard.launch()