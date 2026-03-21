"""
Simple test script to visualize Groq function calling
Hardcoded prompt - no browser needed
api - https://api.aviationstack.com/v1/flights?access_key=1dc2dad618af6bd5d978cbbd68b9a076&limit=100
https://aviationstack.com/documentation
"""
import json
from agent import run_agent

def test_flight_search():
    """Test with a hardcoded prompt"""
    
    # Hardcoded prompt - using a route that has flights TODAY
    prompt = "Find flights from Singapore to Shenzhen today and book the first one"
    # prompt = "Find flights from Delhi to Paris and book one"
    
    print("=" * 80)
    print(f"🤖 TESTING GROQ AGENT")
    print("=" * 80)
    print(f"\n📝 Prompt: {prompt}\n")
    print("🔄 Running agent...\n")
    
    try:
        # Call the agent
        result = run_agent(prompt)
        
        # Extract results
        conversation_log = result.get("conversation_log", [])
        final_response = result.get("response", "")
        
        # Display conversation log
        print("=" * 80)
        print("📊 CONVERSATION LOG (Function Calls)")
        print("=" * 80)
        
        for i, log_entry in enumerate(conversation_log, 1):
            if log_entry["type"] == "tool_call":
                print(f"\n🔧 STEP {i}: AI CALLS FUNCTION")
                print(f"   Function: {log_entry['function']}")
                print(f"   Arguments: {json.dumps(log_entry['arguments'], indent=6)}")
                
            elif log_entry["type"] == "tool_response":
                print(f"\n📥 STEP {i}: FUNCTION RESPONSE")
                print(f"   Function: {log_entry['function']}")
                print(f"   Response: {json.dumps(log_entry['response'], indent=6)}")
        
        # Display final response
        print("\n" + "=" * 80)
        print("💬 FINAL AI RESPONSE")
        print("=" * 80)
        print(final_response)
        
        # Display raw JSON
        print("\n" + "=" * 80)
        print("📋 RAW CONVERSATION LOG (JSON)")
        print("=" * 80)
        print(json.dumps(conversation_log, indent=2))
        
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_flight_search()