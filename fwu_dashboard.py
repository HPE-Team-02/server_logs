import os
import pandas as pd
from pymongo import MongoClient
from bson import ObjectId
from urllib.parse import quote_plus
from dotenv import load_dotenv
import gradio as gr
import plotly.express as px

# Load env variables
load_dotenv()

# MongoDB setup
username = quote_plus(os.getenv("MONGO_USER"))
password = quote_plus(os.getenv("MONGO_PASS"))
host = os.getenv("MONGO_HOST")
port = os.getenv("MONGO_PORT")
db_name = os.getenv("MONGO_DB")

uri = f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin"
client = MongoClient(uri)
db = client[db_name]
collections_list = db.list_collection_names()
for collection in collections_list:
    if collection == "Analytics":
        collections_list.remove(collection)

# Helper functions
def fetch_all_tasks(collection_name):
    return list(db[collection_name].find())

def build_summary_from_analytics():
    analytics_doc = db["Analytics"].find_one()
    if not analytics_doc:
        return pd.DataFrame(), 0, 0
    successes = analytics_doc.get("successful_updates", 0)
    failures = analytics_doc.get("failed_updates", 0)
    total = successes + failures
    df = pd.DataFrame({
        "Status": ["Total Tasks", "Succeeded", "Failed"],
        "Count": [total, successes, failures]
    })
    return df, successes, failures

def dict_to_df(d):
    return pd.DataFrame(list(d.items()), columns=["Key", "Value"]) if d else pd.DataFrame(columns=["Key", "Value"])

def show_task_details(collection_name, task_id):
    doc = db[collection_name].find_one({"_id": ObjectId(task_id)})
    if not doc:
        return [pd.DataFrame()] * 5

    all_components = doc.get("Components", [])
    failed_names = doc.get("Failed Components", [])

    if not isinstance(failed_names, list):
        failed_names = [failed_names]

    failed_names_clean = set(fn.strip() for fn in failed_names if fn)

    filtered_components = [
        comp for comp in all_components
        if comp.get("FileName", "").strip() in failed_names_clean
    ]

    print("DEBUG: Failed names from DB:", failed_names_clean)
    print("DEBUG: Matched FileNames:", [comp.get("FileName") for comp in filtered_components])

    columns = ["FileName", "Installed Version", "To Version", "TargetGUID"]
    components_df = pd.DataFrame(filtered_components)[columns] if filtered_components else pd.DataFrame([], columns=columns)

    return (
        dict_to_df(doc.get("OneView", {})),
        dict_to_df(doc.get("Server", {})),
        dict_to_df(doc.get("Firmware Update", {})),
        dict_to_df(doc.get("Install set Response", {})),
        components_df
    )

def make_pie_chart(successes, failures):
    df = pd.DataFrame({"Status": ["Succeeded", "Failed"], "Count": [successes, failures]})
    return px.pie(
        df,
        names="Status",
        values="Count",
        title="Task Status Distribution",
        color="Status",
        color_discrete_map={"Succeeded": "green", "Failed": "red"}
    )

# Gradio UI
dashboard = gr.Blocks(theme=gr.themes.Soft())

with dashboard:
    gr.Markdown("## 📊 Firmware Update Summary Dashboard")

    with gr.Column(visible=True) as summary_section:
        summary_df = gr.Dataframe(label="Task Summary", interactive=False)
        pie_plot = gr.Plot(label="Task Status Pie Chart")

        with gr.Accordion("Task Information", open=False):
            failed_collections_df = gr.Dataframe(label="Collections", interactive=False)
            failed_tasks_df = gr.Dataframe(label="Task Details", interactive=False)

    with gr.Column(visible=False) as detail_section:
        gr.Markdown("### 📂 Selected Task Info")
        with gr.Row():
            oneview_df = gr.Dataframe(label="OneView", interactive=False)
            server_df = gr.Dataframe(label="Server", interactive=False)
        with gr.Row():
            firmware_df = gr.Dataframe(label="Firmware Update", interactive=False)
            install_df = gr.Dataframe(label="Install Set Response", interactive=False)
        components_df = gr.Dataframe(label="Components", interactive=False)
        back_button = gr.Button("🔙 Back to Summary")

    state_failed_tasks = gr.State()
    state_current_collection = gr.State()

    def load_summary_on_start():
        summary, successes, failures = build_summary_from_analytics()
        collections_df = pd.DataFrame({"Collection": collections_list})
        return summary, make_pie_chart(successes, failures), collections_df

    def load_failed_tasks_on_select(evt: gr.SelectData):
        collection_name = collections_list[evt.index[0]]
        tasks = fetch_all_tasks(collection_name)
        failed_data = []
        for task in tasks:
            ts_obj = task.get("Failed Timestamps", {})
            if isinstance(ts_obj, dict) and ts_obj:
                first_key = next(iter(ts_obj))
                timestamp = ts_obj[first_key]
            else:
                timestamp = ""
            failed_data.append({
                "Task ID": str(task["_id"]),
                "Number of Failed Components": task.get("Number of Failed Components", 0),
                "Timestamp of Failure": timestamp
            })
        failed_df = pd.DataFrame(failed_data)
        return (
            failed_df.to_dict(), failed_df,
            collection_name
        )

    def on_task_select(evt: gr.SelectData, tasks_dict, collection_name):
        df = pd.DataFrame(tasks_dict)
        row_index = evt.index[0]
        task_id = df.at[row_index, "Task ID"]
        oneview, server, firmware, install, components = show_task_details(collection_name, task_id)
        return (
            oneview, server, firmware, install,
            gr.update(value=components, visible=not components.empty),
            gr.update(visible=False),
            gr.update(visible=True)
        )

    def back_to_summary():
        empty_df = pd.DataFrame()
        return [empty_df] * 4 + [gr.update(value=empty_df, visible=False), gr.update(visible=True), gr.update(visible=False)]

    failed_tasks_df.select(
        on_task_select,
        inputs=[state_failed_tasks, state_current_collection],
        outputs=[
            oneview_df, server_df, firmware_df, install_df,
            components_df,
            summary_section, detail_section
        ]
    )

    back_button.click(
        back_to_summary,
        inputs=[],
        outputs=[
            oneview_df, server_df, firmware_df, install_df,
            components_df,
            summary_section, detail_section
        ]
    )

    dashboard.load(
        load_summary_on_start,
        inputs=[],
        outputs=[summary_df, pie_plot, failed_collections_df]
    )

    failed_collections_df.select(
        load_failed_tasks_on_select,
        inputs=[],
        outputs=[state_failed_tasks, failed_tasks_df, state_current_collection]
    )


dashboard.launch(server_name="0.0.0.0", server_port=7860)
