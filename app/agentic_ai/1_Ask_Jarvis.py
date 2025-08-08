import streamlit as st
import sys
import os
# Add current directory to path so we can import supervisor_agent
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from supervisor_agent import supervisor
    supervisor_available = True
except ImportError as e:
    supervisor_available = False
    import_error = str(e)

# Page header
st.markdown("# 🤖 Ask Jarvis")
st.markdown("*Your intelligent AI assistant powered by Azure*")
st.markdown("---")

# Create two columns for a clean layout
col1, col2 = st.columns([3, 1])

with col1:
    # Main chat interface
    st.markdown("### What can I help you with today?")
    
    # Chat input
    user_prompt = st.text_area(
        "Your Question",
        placeholder="Type your question or request here...",
        height=100,
        label_visibility="collapsed"
    )
    
    # Submit button
    submit_button = st.button("Ask Jarvis", type="primary", use_container_width=True)

with col2:
    # Quick actions or tips
    st.markdown("### Quick Tips")
    st.markdown("""
    - Ask specific questions
    - Get explanations
    - Troubleshoot issues
    """)

# Process the request
if submit_button and user_prompt:
    if not supervisor_available:
        st.error(f"❌ Supervisor agent not available: {import_error}")
        st.stop()
    
    with st.spinner("🤔 Jarvis is thinking..."):
        try:
            # Use the supervisor agent to process the input
            response = supervisor.invoke({"messages": [{"role": "user", "content": user_prompt}]})
            
            # Extract the AI response content from the messages
            ai_response = ""
            if "messages" in response:
                for message in response["messages"]:
                    if hasattr(message, 'content') and hasattr(message, 'name') and message.name == 'supervisor':
                        ai_response = message.content
                        break
            
            # If no supervisor response found, get the last message
            if not ai_response and "messages" in response and response["messages"]:
                last_message = response["messages"][-1]
                if hasattr(last_message, 'content'):
                    ai_response = last_message.content
            
            if not ai_response:
                ai_response = "I'm sorry, I couldn't process your request at this time."

            # Display user's prompt
            st.markdown("### Your Question:")
            st.info(user_prompt)

            # Display the agent's response
            st.markdown("### Jarvis Response:")
            st.success(ai_response)

            # Add some spacing
            st.markdown("---")
            
        except Exception as e:
            st.error(f"❌ Error processing request: {str(e)}")
            st.error("Please check the logs for more details.")

elif submit_button and not user_prompt:
    st.warning("⚠️ Please enter a question or prompt before submitting.")

# Footer with additional info
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    Powered by Team Argus | ANF ChatBots
    </div>
    """, 
    unsafe_allow_html=True
)
