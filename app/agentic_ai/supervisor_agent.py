from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from azure.identity import ManagedIdentityCredential,DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.kusto.data import KustoConnectionStringBuilder, KustoClient
from pydantic import BaseModel, Field
from typing import Optional
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from datetime import timedelta
import requests
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta

# Utility function for JSON serialization
def convert_numpy_to_list(obj):
    """Convert numpy arrays to lists for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_numpy_to_list(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_list(item) for item in obj]
    elif hasattr(obj, 'tolist'):  # numpy array
        return obj.tolist()
    else:
        return obj

def format_prometheus_range_data_for_charts(prometheus_response):
    """
    Convert Prometheus range query response into format suitable for chart creation.
    
    Args:
        prometheus_response: Response from promql_range_query_tool
        
    Returns:
        List of dictionaries with timestamp and metric columns
    """
    try:
        if not prometheus_response.get('data', {}).get('result'):
            return []
        
        formatted_data = []
        
        for result in prometheus_response['data']['result']:
            metric_name = result.get('metric', {}).get('__name__', 'unknown_metric')
            
            # Add other labels to make metric names unique (like pod names)
            labels = result.get('metric', {})
            label_parts = []
            for key, value in labels.items():
                if key not in ['__name__']:  # Skip __name__ as we already used it
                    # Clean label values - remove special characters that might cause issues
                    clean_value = str(value).replace('-', '_').replace('.', '_').replace('/', '_')
                    label_parts.append(f"{key}_{clean_value}")
            
            if label_parts:
                metric_name = f"{metric_name}_{'_'.join(label_parts)}"
            
            # Process each timestamp/value pair
            for timestamp, value in result.get('values', []):
                try:
                    # Convert Unix timestamp to ISO format
                    dt = datetime.fromtimestamp(float(timestamp))
                    iso_timestamp = dt.isoformat() + 'Z'
                    
                    # Find or create row for this timestamp
                    existing_row = None
                    for row in formatted_data:
                        if row['timestamp'] == iso_timestamp:
                            existing_row = row
                            break
                    
                    if existing_row:
                        existing_row[metric_name] = float(value)
                    else:
                        new_row = {'timestamp': iso_timestamp, metric_name: float(value)}
                        formatted_data.append(new_row)
                except (ValueError, TypeError) as e:
                    print(f"Error processing timestamp/value pair: {timestamp}, {value} - {e}")
                    continue
        
        # Sort by timestamp
        formatted_data.sort(key=lambda x: x['timestamp'])
        return formatted_data
        
    except Exception as e:
        print(f"Error formatting Prometheus data: {e}")
        # Return empty list instead of None to avoid downstream issues
        return []

def get_secret_from_keyvault(secret_name, vault_url):
    """
    Reads a secret from Azure Key Vault using DefaultAzureCredential.
    DefaultAzureCredential will automatically try multiple authentication methods including managed identity.
    """
    try:
        # DefaultAzureCredential will automatically try managed identity, environment variables, etc.
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)
        secret = client.get_secret(secret_name)
        if not secret.value:
            raise ValueError(f"Secret '{secret_name}' is empty in Key Vault '{vault_url}'")
        return secret.value
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve secret '{secret_name}' from Key Vault: {e}")

# Fallback values if config.py is not found
VAULT_URL = "https://argusaskagenthackathonkv.vault.azure.net/"
KUSTO_CLUSTER_URI = "https://argushackathoncluster.westus.kusto.windows.net"
KUSTO_DATABASE = "ArgusAskJarvisDB"
KUSTO_INCIDENT_TABLE = "IcMDataWarehouse"
KUSTO_DEPLOYMENT_TABLE = "DeploymentEvents"
KUSTO_CLIENT_ID = get_secret_from_keyvault("KUSTOCLIENTID", VAULT_URL)
KUSTO_TENANT_ID = get_secret_from_keyvault("TENANTID", VAULT_URL)
PROMETHEUS_QUERY_ENDPOINT = "https://amw-argus-hack25-gqczh3d4b2d8d3en.westus.prometheus.monitor.azure.com"
PROMETHEUS_CLIENT_ID = get_secret_from_keyvault("PROMETHEUSCLIENTID", VAULT_URL)
LOG_ANALYTICS_WORKSPACE_ID = "f4576696-34ed-4caf-acd6-695a69f857d0"
LOG_ANALYTICS_CLIENT_ID = get_secret_from_keyvault("LOGANALYTICSCLIENTID", VAULT_URL)
OPEN_AI_API_KEY = get_secret_from_keyvault("AZUREOPENAIKEY", VAULT_URL)


# Initialize the model (default temperature)
model_to_use = AzureChatOpenAI(
    azure_deployment="gpt-4.1",
    # azure_deployment="gpt-35-turbo", # swap lighter model (NOTE: THis fails since theres no model deployment)
    api_key=OPEN_AI_API_KEY,  # Use value from key vault
    azure_endpoint="https://aifoundrydeployment.cognitiveservices.azure.com/",
    api_version="2024-12-01-preview",
    temperature=0.1,
)

def create_model_with_temperature(temperature=0.1):
    """Create an AzureChatOpenAI model with specified temperature."""
    return AzureChatOpenAI(
        azure_deployment="gpt-4.1",
        api_key=OPEN_AI_API_KEY,
        azure_endpoint="https://aifoundrydeployment.cognitiveservices.azure.com/",
        api_version="2024-12-01-preview",
        temperature=temperature,
    )

# === Default Configuration ===
# Configuration is loaded from config.py
DEFAULT_CONFIG = {
    "kusto": {
        "cluster_uri": KUSTO_CLUSTER_URI,
        "database": KUSTO_DATABASE,
        "incident_table": KUSTO_INCIDENT_TABLE,
        "deployment_table": KUSTO_DEPLOYMENT_TABLE,
        "client_id": KUSTO_CLIENT_ID,
        "tenant_id": KUSTO_TENANT_ID
    },
    "prometheus": {
        "query_endpoint": PROMETHEUS_QUERY_ENDPOINT,
        "client_id": PROMETHEUS_CLIENT_ID
    },
    "log_analytics": {
        "workspace_id": LOG_ANALYTICS_WORKSPACE_ID,
        "client_id": LOG_ANALYTICS_CLIENT_ID
    }
}

# === Kusto Tools ===
def kusto_schema_fetcher(cluster_uri, database, table, client_id, Tenantid):
    kcsb = KustoConnectionStringBuilder.with_aad_managed_service_identity_authentication(cluster_uri, client_id)
    kcsb.authority_id = Tenantid
    client = KustoClient(kcsb)
    query = f"{table}|getschema"
    response = client.execute(database, query)
    return [row.to_dict() for row in response.primary_results[0]]

def query_kusto_table(cluster_uri, database, table, client_id, Tenantid, query):
    kcsb = KustoConnectionStringBuilder.with_aad_managed_service_identity_authentication(cluster_uri, client_id)
    kcsb.authority_id = Tenantid
    client = KustoClient(kcsb)
    response = client.execute(database, query)
    return [row.to_dict() for row in response.primary_results[0]]

class kustoconfig(BaseModel):
    cluster_uri: object = Field(default=DEFAULT_CONFIG["kusto"]["cluster_uri"], description="uri of the cluster")
    database: object = Field(default=DEFAULT_CONFIG["kusto"]["database"], description="kusto db")
    incident_table: object = Field(default=DEFAULT_CONFIG["kusto"]["incident_table"], description="kusto incidents table")
    deployment_table: object = Field(default=DEFAULT_CONFIG["kusto"]["deployment_table"], description="kusto deployments table")
    client_id: object = Field(default=DEFAULT_CONFIG["kusto"]["client_id"], description="msi client_id")
    Tenantid: object = Field(default=DEFAULT_CONFIG["kusto"]["tenant_id"], description="Tenant id")
    query: object = Field(default="", description="Kusto Query generated by llm")

@tool
def kusto_schema_tool(
    table: str = "IcMDataWarehouse",
    cluster_uri: str = DEFAULT_CONFIG["kusto"]["cluster_uri"],
    database: str = DEFAULT_CONFIG["kusto"]["database"], 
    client_id: str = DEFAULT_CONFIG["kusto"]["client_id"],
    tenant_id: str = DEFAULT_CONFIG["kusto"]["tenant_id"]
) -> list:
    """
    Fetch schema from kusto table. Defaults to IcMDataWarehouse (incidents).
    Use table='DeploymentEvents' for deployment data.
    """
    return kusto_schema_fetcher(cluster_uri, database, table, client_id, tenant_id)

@tool
def kusto_query_tool(
    query: str,
    table: str = "IcMDataWarehouse",
    cluster_uri: str = DEFAULT_CONFIG["kusto"]["cluster_uri"],
    database: str = DEFAULT_CONFIG["kusto"]["database"], 
    client_id: str = DEFAULT_CONFIG["kusto"]["client_id"],
    tenant_id: str = DEFAULT_CONFIG["kusto"]["tenant_id"]
) -> list:
    """
    Execute a Kusto query on specified table. Defaults to IcMDataWarehouse (incidents).
    Use table='DeploymentEvents' for deployment queries.
    The query should NOT include the table name - just the query operations.
    """
    # Ensure the query starts with the table name
    if not query.strip().startswith(table):
        query = f"{table} | {query}"
    return query_kusto_table(cluster_uri, database, "", client_id, tenant_id, query)

@tool
def kusto_incident_schema_tool(
    cluster_uri: str = DEFAULT_CONFIG["kusto"]["cluster_uri"],
    database: str = DEFAULT_CONFIG["kusto"]["database"], 
    client_id: str = DEFAULT_CONFIG["kusto"]["client_id"],
    tenant_id: str = DEFAULT_CONFIG["kusto"]["tenant_id"]
) -> list:
    """
    Fetch schema from the IcMDataWarehouse incidents table using default configuration.
    """
    return kusto_schema_fetcher(cluster_uri, database, DEFAULT_CONFIG["kusto"]["incident_table"], client_id, tenant_id)

@tool
def kusto_deployment_schema_tool(
    cluster_uri: str = DEFAULT_CONFIG["kusto"]["cluster_uri"],
    database: str = DEFAULT_CONFIG["kusto"]["database"], 
    client_id: str = DEFAULT_CONFIG["kusto"]["client_id"],
    tenant_id: str = DEFAULT_CONFIG["kusto"]["tenant_id"]
) -> list:
    """
    Fetch schema from the DeploymentEvents table using default configuration.
    """
    return kusto_schema_fetcher(cluster_uri, database, DEFAULT_CONFIG["kusto"]["deployment_table"], client_id, tenant_id)

@tool
def kusto_incident_query_tool(
    query: str,
    cluster_uri: str = DEFAULT_CONFIG["kusto"]["cluster_uri"],
    database: str = DEFAULT_CONFIG["kusto"]["database"], 
    client_id: str = DEFAULT_CONFIG["kusto"]["client_id"],
    tenant_id: str = DEFAULT_CONFIG["kusto"]["tenant_id"]
) -> list:
    """
    Execute a Kusto query on the IcMDataWarehouse incidents table.
    Only the query parameter is required. Other parameters use defaults unless overridden.
    """
    return query_kusto_table(cluster_uri, database, DEFAULT_CONFIG["kusto"]["incident_table"], client_id, tenant_id, query)

@tool
def kusto_deployment_query_tool(
    query: str,
    cluster_uri: str = DEFAULT_CONFIG["kusto"]["cluster_uri"],
    database: str = DEFAULT_CONFIG["kusto"]["database"], 
    client_id: str = DEFAULT_CONFIG["kusto"]["client_id"],
    tenant_id: str = DEFAULT_CONFIG["kusto"]["tenant_id"]
) -> list:
    """
    Execute a Kusto query on the DeploymentEvents table.
    Only the query parameter is required. Other parameters use defaults unless overridden.
    """
    return query_kusto_table(cluster_uri, database, DEFAULT_CONFIG["kusto"]["deployment_table"], client_id, tenant_id, query)

# === Prometheus Tools ===
def get_prometheus_metrics(query_endpoint, clientid):
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://data.monitor.azure.com").token
        headers = {
            "Authorization": f"Bearer {token}"
        }
        response = requests.get(f"{query_endpoint}/api/v1/label/__name__/values", headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'success':
            return data.get('data', [])
        else:
            print(f"Error from Prometheus API: {data}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def run_promql_query(query_endpoint, promql_query, clientid):
    """
    Runs a PromQL query in Azure Monitor using managed identity authentication.
    """
    credential = DefaultAzureCredential()
    token = credential.get_token("https://data.monitor.azure.com").token

    url = f"{query_endpoint}/api/v1/query?query={promql_query}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def run_promql_range_query(query_endpoint, promql_query, start_time, end_time, step, clientid):
    """
    Runs a PromQL range query in Azure Monitor using managed identity authentication.
    Returns time series data with timestamps.
    
    Args:
        query_endpoint: The Prometheus query endpoint
        promql_query: The PromQL query string
        start_time: Start time (ISO format or Unix timestamp)
        end_time: End time (ISO format or Unix timestamp) 
        step: Query resolution step (e.g., '1m', '5m', '1h')
        clientid: Client ID for authentication
    """
    credential = DefaultAzureCredential()
    token = credential.get_token("https://data.monitor.azure.com").token

    # Build the range query URL
    params = {
        'query': promql_query,
        'start': start_time,
        'end': end_time,
        'step': step
    }
    
    # Convert params to query string
    query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
    url = f"{query_endpoint}/api/v1/query_range?{query_string}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

class promconfig(BaseModel):
    query_endpoint: object = Field(default=DEFAULT_CONFIG["prometheus"]["query_endpoint"], description="The Azure Monitor workspace query endpoint")
    promql_query: object = Field(default="", description="prom ql query generated by llm")
    clientid: object = Field(default=DEFAULT_CONFIG["prometheus"]["client_id"], description="msi client_id")

@tool
def prometheus_metrics_fetch_tool(
    query_endpoint: str = DEFAULT_CONFIG["prometheus"]["query_endpoint"],
    client_id: str = DEFAULT_CONFIG["prometheus"]["client_id"]
) -> list:
    """
    Fetch all prometheus metrics from azure monitor workspace using default configuration.
    Parameters use defaults unless overridden.
    """
    return get_prometheus_metrics(query_endpoint, client_id)

@tool
def promql_query_tool(
    promql_query: str,
    query_endpoint: str = DEFAULT_CONFIG["prometheus"]["query_endpoint"],
    client_id: str = DEFAULT_CONFIG["prometheus"]["client_id"]
) -> dict:
    """
    Execute PromQL query against Azure Monitor workspace using default configuration.
    Only the promql_query parameter is required. Other parameters use defaults unless overridden.
    """
    return run_promql_query(query_endpoint, promql_query, client_id)

@tool
def promql_range_query_tool(
    promql_query: str,
    start_time: str = "2025-08-08T09:00:00Z",
    end_time: str = "2025-08-08T10:00:00Z", 
    step: str = "5m",
    query_endpoint: str = DEFAULT_CONFIG["prometheus"]["query_endpoint"],
    client_id: str = DEFAULT_CONFIG["prometheus"]["client_id"]
) -> dict:
    """
    Execute PromQL range query to get time series data with timestamps.
    This is essential for creating charts as it returns data over time.
    
    Args:
        promql_query: The PromQL query (required)
        start_time: Start time in ISO format (default: 1 hour ago)
        end_time: End time in ISO format (default: now) 
        step: Query resolution (default: 5m intervals)
        query_endpoint: Prometheus endpoint (uses default)
        client_id: Client ID (uses default)
    
    Returns:
        Time series data with timestamps suitable for chart creation
    """
    return run_promql_range_query(query_endpoint, promql_query, start_time, end_time, step, client_id)

# @tool - DISABLED
# def format_prometheus_data_for_charts(prometheus_response: str) -> str:
#     """Convert Prometheus range query response into format suitable for chart creation."""
#     pass

# @tool - DISABLED  
# def debug_prometheus_response(prometheus_response: str) -> str:
#     """Debug tool to analyze Prometheus response structure."""
#     pass

# === Log Analytics Tools ===
@tool
def query_log_analytics_tool(
    query: str,
    workspace_id: str = DEFAULT_CONFIG["log_analytics"]["workspace_id"],
    client_id: str = DEFAULT_CONFIG["log_analytics"]["client_id"]
) -> list:
    """
    Tool to run Kusto queries on Azure Log Analytics using default configuration.
    Only the query parameter is required. Other parameters use defaults unless overridden.
    """
    if not query:
        raise ValueError("Query is required. The agent must generate one based on user intent.")

    credential = DefaultAzureCredential()
    client = LogsQueryClient(credential)

    try:
        response = client.query_workspace(
            workspace_id=workspace_id,
            query=query,
            timespan=timedelta(hours=1)
        )
        
        if response.status == LogsQueryStatus.SUCCESS:
            table = response.tables[0]
            columns = [col if isinstance(col, str) else col.name for col in table.columns]
            rows = [dict(zip(columns, row)) for row in table.rows]
            return rows
        else:
            return [{"error": response.error.message}]
    except Exception as e:
        return [{"exception": str(e)}]

# === Line Graph Visualization Tools === DISABLED
# All chart creation tools have been disabled to resolve issues

# @tool
# def create_timeseries_line_chart(
#     data: str,
#     x_column: str = "timestamp",
#     y_column: str = "value", 
#     title: str = "Time Series Data",
#     x_label: str = "Time",
#     y_label: str = "Value"
# ):
#     """Create an interactive line chart from time series data."""
#     pass

# @tool
# def create_multi_metric_timeseries(
#     data: str,
#     x_column: str = "timestamp",
#     metric_columns: str = "value1,value2", 
#     title: str = "Multi-Metric Time Series",
#     x_label: str = "Time"
# ):
#     """Create an interactive line chart with multiple metrics."""
#     pass

# @tool
# def create_incident_timeline(
#     incident_data: str,
#     metrics_data: str = "[]",
#     incident_time_column: str = "CreatedDate",
#     incident_title_column: str = "Title",
#     incident_severity_column: str = "Severity",
#     title: str = "Incident Timeline with Metrics"
# ):
#     """Create a timeline chart showing incidents overlaid with system metrics."""
#     pass

# @tool  
# def create_deployment_impact_chart(
#     deployment_data: str,
#     metrics_data: str,
#     deployment_time_column: str = "DeploymentTime", 
#     deployment_name_column: str = "DeploymentName",
#     metric_time_column: str = "timestamp",
#     metric_value_column: str = "value",
#     title: str = "Deployment Impact Analysis"
# ):
#     """Create a chart showing deployment events and their impact on system metrics."""
#     pass
# Define the Kusto agent
kusto_agent = create_react_agent(
    model=model_to_use,
    tools=[
        kusto_schema_tool, 
        kusto_query_tool,
        kusto_incident_schema_tool, 
        kusto_incident_query_tool,
        kusto_deployment_schema_tool,
        kusto_deployment_query_tool
    ],
    prompt=(
        "You are an Azure Data Explorer (Kusto) agent who can read Azure Data Explorer tables. "
        "You have access to TWO tables with default configuration:\n"
        "1. IcMDataWarehouse - Contains incident management data\n"
        "2. DeploymentEvents - Contains deployment and release information\n\n"
        "INSTRUCTIONS:\n"
        "- Use kusto_incident_schema_tool() to get the schema of the incidents table\n"
        "- Use kusto_deployment_schema_tool() to get the schema of the deployments table\n"
        "- Generate Kusto queries based on user requests after getting the appropriate schema\n"
        "- Use kusto_incident_query_tool(query='your_query_here') for incident-related queries\n"
        "- Use kusto_deployment_query_tool(query='your_query_here') for deployment-related queries\n"
        "- You can also use the generic kusto_schema_tool(table='TableName') and kusto_query_tool(query='...', table='TableName')\n"
        "- You can correlate data between both tables when needed\n"
        "- Focus on helping users analyze incident data, deployment patterns, and their relationships\n"
        "- Respond ONLY with the results of your work, do NOT include ANY other text."
    ),
    name="kusto_agent",
)

# Define the Prometheus agent

# Define the Prometheus agent
prometheus_agent = create_react_agent(
    model=model_to_use,
    tools=[prometheus_metrics_fetch_tool, promql_query_tool, promql_range_query_tool],
    prompt=(
        "You are a Prometheus agent who can read Azure Monitor workspace (Prometheus environment). "
        "You have default configuration values pre-configured, so you can work immediately without asking for connection details.\n\n"
        "INSTRUCTIONS:\n"
        "- Use prometheus_metrics_fetch_tool() to get available metrics from the default workspace\n"
        "- Use promql_query_tool(promql_query='your_query_here') for instant snapshots of current values\n"
        "- Use promql_range_query_tool(promql_query='your_query_here', start_time='...', end_time='...', step='5m') for time series data\n"
        "- The default endpoint and authentication are already configured\n"
        "- Focus on helping users analyze metrics and performance data\n"
        "- Respond ONLY with the results of your work, do NOT include ANY other text."
    ),
    name="prometheus_agent",
)

# Define the Log Analytics agent
log_analytics_agent = create_react_agent(
    model=model_to_use,
    tools=[query_log_analytics_tool],
    prompt=(
        "You are a Log Analytics agent that queries Azure Monitor logs using Kusto query language. "
        "You have default configuration values pre-configured, so you can work immediately without asking for connection details.\n\n"
        "INSTRUCTIONS:\n"
        "- Generate valid Kusto queries based on user requests\n"
        "- Query logs from ContainerLogV2 and other Azure Monitor log tables\n"
        "- Execute queries using query_log_analytics_tool(query='your_query_here')\n"
        "- The default workspace ID and authentication are already configured\n"
        "- Focus on retrieving logs, traces, and telemetry data for troubleshooting\n"
        "- Respond ONLY with the results of your work, do NOT include ANY other text."
    ),
    name="log_analytics_agent",
)

# Define the Line Graph agent - DISABLED
# line_graph_agent = create_react_agent(
#     model=model_to_use,
#     tools=[
#         create_timeseries_line_chart,
#         create_multi_metric_timeseries, 
#         create_incident_timeline,
#         create_deployment_impact_chart
#     ],
#     prompt=(
#         "You are a Line Graph visualization agent. Your ONLY job is to create interactive charts using the provided tools.\n\n"
#         "ABSOLUTE REQUIREMENTS:\n"
#         "1. You MUST ALWAYS call a chart creation tool - NEVER just describe what a chart would look like\n"
#         "2. You MUST use one of these tools for EVERY request: create_timeseries_line_chart, create_multi_metric_timeseries, create_incident_timeline, or create_deployment_impact_chart\n"
#         "3. You MUST return the complete JSON response from the tool in your answer\n"
#         "4. You are FORBIDDEN from providing text descriptions without calling a tool first\n\n"
#         "TOOL SELECTION:\n"
#         "- create_timeseries_line_chart() for single metric time series\n"
#         "- create_multi_metric_timeseries() for multiple metrics (like podA, podB, podC memory usage)\n"
#         "- create_incident_timeline() for incident overlays\n"
#         "- create_deployment_impact_chart() for deployment analysis\n\n"
#         "WORKFLOW:\n"
#         "1. Receive data from supervisor\n"
#         "2. Immediately call appropriate chart tool\n"
#         "3. Return the complete JSON response from the tool\n"
#         "4. Add brief description after the JSON\n\n"
#         "CRITICAL: If you receive a request but no data, you MUST still call a chart tool with sample data or ask the supervisor to provide data. You are NEVER allowed to just describe a chart without creating one.\n\n"
#         "Your response format MUST be:\n"
#         "[COMPLETE JSON FROM TOOL]\n\n[Brief description]"
#     ),
#     name="line_graph_agent",
# )

# Define the supervisor agent
supervisor = create_supervisor(
    model=model_to_use,
    agents=[kusto_agent, prometheus_agent, log_analytics_agent],
    prompt=(
        "You are a supervisor managing the following agents:\n"
        "- a kusto agent. Use this agent to get relevant data from azure data explorer(kusto). You can use this agent to get incident details from IcMDataWarehouse table and deployment information from DeploymentEvents table. It can correlate incidents with deployments to identify deployment-related issues.\n"
        "- a prometheus agent. Use this agent to get relevant data from azure monitor workspace(prometheus). You can use this agent to get the metrics that are relevant to the icm, to run promql query for those selected metrics and to analyze the data the query returns.\n"
        "- a log analytics agent. Use this agent to query Azure Monitor Logs using Kusto language. It can retrieve logs like errors, health checks, request traces, and other structured logs from ContainerLogV2 and related tables\n"
        "Assign work to one agent at a time, do not call agents in parallel.\n"
        "Do not do any work yourself.\n"
        "When users refer to 'that incident', 'the deployment', or 'the current issue', use any provided context to understand what they're referring to.\n"
        "If a user asks follow-up questions without context, ask for clarification about which specific incident, deployment, or issue they mean."
    ),
    add_handoff_back_messages=True,
    output_mode="last_message",
).compile()

def create_context_aware_supervisor(session_context=None):
    """Create a supervisor that's aware of session context."""
    
    context_prompt_addition = ""
    if session_context:
        context_parts = []
        if session_context.get('last_incident_id'):
            context_parts.append(f"Current incident context: {session_context['last_incident_id']}")
        if session_context.get('last_deployment'):
            context_parts.append(f"Current deployment context: {session_context['last_deployment']}")
        if session_context.get('active_investigation'):
            context_parts.append(f"Active investigation type: {session_context['active_investigation']}")
        
        if context_parts:
            context_prompt_addition = f"\n\nCURRENT SESSION CONTEXT:\n{chr(10).join(context_parts)}\nPlease consider this context when routing requests and providing responses."
    
    return create_supervisor(
        model=model_to_use,
        agents=[kusto_agent, prometheus_agent, log_analytics_agent],
        prompt=(
            "You are a supervisor managing the following agents:\n"
            "- a kusto agent. Use this agent to get relevant data from azure data explorer(kusto). You can use this agent to get incident details from IcMDataWarehouse table and deployment information from DeploymentEvents table. It can correlate incidents with deployments to identify deployment-related issues.\n"
            "- a prometheus agent. Use this agent to get relevant data from azure monitor workspace(prometheus). You can use this agent to get the metrics that are relevant to the icm, to run promql query for those selected metrics and to analyze the data the query returns\n"
            "- a log analytics agent. Use this agent to query Azure Monitor Logs using Kusto language. It can retrieve logs like errors, health checks, request traces, and other structured logs from ContainerLogV2 and related tables\n"
            "Assign work to one agent at a time, do not call agents in parallel.\n"
            "Do not do any work yourself.\n"
            "When users refer to 'that incident', 'the deployment', or 'the current issue', use the session context to understand what they're referring to."
            + context_prompt_addition
        ),
        add_handoff_back_messages=True,
        output_mode="last_message",
    ).compile()

def create_dynamic_supervisor(temperature=0.1, session_context=None, custom_prompts=None):
    """Create a supervisor with dynamic temperature, optional session context, and custom prompts."""
    
    # Create model with specified temperature
    dynamic_model = create_model_with_temperature(temperature)
    
    # Default prompts
    default_prompts = {
        "kusto": (
            "You are an Azure Data Explorer (Kusto) agent who can read Azure Data Explorer tables. "
            "You have access to TWO tables with default configuration:\n"
            "1. IcMDataWarehouse - Contains incident management data\n"
            "2. DeploymentEvents - Contains deployment and release information\n\n"
            "INSTRUCTIONS:\n"
            "- Use kusto_incident_schema_tool() to get the schema of the incidents table\n"
            "- Use kusto_deployment_schema_tool() to get the schema of the deployments table\n"
            "- Generate Kusto queries based on user requests after getting the appropriate schema\n"
            "- Use kusto_incident_query_tool(query='your_query_here') for incident-related queries\n"
            "- Use kusto_deployment_query_tool(query='your_query_here') for deployment-related queries\n"
            "- You can also use the generic kusto_schema_tool(table='TableName') and kusto_query_tool(query='...', table='TableName')\n"
            "- You can correlate data between both tables when needed\n"
            "- Focus on helping users analyze incident data, deployment patterns, and their relationships\n"
            "- Respond ONLY with the results of your work, do NOT include ANY other text."
        ),
        "prometheus": (
            "You are a Prometheus agent who can read Azure Monitor workspace (Prometheus environment). "
            "You have default configuration values pre-configured, so you can work immediately without asking for connection details.\n\n"
            "INSTRUCTIONS:\n"
            "- Use prometheus_metrics_fetch_tool() to get available metrics from the default workspace\n"
            "- Create PromQL queries based on user requests\n"
            "- Execute PromQL queries using promql_query_tool(promql_query='your_query_here')\n"
            "- The default endpoint and authentication are already configured\n"
            "- Focus on helping users analyze metrics and performance data\n"
            "- Respond ONLY with the results of your work, do NOT include ANY other text."
        ),
        "log_analytics": (
            "You are a Log Analytics agent that queries Azure Monitor logs using Kusto query language. "
            "You have default configuration values pre-configured, so you can work immediately without asking for connection details.\n\n"
            "INSTRUCTIONS:\n"
            "- Generate valid Kusto queries based on user requests\n"
            "- Query logs from ContainerLogV2 and other Azure Monitor log tables\n"
            "- Execute queries using query_log_analytics_tool(query='your_query_here')\n"
            "- The default workspace ID and authentication are already configured\n"
            "- Focus on retrieving logs, traces, and telemetry data for troubleshooting\n"
            "- Respond ONLY with the results of your work, do NOT include ANY other text."
        )
    }
    
    # Use custom prompts if provided, otherwise use defaults
    prompts = custom_prompts if custom_prompts else default_prompts
    
    # Create agents with the dynamic model and custom prompts
    dynamic_kusto_agent = create_react_agent(
        model=dynamic_model,
        tools=[
            kusto_schema_tool, 
            kusto_query_tool,
            kusto_incident_schema_tool, 
            kusto_incident_query_tool,
            kusto_deployment_schema_tool,
            kusto_deployment_query_tool
        ],
        prompt=prompts["kusto"],
        name="kusto_agent",
    )
    
    dynamic_prometheus_agent = create_react_agent(
        model=dynamic_model,
        tools=[prometheus_metrics_fetch_tool, promql_query_tool],
        prompt=prompts["prometheus"],
        name="prometheus_agent",
    )
    
    dynamic_log_analytics_agent = create_react_agent(
        model=dynamic_model,
        tools=[query_log_analytics_tool],
        prompt=prompts["log_analytics"],
        name="log_analytics_agent",
    )
    
    # Create dynamic line graph agent - DISABLED
    # dynamic_line_graph_agent = create_react_agent(
    #     model=dynamic_model,
    #     tools=[
    #         create_timeseries_line_chart,
    #         create_multi_metric_timeseries, 
    #         create_incident_timeline,
    #         create_deployment_impact_chart
    #     ],
    #     prompt=(
    #         "You are a Line Graph visualization agent that creates interactive time series charts and visualizations. "
    #         "You can create various types of charts to help users visualize their observability data over time.\n\n"
    #         "INSTRUCTIONS:\n"
    #         "- Use create_timeseries_line_chart() for basic time series line charts with a single metric\n"
    #         "- Use create_multi_metric_timeseries() for charts with multiple metrics on the same plot\n"
    #         "- Use create_incident_timeline() to create timeline charts showing incidents overlaid with system metrics\n"
    #         "- Use create_deployment_impact_chart() to visualize how deployments impact system metrics\n"
    #         "- Always ensure data is properly formatted as JSON strings before passing to tools\n"
    #         "- When a chart tool returns JSON data, INCLUDE THE ENTIRE JSON RESPONSE in your final answer\n"
    #         "- Focus on creating clear, interactive visualizations that help users understand their data\n"
    #         "- When receiving data from other agents, transform it appropriately for visualization\n"
    #         "- Your response should include both the chart JSON and a brief description\n"
    #         "- IMPORTANT: Always include the complete JSON response from the chart tools in your answer so Streamlit can render the charts\n"
    #         "- Provide helpful context about what the charts show and any patterns or anomalies visible"
    #     ),
    #     name="line_graph_agent",
    # )
    
    # Build context-aware prompt
    context_prompt_addition = ""
    if session_context:
        context_parts = []
        if session_context.get('last_incident_id'):
            context_parts.append(f"Current incident context: {session_context['last_incident_id']}")
        if session_context.get('last_deployment'):
            context_parts.append(f"Current deployment context: {session_context['last_deployment']}")
        if session_context.get('active_investigation'):
            context_parts.append(f"Active investigation type: {session_context['active_investigation']}")
        
        if context_parts:
            context_prompt_addition = f"\n\nCURRENT SESSION CONTEXT:\n{chr(10).join(context_parts)}\nPlease consider this context when routing requests and providing responses."
    
    # Create supervisor with dynamic agents
    return create_supervisor(
        model=dynamic_model,
        agents=[dynamic_kusto_agent, dynamic_prometheus_agent, dynamic_log_analytics_agent],
        prompt=(
            "You are a supervisor managing the following agents:\n"
            "- a kusto agent. Use this agent to get relevant data from azure data explorer(kusto). You can use this agent to get incident details from IcMDataWarehouse table and deployment information from DeploymentEvents table. It can correlate incidents with deployments to identify deployment-related issues.\n"
            "- a prometheus agent. Use this agent to get relevant data from azure monitor workspace(prometheus). You can use this agent to get the metrics that are relevant to the icm, to run promql query for those selected metrics and to analyze the data the query returns\n"
            "- a log analytics agent. Use this agent to query Azure Monitor Logs using Kusto language. It can retrieve logs like errors, health checks, request traces, and other structured logs from ContainerLogV2 and related tables\n"
            "Assign work to one agent at a time, do not call agents in parallel.\n"
            "Do not do any work yourself.\n"
            "When users refer to 'that incident', 'the deployment', or 'the current issue', use the session context to understand what they're referring to."
            + context_prompt_addition
        ),
        add_handoff_back_messages=True,
        output_mode="last_message",
    ).compile()
