# HeyJarvis Azure Observability Chatbot - Configuration Guide

## Quick Setup

The chatbot now includes embedded configuration so users don't need to provide connection details every time they ask a question.

### Configuration Files

1. **`config.py`** - Main configuration file with your Azure resource details
2. **`supervisor_agent.py`** - Contains the agent logic with embedded defaults

### Setting Up Your Environment

**Step 1: Create Configuration File**
```bash
# Copy the template to create your config file
cp config_template.py config.py
```

**Step 2: Edit Configuration**
Edit `config.py` and replace the placeholder values with your actual Azure resources:

```python
# Azure Data Explorer (Kusto) Configuration
KUSTO_CLUSTER_URI = "https://your-actual-cluster.kusto.windows.net"
KUSTO_DATABASE = "YourActualDatabase"
KUSTO_TABLE = "YourActualICMTable"
KUSTO_CLIENT_ID = "your-actual-msi-client-id"
KUSTO_TENANT_ID = "your-actual-tenant-id"

# Azure Monitor Workspace (Prometheus) Configuration  
PROMETHEUS_QUERY_ENDPOINT = "https://your-actual-prometheus-workspace.monitor.azure.com"
PROMETHEUS_CLIENT_ID = "your-actual-msi-client-id"

# Azure Log Analytics Configuration
LOG_ANALYTICS_WORKSPACE_ID = "your-actual-workspace-id"
LOG_ANALYTICS_CLIENT_ID = "your-actual-msi-client-id"

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = "your-actual-api-key"
AZURE_OPENAI_ENDPOINT = "https://your-actual-endpoint.cognitiveservices.azure.com/"
AZURE_OPENAI_DEPLOYMENT = "your-deployment-name"
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"
```

**Important Security Note**: The `config.py` file is automatically ignored by git to prevent accidentally committing API keys and secrets.

### How It Works

- **Default Configuration**: When users ask questions, the agents automatically use your configured Azure resources
- **No Parameter Requests**: Users no longer need to provide cluster URIs, database names, workspace IDs, etc.
- **Intelligent Routing**: The supervisor automatically routes requests to the appropriate agent:
  - **Kusto Agent**: For incident data and Azure Data Explorer queries
  - **Prometheus Agent**: For metrics and performance monitoring
  - **Log Analytics Agent**: For logs, traces, and telemetry data
- **Immediate Response**: The chatbot can start working right away with questions like:
  - "Show me recent incidents"
  - "What metrics are available?"
  - "Get the latest container logs"
  - "Help me analyze incident trends"

### Authentication Requirements

Ensure your Azure Managed Service Identity (MSI) has the following permissions:

#### For Kusto (Azure Data Explorer):
- **Role**: Database User or Database Admin
- **Scope**: Your target database
- **Permissions**: Query tables, read schema

#### For Prometheus (Azure Monitor):
- **Role**: Monitoring Reader or higher
- **Scope**: Your Azure Monitor workspace
- **Permissions**: Read metrics, execute PromQL queries

#### For Log Analytics (Azure Monitor):
- **Role**: Log Analytics Reader or higher
- **Scope**: Your Log Analytics workspace
- **Permissions**: Query logs, read workspace data

### Testing Your Configuration

Run the test script to verify everything is working:

```bash
python test_supervisor_advanced.py
```

If you see authentication errors while testing locally, that's normal - the managed identity only works when deployed to Azure. The important thing is that the agents attempt to use the configured values instead of asking for parameters.

### Usage Examples

Once configured, users can ask natural questions:

**Incident Analysis:**
- "Show me incidents from the last 24 hours"
- "What are the most common incident types?"
- "Help me analyze incident trends this week"

**Metrics Analysis:**
- "What metrics are available in our workspace?"
- "Show me CPU usage for the last hour"
- "Create a query for memory utilization trends"

**Log Analysis:**
- "Show me the latest container logs"
- "Get error logs from the last 24 hours"
- "Query ContainerLogV2 for application failures"
- "Find traces related to a specific request ID"

### Deployment Notes

When deploying to Azure (App Service, Container Instances, etc.), ensure:
1. Your deployment environment has the managed identity properly configured
2. The managed identity has the required permissions on your Azure resources
3. The config.py file contains your actual resource details (not placeholders)

### Troubleshooting

- **Authentication Errors**: Check MSI permissions and ensure you're running in an Azure environment
- **Config Not Found**: Make sure config.py is in the same directory as supervisor_agent.py
- **Import Errors**: Verify all required packages are installed in your Python environment
