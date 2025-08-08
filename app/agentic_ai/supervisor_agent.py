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

def get_secret_from_keyvault(secret_name, vault_url):
    """
    Reads a secret from Azure Key Vault using ManagedIdentityCredential.
    """
    default_secrets = {
        "KUSTOCLIENTID": "1932ad34-b426-4267-99e0-d1921c6200e6",
        "TENANTID": "72f988bf-86f1-41af-91ab-2d7cd011db47",
        "PROMETHEUSCLIENTID": "1932ad34-b426-4267-99e0-d1921c6200e6",
        "LOGANALYTICSCLIENTID": "1932ad34-b426-4267-99e0-d1921c6200e6",
        "AZUREOPENAIKEY": os.getenv("AZURE_AI_API_KEY")
    }
    try:
        credential = ManagedIdentityCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)
        secret = client.get_secret(secret_name)
        if not secret.value:
            raise ValueError(f"Secret '{secret_name}' is empty in Key Vault '{vault_url}'")
        return secret.value
    except Exception as e:
        return default_secrets.get(secret_name, None)
        #raise RuntimeError(f"Failed to retrieve secret '{secret_name}' from Key Vault: {e}")

# Import configuration
try:
    from config import *
except ImportError:
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
        credential = ManagedIdentityCredential(client_id=clientid)
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
    credential = ManagedIdentityCredential(client_id=clientid)
    token = credential.get_token("https://data.monitor.azure.com").token

    url = f"{query_endpoint}/api/v1/query?query={promql_query}"
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
            columns = [col if isinstance(col, str) else col.name for col in table.columns]
            rows = [dict(zip(columns, row)) for row in table.rows]
            return rows
        else:
            return [{"error": response.error.message}]
    except Exception as e:
        return [{"exception": str(e)}]

# === Line Graph Visualization Tools ===
@tool
def create_timeseries_line_chart(
    data: str,
    x_column: str = "timestamp",
    y_column: str = "value", 
    title: str = "Time Series Data",
    x_label: str = "Time",
    y_label: str = "Value"
):
    """
    Create an interactive line chart from time series data.
    
    Args:
        data: JSON string containing the time series data
        x_column: Name of the column containing time/date values
        y_column: Name of the column containing numeric values
        title: Chart title
        x_label: Label for x-axis
        y_label: Label for y-axis
    
    Returns:
        Plotly Figure object or error dict
    """
    try:
        # Parse the data
        if isinstance(data, str):
            data_list = json.loads(data)
        else:
            data_list = data
        
        # Convert to DataFrame
        df = pd.DataFrame(data_list)
        
        if df.empty:
            return {"error": "No data provided"}
        
        # Ensure we have the required columns
        if x_column not in df.columns or y_column not in df.columns:
            return {"error": f"Required columns {x_column} and {y_column} not found in data"}
        
        # Convert timestamp column to datetime if it's not already
        if df[x_column].dtype == 'object':
            df[x_column] = pd.to_datetime(df[x_column])
        
        # Sort by time
        df = df.sort_values(x_column)
        
        # Create the line chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df[x_column],
            y=df[y_column],
            mode='lines+markers',
            name=y_label,
            line=dict(width=2),
            marker=dict(size=4)
        ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            hovermode='x unified',
            template='plotly_white'
        )
        
        return {"type": "plotly_figure", "figure_data": fig.to_dict(), "description": f"Created time series chart: {title}"}
        
    except Exception as e:
        return {"error": f"Error creating chart: {str(e)}"}

@tool
def create_multi_metric_timeseries(
    data: str,
    x_column: str = "timestamp",
    metric_columns: str = "value1,value2", 
    title: str = "Multi-Metric Time Series",
    x_label: str = "Time"
):
    """
    Create an interactive line chart with multiple metrics on the same plot.
    
    Args:
        data: JSON string containing the time series data
        x_column: Name of the column containing time/date values
        metric_columns: Comma-separated list of column names to plot as metrics
        title: Chart title
        x_label: Label for x-axis
    
    Returns:
        Plotly Figure object or error dict
    """
    try:
        # Parse the data
        if isinstance(data, str):
            data_list = json.loads(data)
        else:
            data_list = data
        
        # Convert to DataFrame
        df = pd.DataFrame(data_list)
        
        if df.empty:
            return {"error": "No data provided"}
        
        # Parse metric columns
        metrics = [col.strip() for col in metric_columns.split(',')]
        
        # Ensure we have the required columns
        missing_cols = [col for col in [x_column] + metrics if col not in df.columns]
        if missing_cols:
            return {"error": f"Missing columns: {missing_cols}"}
        
        # Convert timestamp column to datetime if it's not already
        if df[x_column].dtype == 'object':
            df[x_column] = pd.to_datetime(df[x_column])
        
        # Sort by time
        df = df.sort_values(x_column)
        
        # Create the multi-line chart
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        for i, metric in enumerate(metrics):
            fig.add_trace(go.Scatter(
                x=df[x_column],
                y=df[metric],
                mode='lines+markers',
                name=metric,
                line=dict(width=2, color=colors[i % len(colors)]),
                marker=dict(size=4)
            ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title="Value",
            hovermode='x unified',
            template='plotly_white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return {"type": "plotly_figure", "figure_data": fig.to_dict(), "description": f"Created multi-metric chart: {title}"}
        
    except Exception as e:
        return {"error": f"Error creating multi-metric chart: {str(e)}"}

@tool
def create_incident_timeline(
    incident_data: str,
    metrics_data: str = "[]",
    incident_time_column: str = "CreatedDate",
    incident_title_column: str = "Title",
    incident_severity_column: str = "Severity",
    title: str = "Incident Timeline with Metrics"
):
    """
    Create a timeline chart showing incidents overlaid with system metrics.
    
    Args:
        incident_data: JSON string containing incident data
        metrics_data: JSON string containing metrics data (optional)
        incident_time_column: Column name for incident timestamps
        incident_title_column: Column name for incident titles
        incident_severity_column: Column name for incident severity
        title: Chart title
    
    Returns:
        Plotly Figure object or error dict
    """
    try:
        # Parse incident data
        if isinstance(incident_data, str):
            incidents = json.loads(incident_data)
        else:
            incidents = incident_data
        
        # Parse metrics data
        if isinstance(metrics_data, str):
            metrics = json.loads(metrics_data) if metrics_data != "[]" else []
        else:
            metrics = metrics_data or []
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            subplot_titles=('System Metrics', 'Incidents'),
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3]
        )
        
        # Add metrics if provided
        if metrics:
            df_metrics = pd.DataFrame(metrics)
            if 'timestamp' in df_metrics.columns and 'value' in df_metrics.columns:
                df_metrics['timestamp'] = pd.to_datetime(df_metrics['timestamp'])
                df_metrics = df_metrics.sort_values('timestamp')
                
                fig.add_trace(
                    go.Scatter(
                        x=df_metrics['timestamp'],
                        y=df_metrics['value'],
                        mode='lines',
                        name='Metric',
                        line=dict(color='blue', width=2)
                    ),
                    row=1, col=1
                )
        
        # Add incidents
        if incidents:
            df_incidents = pd.DataFrame(incidents)
            if incident_time_column in df_incidents.columns:
                df_incidents[incident_time_column] = pd.to_datetime(df_incidents[incident_time_column])
                
                # Color mapping for severity
                severity_colors = {
                    'Sev0': 'red', 'P0': 'red', '0': 'red',
                    'Sev1': 'orange', 'P1': 'orange', '1': 'orange',
                    'Sev2': 'yellow', 'P2': 'yellow', '2': 'yellow',
                    'Sev3': 'green', 'P3': 'green', '3': 'green',
                    'Sev4': 'blue', 'P4': 'blue', '4': 'blue'
                }
                
                for idx, incident in df_incidents.iterrows():
                    severity = str(incident.get(incident_severity_column, 'Unknown'))
                    color = severity_colors.get(severity, 'gray')
                    incident_title = incident.get(incident_title_column, f"Incident {idx}")
                    
                    # Add vertical line for incident
                    fig.add_vline(
                        x=incident[incident_time_column],
                        line_dash="dash",
                        line_color=color,
                        annotation_text=f"{severity}: {incident_title[:30]}...",
                        annotation_position="top"
                    )
                    
                    # Add scatter point on incident timeline
                    fig.add_trace(
                        go.Scatter(
                            x=[incident[incident_time_column]],
                            y=[0],  # Use 0 instead of 1
                            mode='markers',
                            name=f"Sev {severity}",
                            marker=dict(color=color, size=10, symbol='diamond'),
                            text=incident_title,
                            hovertemplate=f"<b>{incident_title}</b><br>Severity: {severity}<br>Time: %{{x}}<extra></extra>",
                            showlegend=False
                        ),
                        row=2, col=1
                    )
        
        # Update layout
        fig.update_layout(
            title=title,
            template='plotly_white',
            showlegend=True,
            height=600
        )
        
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Metric Value", row=1, col=1)
        fig.update_yaxes(title_text="Incidents", row=2, col=1, showticklabels=False)
        
        return {"type": "plotly_figure", "figure_data": fig.to_dict(), "description": f"Created incident timeline: {title}"}
        
    except Exception as e:
        return {"error": f"Error creating incident timeline: {str(e)}"}@tool  
def create_deployment_impact_chart(
    deployment_data: str,
    metrics_data: str,
    deployment_time_column: str = "DeploymentTime", 
    deployment_name_column: str = "DeploymentName",
    metric_time_column: str = "timestamp",
    metric_value_column: str = "value",
    title: str = "Deployment Impact Analysis"
):
    """
    Create a chart showing deployment events and their impact on system metrics.
    
    Args:
        deployment_data: JSON string containing deployment data
        metrics_data: JSON string containing metrics data
        deployment_time_column: Column name for deployment timestamps
        deployment_name_column: Column name for deployment names
        metric_time_column: Column name for metric timestamps
        metric_value_column: Column name for metric values
        title: Chart title
    
    Returns:
        Plotly Figure object or error dict
    """
    try:
        # Parse data
        if isinstance(deployment_data, str):
            deployments = json.loads(deployment_data)
        else:
            deployments = deployment_data
        
        if isinstance(metrics_data, str):
            metrics = json.loads(metrics_data)
        else:
            metrics = metrics_data
        
        if not deployments or not metrics:
            return {"error": "Both deployment and metrics data are required"}
        
        # Convert to DataFrames
        df_deployments = pd.DataFrame(deployments)
        df_metrics = pd.DataFrame(metrics)
        
        # Convert timestamps
        df_deployments[deployment_time_column] = pd.to_datetime(df_deployments[deployment_time_column])
        df_metrics[metric_time_column] = pd.to_datetime(df_metrics[metric_time_column])
        
        # Sort data
        df_deployments = df_deployments.sort_values(deployment_time_column)
        df_metrics = df_metrics.sort_values(metric_time_column)
        
        # Create figure
        fig = go.Figure()
        
        # Add metrics line
        fig.add_trace(go.Scatter(
            x=df_metrics[metric_time_column],
            y=df_metrics[metric_value_column],
            mode='lines+markers',
            name='System Metric',
            line=dict(color='blue', width=2),
            marker=dict(size=4)
        ))
        
        # Add deployment markers
        for idx, deployment in df_deployments.iterrows():
            deployment_time = deployment[deployment_time_column]
            deployment_name = deployment.get(deployment_name_column, f"Deployment {idx}")
            
            # Find metric value at deployment time (or closest)
            time_diff = abs(df_metrics[metric_time_column] - deployment_time)
            closest_metric_idx = time_diff.idxmin()
            metric_value = df_metrics.loc[closest_metric_idx, metric_value_column]
            
            # Add vertical line for deployment
            fig.add_vline(
                x=deployment_time,
                line_dash="dash", 
                line_color="red",
                annotation_text=f"Deploy: {deployment_name}",
                annotation_position="top"
            )
            
            # Add deployment marker
            fig.add_trace(go.Scatter(
                x=[deployment_time],
                y=[metric_value],
                mode='markers',
                name=f"Deploy: {deployment_name}",
                marker=dict(color='red', size=12, symbol='triangle-up'),
                text=deployment_name,
                hovertemplate=f"<b>{deployment_name}</b><br>Time: %{{x}}<br>Metric: %{{y}}<extra></extra>"
            ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="Metric Value", 
            template='plotly_white',
            hovermode='x unified'
        )
        
        return {"type": "plotly_figure", "figure_data": fig.to_dict(), "description": f"Created deployment impact chart: {title}"}
        
    except Exception as e:
        return {"error": f"Error creating deployment impact chart: {str(e)}"}

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
    tools=[prometheus_metrics_fetch_tool, promql_query_tool],
    prompt=(
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

# Define the Line Graph agent
line_graph_agent = create_react_agent(
    model=model_to_use,
    tools=[
        create_timeseries_line_chart,
        create_multi_metric_timeseries, 
        create_incident_timeline,
        create_deployment_impact_chart
    ],
    prompt=(
        "You are a Line Graph visualization agent that creates interactive time series charts and visualizations. "
        "You can create various types of charts to help users visualize their observability data over time.\n\n"
        "INSTRUCTIONS:\n"
        "- Use create_timeseries_line_chart() for basic time series line charts with a single metric\n"
        "- Use create_multi_metric_timeseries() for charts with multiple metrics on the same plot\n"
        "- Use create_incident_timeline() to create timeline charts showing incidents overlaid with system metrics\n"
        "- Use create_deployment_impact_chart() to visualize how deployments impact system metrics\n"
        "- Always ensure data is properly formatted as JSON strings before passing to tools\n"
        "- Focus on creating clear, interactive visualizations that help users understand their data\n"
        "- When receiving data from other agents, transform it appropriately for visualization\n"
        "- Provide helpful context about what the charts show and any patterns or anomalies visible\n"
        "- Return the chart JSON and a brief description of what the visualization shows"
    ),
    name="line_graph_agent",
)

# Define the supervisor agent
supervisor = create_supervisor(
    model=model_to_use,
    agents=[kusto_agent, prometheus_agent, log_analytics_agent, line_graph_agent],
    prompt=(
        "You are a supervisor managing the following agents:\n"
        "- a kusto agent. Use this agent to get relevant data from azure data explorer(kusto). You can use this agent to get incident details from IcMDataWarehouse table and deployment information from DeploymentEvents table. It can correlate incidents with deployments to identify deployment-related issues.\n"
        "- a prometheus agent. Use this agent to get relevant data from azure monitor workspace(prometheus). You can use this agent to get the metrics that are relevant to the icm, to run promql query for those selected metrics and to analyze the data the query returns\n"
        "- a log analytics agent. Use this agent to query Azure Monitor Logs using Kusto language. It can retrieve logs like errors, health checks, request traces, and other structured logs from ContainerLogV2 and related tables\n"
        "- a line graph agent. Use this agent to create interactive time series visualizations from data obtained by other agents. It can create basic line charts, multi-metric overlays, incident timelines, and deployment impact charts.\n"
        "Assign work to one agent at a time, do not call agents in parallel.\n"
        "Do not do any work yourself.\n"
        "When users ask for charts, graphs, or visualizations of time series data, use the line graph agent after obtaining the data from other agents.\n"
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
        agents=[kusto_agent, prometheus_agent, log_analytics_agent, line_graph_agent],
        prompt=(
            "You are a supervisor managing the following agents:\n"
            "- a kusto agent. Use this agent to get relevant data from azure data explorer(kusto). You can use this agent to get incident details from IcMDataWarehouse table and deployment information from DeploymentEvents table. It can correlate incidents with deployments to identify deployment-related issues.\n"
            "- a prometheus agent. Use this agent to get relevant data from azure monitor workspace(prometheus). You can use this agent to get the metrics that are relevant to the icm, to run promql query for those selected metrics and to analyze the data the query returns\n"
            "- a log analytics agent. Use this agent to query Azure Monitor Logs using Kusto language. It can retrieve logs like errors, health checks, request traces, and other structured logs from ContainerLogV2 and related tables\n"
            "- a line graph agent. Use this agent to create interactive time series visualizations from data obtained by other agents. It can create basic line charts, multi-metric overlays, incident timelines, and deployment impact charts.\n"
            "Assign work to one agent at a time, do not call agents in parallel.\n"
            "Do not do any work yourself.\n"
            "When users ask for charts, graphs, or visualizations of time series data, use the line graph agent after obtaining the data from other agents.\n"
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
    
    # Create dynamic line graph agent
    dynamic_line_graph_agent = create_react_agent(
        model=dynamic_model,
        tools=[
            create_timeseries_line_chart,
            create_multi_metric_timeseries, 
            create_incident_timeline,
            create_deployment_impact_chart
        ],
        prompt=(
            "You are a Line Graph visualization agent that creates interactive time series charts and visualizations. "
            "You can create various types of charts to help users visualize their observability data over time.\n\n"
            "INSTRUCTIONS:\n"
            "- Use create_timeseries_line_chart() for basic time series line charts with a single metric\n"
            "- Use create_multi_metric_timeseries() for charts with multiple metrics on the same plot\n"
            "- Use create_incident_timeline() to create timeline charts showing incidents overlaid with system metrics\n"
            "- Use create_deployment_impact_chart() to visualize how deployments impact system metrics\n"
            "- Always ensure data is properly formatted as JSON strings before passing to tools\n"
            "- Focus on creating clear, interactive visualizations that help users understand their data\n"
            "- When receiving data from other agents, transform it appropriately for visualization\n"
            "- Provide helpful context about what the charts show and any patterns or anomalies visible\n"
            "- Return the chart JSON and a brief description of what the visualization shows"
        ),
        name="line_graph_agent",
    )
    
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
        agents=[dynamic_kusto_agent, dynamic_prometheus_agent, dynamic_log_analytics_agent, dynamic_line_graph_agent],
        prompt=(
            "You are a supervisor managing the following agents:\n"
            "- a kusto agent. Use this agent to get relevant data from azure data explorer(kusto). You can use this agent to get incident details from IcMDataWarehouse table and deployment information from DeploymentEvents table. It can correlate incidents with deployments to identify deployment-related issues.\n"
            "- a prometheus agent. Use this agent to get relevant data from azure monitor workspace(prometheus). You can use this agent to get the metrics that are relevant to the icm, to run promql query for those selected metrics and to analyze the data the query returns\n"
            "- a log analytics agent. Use this agent to query Azure Monitor Logs using Kusto language. It can retrieve logs like errors, health checks, request traces, and other structured logs from ContainerLogV2 and related tables\n"
            "- a line graph agent. Use this agent to create interactive time series visualizations from data obtained by other agents. It can create basic line charts, multi-metric overlays, incident timelines, and deployment impact charts.\n"
            "Assign work to one agent at a time, do not call agents in parallel.\n"
            "Do not do any work yourself.\n"
            "When users ask for charts, graphs, or visualizations of time series data, use the line graph agent after obtaining the data from other agents.\n"
            "When users refer to 'that incident', 'the deployment', or 'the current issue', use the session context to understand what they're referring to."
            + context_prompt_addition
        ),
        add_handoff_back_messages=True,
        output_mode="last_message",
    ).compile()
