import streamlit as st

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
        "",
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
    with st.spinner("🤔 Jarvis is thinking..."):
        # Placeholder for Azure AI service call
        st.success("✅ Request received!")
        
        # Display user's prompt
        st.markdown("### Your Question:")
        st.info(user_prompt)
        
        # Placeholder response area
        st.markdown("### Jarvis Response:")
        st.markdown("""
        *This is where the response from your Azure AI service will appear.*
        
        Currently, this is a placeholder. You'll need to integrate with your Azure AI service to get actual responses.
        """)
        
        # Add some spacing
        st.markdown("---")

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
