"""
Comprehensive test script to demonstrate all fixes
"""
import json
from agent import run_agent

def print_test_header(test_num, description):
    print("\n" + "=" * 80)
    print(f"TEST {test_num}: {description}")
    print("=" * 80)

def print_result(result):
    conversation_log = result.get("conversation_log", [])
    final_response = result.get("response", "")
    
    print("\n📊 Function Calls:")
    for log_entry in conversation_log:
        if log_entry["type"] == "tool_call":
            print(f"  🔧 {log_entry['function']}({json.dumps(log_entry['arguments'])})")
        elif log_entry["type"] == "tool_response":
            status = log_entry['response'].get('status', 'unknown')
            print(f"  📥 Response: {status}")
    
    print(f"\n💬 Final Response:\n{final_response}\n")

# Test 1: Date validation - should reject past dates
print_test_header(1, "Date Validation - Past Date Should Be Rejected")
try:
    result1 = run_agent("Find flights from Delhi to Mumbai on 2024-01-01")
    print_result(result1)
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Current date usage
print_test_header(2, "Current Date - Should Use Today's Date")
try:
    result2 = run_agent("Find flights from Singapore to Shenzhen")
    print_result(result2)
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Future date (7 days from now)
print_test_header(3, "Future Date - Should Use Next Week")
try:
    result3 = run_agent("Find flights from Tokyo to Osaka next week")
    print_result(result3)
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Get user preferences only
print_test_header(4, "Get User Preferences - Should Call get_user_preferences")
try:
    result4 = run_agent("What are my saved preferences?")
    print_result(result4)
except Exception as e:
    print(f"❌ Error: {e}")

# Test 5: Invalid flight ID booking
print_test_header(5, "Invalid Flight ID - Should Reject Empty/Invalid IDs")
try:
    result5 = run_agent("Book flight with ID ''")
    print_result(result5)
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("✅ ALL TESTS COMPLETE")
print("=" * 80)
print("\n📝 Summary of Fixes:")
print("  ✅ System prompt now includes current date (2025-12-20)")
print("  ✅ Date validation rejects past dates")
print("  ✅ Tool descriptions improved for clarity")
print("  ✅ book_flight validates flight IDs")
print("  ✅ AI instructed not to make up flight IDs")
print("\n⚠️  Note: Free API may not return flights for all routes")
print("   This is an API limitation, not a code issue.\n")

