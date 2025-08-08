from langchain.tools import tool
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from azure.identity import ManagedIdentityCredential
from datetime import timedelta
from langgraph.prebuilt import create_react_agent

class LogAnalyticsConfig:
    def __init__(self, workspace_id, query, client_id):
        self.workspace_id = workspace_id
        self.query = query
        self.client_id = client_id

@tool(args_schema=LogAnalyticsConfig)
def query_log_analytics_tool(workspace_id: str, query: str, client_id: str) -> list:
    """
    Tool to run Kusto queries on Azure Log Analytics.
    """
    credential = ManagedIdentityCredential(client_id=client_id)
    client = LogsQueryClient(credential)

    try:
        response = client.query_workspace(
            workspace_id=workspace_id,
            query=query,
            timespan=timedelta(hours=1)
        )

        if response.status == LogsQueryStatus.SUCCESS:
            table = response.tables[0]
            columns = [col.name for col in table.columns]
            rows = [dict(zip(columns, row)) for row in table.rows]
            return rows
        else:
            return [{"error": response.error.message}]
    except Exception as e:
        return [{"exception": str(e)}]

log_analytics_agent = create_react_agent(
    model=None,  # Replace with your model instance
    tools=[query_log_analytics_tool],
    prompt=(
        "You are a Log Analytics agent that queries Azure Monitor logs using Kusto query language.\n\n"
        "Use the provided tool to:\n"
        "- Query logs from a specific Log Analytics workspace\n"
        "- Return logs or telemetry based on user prompts\n"
        "- Do NOT interpret results, only return them\n"
        "- Do not attempt to do work yourself — rely entirely on the tool."
    ),
    name="log_analytics_agent",
)
