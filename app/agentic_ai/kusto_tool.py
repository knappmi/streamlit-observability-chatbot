from azure.kusto.data import KustoConnectionStringBuilder, KustoClient
from azure.identity import DefaultAzureCredential
from langchain_core.tools import tool

def list_kusto_tables(cluster_uri, database, client_id=None, tenant_id=None):
    """
    Returns a list of tables in the specified Kusto database.
    """
    token_credential = DefaultAzureCredential()
    kcsb = KustoConnectionStringBuilder.with_azure_token_credential(cluster_uri, token_credential)
    client = KustoClient(kcsb)
    query = ".show tables"
    response = client.execute(database, query)
    return [row['TableName'] for row in response.primary_results[0]]

@tool
def kusto_list_tables_tool(
    cluster_uri: str,
    database: str,
    client_id: str = None,
    tenant_id: str = None
) -> list:
    """
    List all tables in the specified Kusto cluster and database.
    """
    return list_kusto_tables(cluster_uri, database, client_id, tenant_id)