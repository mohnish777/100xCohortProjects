import streamlit as st
from agent import run_agent
import json
from datetime import datetime

st.set_page_config(
    page_title="AI Flight Booking Assistant",
    page_icon="✈️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 0.5rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 0.5rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 0.5rem 0;
    }
    .flight-card {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_log" not in st.session_state:
    st.session_state.conversation_log = []

# Sidebar
with st.sidebar:
    st.title("✈️ Flight Booking Agent")
    st.markdown("---")
    
    st.subheader("📋 Example Queries:")
    example_queries = [
        "Find flights from Singapore to Shenzhen today",
        "What are my saved preferences?",
        "Search for flights from Tokyo to Osaka",
        "Find flights from Delhi to Mumbai"
    ]

    for query in example_queries:
        if st.button(query, key=query, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": query})
            with st.spinner("🤔 Processing your request..."):
                result = run_agent(query)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["response"]
                })
                st.session_state.conversation_log = result["conversation_log"]
            st.rerun()

    st.markdown("---")
    st.info(f"📅 Today's date: {datetime.now().strftime('%Y-%m-%d')}")
    
    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_log = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("### ℹ️ How it works:")
    st.markdown("""
    1. 💬 Type your flight request
    2. 🔍 AI searches flights via API
    3. 👤 AI checks your preferences
    4. ✅ AI processes your request
    5. 📧 Get instant response
    """)

    st.markdown("---")
    st.markdown("### ⚠️ Important Notes:")
    st.markdown("""
    - Free API shows **current/today's flights only**
    - Future dates may return no results
    - Some routes may not have flights
    - Past dates are automatically rejected
    """)

# Main chat interface
st.title("🤖 AI Flight Booking Assistant")
st.markdown("Ask me to find and book flights for you!")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("E.g., 'Book a flight from Delhi to Paris with window seat'"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching flights and processing..."):
            result = run_agent(prompt)
            response = result["response"]
            st.session_state.conversation_log = result["conversation_log"]
            
            st.markdown(response)
            
            # Add assistant message
            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })

# Show tool calls in expander with better formatting
if st.session_state.conversation_log:
    with st.expander("🔧 View Function Calls & Responses (Debug Info)", expanded=False):
        st.markdown("### 📊 Conversation Flow")

        # Group tool calls and responses
        call_count = 0
        i = 0
        while i < len(st.session_state.conversation_log):
            log = st.session_state.conversation_log[i]

            if log["type"] == "tool_call":
                call_count += 1
                function_name = log['function']
                arguments = log['arguments']

                # Create columns for better layout
                col1, col2 = st.columns([1, 3])

                with col1:
                    st.markdown(f"### Step {call_count}")
                    st.markdown(f"**🔧 Function:**")
                    st.code(function_name, language="text")

                with col2:
                    st.markdown("**📤 Arguments:**")
                    st.json(arguments)

                # Check if next item is the response
                if i + 1 < len(st.session_state.conversation_log):
                    next_log = st.session_state.conversation_log[i + 1]
                    if next_log["type"] == "tool_response" and next_log["function"] == function_name:
                        response = next_log["response"]
                        status = response.get("status", "unknown")

                        # Color-code based on status
                        if status == "success":
                            st.markdown('<div class="success-box">✅ <b>Status:</b> Success</div>', unsafe_allow_html=True)
                        elif status == "error":
                            st.markdown('<div class="error-box">❌ <b>Status:</b> Error</div>', unsafe_allow_html=True)
                        elif status == "no_flights":
                            st.markdown('<div class="info-box">ℹ️ <b>Status:</b> No Flights Found</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="info-box">📋 <b>Status:</b> {status}</div>', unsafe_allow_html=True)

                        st.markdown("**📥 Full Response:**")
                        st.json(response)

                        # Show flight details if available
                        if "flights" in response and response["flights"]:
                            st.markdown("**✈️ Flights Found:**")
                            for idx, flight in enumerate(response["flights"], 1):
                                with st.container():
                                    st.markdown(f"""
                                    <div class="flight-card">
                                        <b>Flight {idx}:</b> {flight.get('flight_id', 'N/A')}<br>
                                        <b>Route:</b> {flight.get('departure', 'N/A')} → {flight.get('arrival', 'N/A')}<br>
                                        <b>Airline:</b> {flight.get('airline', 'N/A')}<br>
                                        <b>Departure:</b> {flight.get('departure_time', 'N/A')}<br>
                                        <b>Status:</b> {flight.get('status', 'N/A')}
                                    </div>
                                    """, unsafe_allow_html=True)

                        # Show booking details if available
                        if "booking_reference" in response:
                            st.markdown(f"""
                            <div class="success-box">
                                <b>🎫 Booking Reference:</b> {response['booking_reference']}<br>
                                <b>✈️ Flight ID:</b> {response.get('flight_id', 'N/A')}<br>
                                <b>💺 Seat:</b> {response.get('seat', 'N/A')}<br>
                                <b>🍽️ Meal:</b> {response.get('meal', 'N/A')}
                            </div>
                            """, unsafe_allow_html=True)

                        # Show user preferences if available
                        if "preferences" in response:
                            prefs = response["preferences"]
                            st.markdown(f"""
                            <div class="info-box">
                                <b>👤 User Preferences:</b><br>
                                <b>💺 Seat:</b> {prefs.get('seat_type', 'N/A')}<br>
                                <b>🍽️ Meal:</b> {prefs.get('meal_type', 'N/A')}
                            </div>
                            """, unsafe_allow_html=True)

                        i += 2  # Skip the response since we already processed it
                        st.markdown("---")
                        continue

                i += 1
            else:
                i += 1

        # Summary
        st.markdown("---")
        st.markdown(f"**📈 Total Function Calls:** {call_count}")

        # Show raw JSON in a toggle
        if st.checkbox("📄 Show Raw JSON", key="show_raw_json"):
            st.json(st.session_state.conversation_log)
