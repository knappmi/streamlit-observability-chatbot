import streamlit as st
import sys
import os
import re
from datetime import datetime

# Configure page settings - must be first Streamlit command
st.set_page_config(
    page_title="Ask Jarvis",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"  # Can be "expanded", "collapsed", or "auto"
)

# Add current directory to path so we can import supervisor_agent
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def build_context_aware_prompt(user_prompt, conversation_history, context):
    """Build a context-aware prompt that includes conversation history and current context."""
    
    # Build context string
    context_parts = []
    if context['last_incident_id']:
        context_parts.append(f"Currently investigating incident: {context['last_incident_id']}")
    if context['last_deployment']:
        context_parts.append(f"Recent deployment context: {context['last_deployment']}")
    if context['active_investigation']:
        context_parts.append(f"Active investigation: {context['active_investigation']}")
    
    # Build recent conversation context (last 5 messages)
    recent_messages = []
    if len(conversation_history) > 1:  # More than just the current message
        for msg in conversation_history[-6:-1]:  # Last 5 messages before current
            if msg['role'] == 'user':
                recent_messages.append(f"User previously asked: {msg['content']}")
            elif msg['role'] == 'assistant' and not msg['content'].startswith('❌'):
                # Truncate long responses for context
                content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
                recent_messages.append(f"Assistant previously responded: {content}")
    
    # Build the enhanced prompt
    enhanced_prompt = user_prompt
    
    if context_parts or recent_messages:
        enhanced_prompt = f"""
CONTEXT INFORMATION:
{chr(10).join(context_parts) if context_parts else "No specific context"}

RECENT CONVERSATION:
{chr(10).join(recent_messages[-3:]) if recent_messages else "No recent conversation"}

CURRENT REQUEST:
{user_prompt}

Please provide a response that takes into account the above context and conversation history. If the current request relates to previous topics, reference them appropriately.
"""
    
    return enhanced_prompt

def extract_response_content(result):
    """Extract the response content from the supervisor result."""
    if hasattr(result, 'get') and 'messages' in result:
        messages = result['messages']
        if messages:
            # Find the last assistant message
            for msg in reversed(messages):
                if hasattr(msg, 'content') or isinstance(msg, dict):
                    content = msg.content if hasattr(msg, 'content') else str(msg)
                    if content and content.strip():
                        return content
    
    return "I processed your request, but couldn't generate a response."

def update_context_from_response(response, context):
    """Update session context based on the assistant's response."""
    response_lower = response.lower()
    
    # Extract incident IDs (pattern: incident numbers, ICM IDs, etc.)
    incident_patterns = [
        r'incident[:\s]+(\d+)',
        r'icm[:\s]+(\d+)',
        r'incident id[:\s]+([a-zA-Z0-9-]+)',
        r'#(\d+)'
    ]
    
    for pattern in incident_patterns:
        matches = re.findall(pattern, response_lower)
        if matches:
            context['last_incident_id'] = matches[-1]  # Use the last found incident
            break
    
    # Look for deployment information
    deployment_patterns = [
        r'deployment[:\s]+([a-zA-Z0-9.-]+)',
        r'release[:\s]+([a-zA-Z0-9.-]+)',
        r'version[:\s]+([a-zA-Z0-9.-]+)'
    ]
    
    for pattern in deployment_patterns:
        matches = re.findall(pattern, response_lower)
        if matches:
            context['last_deployment'] = matches[-1]
            break
    
    # Detect investigation type
    if any(word in response_lower for word in ['investigating', 'analyzing', 'troubleshooting', 'diagnosing']):
        if 'incident' in response_lower:
            context['active_investigation'] = 'incident_analysis'
        elif 'deployment' in response_lower:
            context['active_investigation'] = 'deployment_analysis'
        elif 'performance' in response_lower or 'metric' in response_lower:
            context['active_investigation'] = 'performance_analysis'
        else:
            context['active_investigation'] = 'general_investigation'
    
    # Clear investigation if resolution is indicated
    if any(word in response_lower for word in ['resolved', 'fixed', 'completed', 'closed']):
        context['active_investigation'] = None

# Initialize session storage
if 'saved_sessions' not in st.session_state:
    st.session_state.saved_sessions = {}

# Initialize session state for conversation history
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'session_id' not in st.session_state:
    st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

if 'context' not in st.session_state:
    st.session_state.context = {
        'last_incident_id': None,
        'last_deployment': None,
        'active_investigation': None
    }

# Helper functions for session management
def save_current_session():
    """Save the current session to the saved_sessions dictionary."""
    if st.session_state.messages:
        # Generate a title based on the first user message or use timestamp
        title = "New Session"
        if st.session_state.messages:
            first_user_msg = next((msg for msg in st.session_state.messages if msg['role'] == 'user'), None)
            if first_user_msg:
                # Use first 50 chars of first user message as title
                title = first_user_msg['content'][:50] + "..." if len(first_user_msg['content']) > 50 else first_user_msg['content']
        
        st.session_state.saved_sessions[st.session_state.session_id] = {
            'title': title,
            'messages': st.session_state.messages.copy(),
            'context': st.session_state.context.copy(),
            'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'message_count': len(st.session_state.messages)
        }

def load_session(session_id):
    """Load a session from the saved_sessions dictionary."""
    if session_id in st.session_state.saved_sessions:
        session_data = st.session_state.saved_sessions[session_id]
        st.session_state.messages = session_data['messages'].copy()
        st.session_state.context = session_data['context'].copy()
        st.session_state.session_id = session_id
        # Update last accessed time
        st.session_state.saved_sessions[session_id]['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def create_new_session():
    """Create a new session."""
    # Save current session first if it has messages
    if st.session_state.messages:
        save_current_session()
    
    # Create new session
    st.session_state.messages = []
    st.session_state.context = {
        'last_incident_id': None,
        'last_deployment': None,
        'active_investigation': None
    }
    st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

def delete_session(session_id):
    """Delete a session from saved sessions."""
    if session_id in st.session_state.saved_sessions:
        del st.session_state.saved_sessions[session_id]
        # If we're deleting the current session, create a new one
        if session_id == st.session_state.session_id:
            create_new_session()

# Import supervisor
try:
    from supervisor_agent import supervisor, create_dynamic_supervisor
    supervisor_available = True
except ImportError as e:
    supervisor_available = False
    import_error = str(e)

# Header with model selection
col1, col2, col3 = st.columns([2.5, 1, 0.5])
with col1:
    st.title("👁️ Ask Jarvis - Your Observability Assistant")

with col2:
    # Model selection dropdown
    model_options = {
        "Standard Model": "standard",
        "Experimental Model": "dynamic"
    }
    
    # Initialize model selection in session state
    if 'selected_model_type' not in st.session_state:
        st.session_state.selected_model_type = "standard"
    
    # Model selector
    selected_model_label = st.selectbox(
        "🤖 Model Type",
        options=list(model_options.keys()),
        index=0,  # Default to Standard Model
        help="Standard: Fixed temperature (0.1), Experimental: Adjustable via sidebar slider"
    )
    
    # Update session state
    st.session_state.selected_model_type = model_options[selected_model_label]

with col3:
    # Reserved space for future features
    st.markdown("####")  # Add some spacing

# Custom CSS for better styling
st.markdown("""
<style>
.session-title {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 5px;
}
.session-info {
    font-size: 12px;
    color: #666;
    margin-bottom: 10px;
}
.current-session {
    border-left: 3px solid #00ff00;
    padding-left: 10px;
    background-color: #f0f8f0;
}
.stExpander > div:first-child {
    background-color: #f8f9fa;
}

/* Sidebar styling */
.css-1d391kg {
    position: relative;
}

/* Add hover effect for sidebar toggle */
.css-17eq0hr {
    transition: all 0.3s ease;
}

/* Sidebar collapse button styling */
[data-testid="collapsedControl"] {
    background-color: #f0f2f6;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
    transition: all 0.2s ease;
}

[data-testid="collapsedControl"]:hover {
    background-color: #e6e9ef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Make the sidebar content area more defined when expanded */
.css-1lcbmhc {
    border-right: 2px solid #f0f2f6;
    padding-right: 1rem;
}
</style>
""", unsafe_allow_html=True)

# Sidebar for session management
with st.sidebar:
    st.header("💬 Chat Sessions")
    
    # Temperature Control (only show for experimental model)
    if st.session_state.selected_model_type == "dynamic":
        st.subheader("🌡️ Temperature Control")
        
        # Initialize temperature in session state
        if 'selected_temperature' not in st.session_state:
            st.session_state.selected_temperature = 0.5
        
        # Temperature slider
        st.session_state.selected_temperature = st.slider(
            "Response Creativity",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.selected_temperature,
            step=0.1,
            help="Lower = more focused and precise, Higher = more creative and diverse"
        )
        
        # Temperature description
        if st.session_state.selected_temperature <= 0.2:
            temp_desc = "Very Conservative"
        elif st.session_state.selected_temperature <= 0.4:
            temp_desc = "Conservative"
        elif st.session_state.selected_temperature <= 0.6:
            temp_desc = "Balanced"
        elif st.session_state.selected_temperature <= 0.8:
            temp_desc = "Creative"
        else:
            temp_desc = "Very Creative"
        
        st.info(f"**Current Setting:** {st.session_state.selected_temperature} ({temp_desc})")
        
        # Prompt Customization
        st.markdown("---")
        st.subheader("✏️ Agent Prompts")
        st.write("Customize the behavior of each agent by editing their prompts:")
        
        # Initialize custom prompts in session state with defaults
        if 'custom_prompts' not in st.session_state:
            st.session_state.custom_prompts = {
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
                ),
                "line_graph": (
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
                )
            }
        
        # Kusto Agent Prompt
        with st.expander("🔍 Kusto Agent Prompt", expanded=False):
            st.session_state.custom_prompts["kusto"] = st.text_area(
                "Kusto Agent Instructions:",
                value=st.session_state.custom_prompts["kusto"],
                height=200,
                help="Define how the Kusto agent should behave when analyzing incidents and deployments"
            )
        
        # Prometheus Agent Prompt
        with st.expander("📊 Prometheus Agent Prompt", expanded=False):
            st.session_state.custom_prompts["prometheus"] = st.text_area(
                "Prometheus Agent Instructions:",
                value=st.session_state.custom_prompts["prometheus"],
                height=200,
                help="Define how the Prometheus agent should behave when analyzing metrics"
            )
        
        # Log Analytics Agent Prompt
        with st.expander("📋 Log Analytics Agent Prompt", expanded=False):
            st.session_state.custom_prompts["log_analytics"] = st.text_area(
                "Log Analytics Agent Instructions:",
                value=st.session_state.custom_prompts["log_analytics"],
                height=200,
                help="Define how the Log Analytics agent should behave when querying logs"
            )
        
        # Line Graph Agent Prompt
        with st.expander("📈 Line Graph Agent Prompt", expanded=False):
            st.session_state.custom_prompts["line_graph"] = st.text_area(
                "Line Graph Agent Instructions:",
                value=st.session_state.custom_prompts["line_graph"],
                height=200,
                help="Define how the Line Graph agent should behave when creating visualizations"
            )
        
        # Reset to defaults button
        if st.button("🔄 Reset Prompts to Default", use_container_width=True):
            st.session_state.custom_prompts = {
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
                ),
                "line_graph": (
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
                )
            }
            st.success("✅ Prompts reset to defaults!")
            st.rerun()
        
        st.markdown("---")
    
    else:
        # For standard model, set fixed temperature and ensure custom_prompts exists
        st.session_state.selected_temperature = 0.1
        # Initialize custom prompts if not exists (for when switching between models)
        if 'custom_prompts' not in st.session_state:
            st.session_state.custom_prompts = {
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
                ),
                "line_graph": (
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
                )
            }
    
    # New Session button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 New", use_container_width=True):
            create_new_session()
            st.success("New session started!")
            st.rerun()
    
    with col2:
        if st.button("💾 Save", use_container_width=True):
            save_current_session()
            st.success("Session saved!")
            st.rerun()
    
    # Display saved sessions
    if st.session_state.saved_sessions:
        st.subheader(f"📁 Saved Sessions ({len(st.session_state.saved_sessions)})")
        
        # Sort sessions by last updated time (most recent first)
        sorted_sessions = sorted(
            st.session_state.saved_sessions.items(), 
            key=lambda x: x[1]['last_updated'], 
            reverse=True
        )
        
        for session_id, session_data in sorted_sessions:
            is_current = session_id == st.session_state.session_id
            
            # Create a container for each session with custom styling
            container_class = "current-session" if is_current else ""
            
            # Session title with current indicator and message count
            title_prefix = "🟢 " if is_current else "💬 "
            title = f"{title_prefix}{session_data['title']} ({session_data['message_count']} msgs)"
            
            # Collapsible session info
            with st.expander(title, expanded=False):
                # Session metadata
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"📅 **Created:**")
                    st.write(session_data['created'])
                with col2:
                    st.write(f"🔄 **Last Active:**")
                    st.write(session_data['last_updated'])
                
                # Context info in a more compact format
                context_items = []
                if session_data['context']['last_incident_id']:
                    context_items.append(f"🚨 {session_data['context']['last_incident_id']}")
                if session_data['context']['last_deployment']:
                    context_items.append(f"🚀 {session_data['context']['last_deployment']}")
                if session_data['context']['active_investigation']:
                    context_items.append(f"🔍 {session_data['context']['active_investigation']}")
                
                if context_items:
                    st.write("**Context:**")
                    for item in context_items:
                        st.write(f"- {item}")
                else:
                    st.write("**Context:** *None*")
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📂 Load", key=f"load_{session_id}", use_container_width=True, disabled=is_current):
                        load_session(session_id)
                        st.success(f"✅ Loaded: {session_data['title'][:30]}")
                        st.rerun()
                
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{session_id}", use_container_width=True):
                        delete_session(session_id)
                        st.success("✅ Session deleted!")
                        st.rerun()
        
        # Session statistics
        total_messages = sum(session['message_count'] for session in st.session_state.saved_sessions.values())
        st.info(f"📊 Total messages across all sessions: **{total_messages}**")
        
        # Clear all sessions
        st.markdown("---")
        if st.button("🗑️ Clear All Sessions", use_container_width=True):
            st.session_state.saved_sessions = {}
            create_new_session()
            st.success("✅ All sessions cleared!")
            st.rerun()
    
    else:
        st.write("*No saved sessions*")
        st.info("💡 Start a conversation and click 'Save' to save your session!")
    
    st.markdown("---")
    
    # Current session info
    st.header("📊 Current Session")
    st.write(f"**ID:** `{st.session_state.session_id}`")
    st.write(f"**Messages:** {len(st.session_state.messages)}")
    st.write(f"**Model:** {selected_model_label}")
    
    if st.session_state.selected_model_type == "dynamic":
        temp_desc = "Very Conservative" if st.session_state.selected_temperature <= 0.2 else \
                   "Conservative" if st.session_state.selected_temperature <= 0.4 else \
                   "Balanced" if st.session_state.selected_temperature <= 0.6 else \
                   "Creative" if st.session_state.selected_temperature <= 0.8 else "Very Creative"
        st.write(f"**Temperature:** {st.session_state.selected_temperature} ({temp_desc})")
        st.write(f"**Custom Prompts:** ✅ Active")
    else:
        st.write(f"**Temperature:** 0.1 (Fixed - Conservative)")
        st.write(f"**Custom Prompts:** Default")
    
    # Display current context
    st.subheader("🎯 Active Context")
    if st.session_state.context['last_incident_id']:
        st.write(f"🚨 **Incident:** {st.session_state.context['last_incident_id']}")
    if st.session_state.context['last_deployment']:
        st.write(f"🚀 **Deployment:** {st.session_state.context['last_deployment']}")
    if st.session_state.context['active_investigation']:
        st.write(f"🔍 **Investigation:** {st.session_state.context['active_investigation']}")
    
    if not any(st.session_state.context.values()):
        st.write("*No active context*")
    
    # Quick actions
    st.markdown("---")
    if st.button("🔄 Clear History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.context = {
            'last_incident_id': None,
            'last_deployment': None,
            'active_investigation': None
        }
        st.success("History cleared!")
        st.rerun()

# Main chat area
st.header("Conversation")

# Display conversation history
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "timestamp" in message:
            caption_parts = [f"⏱️ {message['timestamp']}"]
            if "response_time" in message:
                caption_parts.append(message['response_time'])
            if "temperature_label" in message:
                caption_parts.append(f"🌡️ {message['temperature_label']}")
            st.caption(" | ".join(caption_parts))

# Input for new message
if prompt := st.chat_input("Ask me anything about your infrastructure..."):
    if not supervisor_available:
        st.error(f"❌ Supervisor agent not available: {import_error}")
        st.stop()
    
    # Add user message to conversation history
    user_message = {
        "role": "user", 
        "content": prompt,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    st.session_state.messages.append(user_message)
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Build context-aware prompt
            context_prompt = build_context_aware_prompt(prompt, st.session_state.messages, st.session_state.context)
            
            # Show thinking indicator
            with st.spinner("🤔 Jarvis is thinking..."):
                start_time = datetime.now()
                
                # Choose supervisor based on model type
                if st.session_state.selected_model_type == "standard":
                    # Use original supervisor with fixed temperature (0.1)
                    result = supervisor.invoke({
                        "messages": [("user", context_prompt)]
                    })
                else:
                    # Use dynamic supervisor with selected temperature and custom prompts
                    dynamic_supervisor = create_dynamic_supervisor(
                        temperature=st.session_state.selected_temperature,
                        session_context=st.session_state.context,
                        custom_prompts=st.session_state.custom_prompts
                    )
                    result = dynamic_supervisor.invoke({
                        "messages": [("user", context_prompt)]
                    })
                
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
            
            # Extract the final message from supervisor response
            response = extract_response_content(result)
            
            # Update context based on response
            update_context_from_response(response, st.session_state.context)
            
            # Display the response
            message_placeholder.markdown(response)
            
            # Generate temperature label
            if st.session_state.selected_model_type == "standard":
                temp_label = "Standard Model (0.1)"
            else:
                temp_desc = "Very Conservative" if st.session_state.selected_temperature <= 0.2 else \
                           "Conservative" if st.session_state.selected_temperature <= 0.4 else \
                           "Balanced" if st.session_state.selected_temperature <= 0.6 else \
                           "Creative" if st.session_state.selected_temperature <= 0.8 else "Very Creative"
                temp_label = f"Experimental ({st.session_state.selected_temperature}) - {temp_desc}"
            
            # Add assistant response to conversation history
            assistant_message = {
                "role": "assistant", 
                "content": response,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "response_time": f"{response_time:.2f}s",
                "temperature": st.session_state.selected_temperature,
                "temperature_label": temp_label,
                "model_type": st.session_state.selected_model_type
            }
            st.session_state.messages.append(assistant_message)
            
            # Add temperature info to response display
            st.caption(f"⏱️ {response_time:.2f}s | 🌡️ {temp_label}")
            
            # Auto-save session after each response
            save_current_session()
            
        except Exception as e:
            error_message = f"❌ Error processing request: {str(e)}"
            message_placeholder.error(error_message)
            
            # Add error to conversation history
            error_msg = {
                "role": "assistant", 
                "content": error_message,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            st.session_state.messages.append(error_msg)

# Display helpful examples if no conversation history
if len(st.session_state.messages) == 0:
    st.markdown("""
    ### 💡 Try asking Jarvis:
    
    **Incident Investigation:**
    - "Show me the latest P0 incidents"
    - "Analyze incident #12345"
    - "What incidents occurred after the last deployment?"
    
    **Deployment Analysis:**
    - "Show me recent deployments"
    - "Did any deployments cause incidents this week?"
    - "Get deployment events from yesterday"
    
    **Metrics & Performance:**
    - "Show me CPU metrics for the last hour"
    - "What Prometheus metrics are available?"
    - "Check memory usage trends"
    
    **Log Analysis:**
    - "Show me error logs from the last hour"
    - "Get container logs for failed pods"
    - "Find logs related to the current incident"
    
    **Time Series Visualizations:**
    - "Create a line chart of CPU usage over the last hour"
    - "Show me a timeline of incidents with system metrics"
    - "Graph the impact of deployments on error rates"
    - "Create a multi-metric chart showing CPU and memory trends"
    - "Visualize incident patterns over time"
    
    **Contextual Follow-ups:**
    - "Tell me more about that incident"
    - "What were the metrics during that deployment?"
    - "Show me logs from the same timeframe"
    - "Graph the metrics around that incident"
    
    ---
    
    ### 🎛️ Interface Tips:
    
    **Sidebar Controls:**
    - **Collapse Sidebar**: Use the native collapse button to hide/show the sidebar
    - 🔄 **Session Management**: Save, load, and manage conversation history
    - 🌡️ **Experimental Mode**: Access temperature control and custom prompts
    
    **Model Selection:**
    - 🤖 **Standard Model**: Consistent, reliable responses (temp: 0.1)
    - 🧪 **Experimental Model**: Customizable creativity and agent prompts (includes visualization agent)
    
    **Visualization Features:**
    - 📈 **Line Charts**: Time series data visualization with interactive plots
    - 📊 **Multi-Metric Charts**: Compare multiple metrics on the same timeline
    - 🎯 **Incident Timelines**: Overlay incidents on system metrics
    - 🚀 **Deployment Impact**: Visualize how deployments affect system performance
    """)

# Footer with session info
st.markdown("---")
st.caption(f"Session: {st.session_state.session_id} | Powered by Team Argus | ANF ChatBots")
