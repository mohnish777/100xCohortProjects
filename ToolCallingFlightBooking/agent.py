import os
import json
from datetime import datetime, timedelta

import requests
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# AviationStack API Key
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

USER_PREFERENCES = {
    "user123": {
        "seat_preferece" : "window",
        "meal_preference" :"vegetarian",
        "frequent_flyer" : "Air France"
    }
}

# Tool: search_flights (AviationStack API)
def search_flights(departure, destination, date=None):
    """
    Search real flights via AviationStack API.
    Since free tier doesn't support filtering by route/date, we fetch flights and filter locally.
    """
    # If user didn't pass a date, default to today (free tier only shows current/today's flights)
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Validate date is not in the past
    try:
        search_date = datetime.strptime(date, "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if search_date < today:
            return {
                "status": "error",
                "message": f"Cannot search for past dates. Date provided: {date}. Please use today ({today.strftime('%Y-%m-%d')}) or a future date.",
                "search_query": {
                    "from": departure,
                    "to": destination,
                    "date": date
                }
            }
    except ValueError:
        return {
            "status": "error",
            "message": f"Invalid date format: {date}. Please use YYYY-MM-DD format (e.g., 2025-12-27).",
            "search_query": {
                "from": departure,
                "to": destination,
                "date": date
            }
        }

    # Simple city → IATA mapping
    city_to_iata = {
        "Delhi": "DEL", "New Delhi": "DEL",
        "Paris": "CDG", "PAR": "CDG",
        "Mumbai": "BOM",
        "Bangalore": "BLR", "Bengaluru": "BLR",
        "London": "LHR", "LON": "LHR",
        "Dubai": "DXB",
        "New York": "JFK", "NYC": "JFK",
        "Los Angeles": "LAX", "LA": "LAX",
        "San Francisco": "SFO",
        "Chicago": "ORD",
        "Boston": "BOS",
        "Amsterdam": "AMS",
        "Frankfurt": "FRA",
        "Singapore": "SIN",
        "Tokyo": "NRT",
        "Hong Kong": "HKG",
        "Shenzhen": "SZX",
        "Singapore": "SIN"
    }

    origin = city_to_iata.get(departure, departure.upper())
    dest = city_to_iata.get(destination, destination.upper())

    # AviationStack API endpoint (free tier - fetches current flights)
    url = "http://api.aviationstack.com/v1/flights"

    params = {
        "access_key": AVIATIONSTACK_API_KEY,
        "limit": 100  # Fetch more flights to increase chance of finding matches
    }

    try:
        print(f"Searching flights from {origin} to {dest}...")
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        if "error" in data:
            return {
                "status": "error",
                "message": f"API Error: {data['error'].get('message', 'Unknown error')}",
                "search_date": date,
                "source": "aviationstack"
            }

        all_flights = data.get("data", [])

        # Filter flights matching origin and destination
        matching_flights = []
        for flight_data in all_flights:
            dep = flight_data.get("departure", {})
            arr = flight_data.get("arrival", {})

            dep_iata = dep.get("iata", "")
            arr_iata = arr.get("iata", "")

            # Check if this flight matches our route
            if dep_iata == origin and arr_iata == dest:
                flight_info = flight_data.get("flight", {})
                airline_info = flight_data.get("airline", {})

                matching_flights.append({
                    "id": flight_info.get("iata", flight_info.get("number", "N/A")),
                    "airline": airline_info.get("name", "Unknown Airline"),
                    "flight_number": flight_info.get("iata", flight_info.get("number", "N/A")),
                    "price": None,  # Free tier doesn't provide pricing
                    "currency": "USD",
                    "departure_time": dep.get("scheduled", "N/A"),
                    "arrival_time": arr.get("scheduled", "N/A"),
                    "duration": "N/A",
                    "direct": True,  # Assume direct for simplicity
                    "origin": dep.get("airport", origin),
                    "destination": arr.get("airport", dest),
                    "status": flight_data.get("flight_status", "scheduled")
                })

        if not matching_flights:
            return {
                "status": "no_flights",
                "message": f"No flights found from {departure} ({origin}) to {destination} ({dest}). Try different cities or check IATA codes.",
                "search_query": {
                    "from": departure,
                    "to": destination,
                    "date": date,
                    "origin_code": origin,
                    "dest_code": dest
                },
                "flights": [],
                "search_date": date,
                "source": "aviationstack",
                "note": "Free tier shows only current/today's flights. For future dates, upgrade to paid plan."
            }

        # Limit to top 5 flights
        matching_flights = matching_flights[:5]

        return {
            "status": "success",
            "search_query": {
                "from": departure,
                "to": destination,
                "date": date,
                "origin_code": origin,
                "dest_code": dest
            },
            "flights": matching_flights,
            "total_found": len(matching_flights),
            "search_date": date,
            "source": "aviationstack",
            "note": "Prices not available in free tier. Showing current/today's flights only."
        }

    except Exception as e:
        print(f"Error searching flights: {e}")
        return {
            "status": "error",
            "message": f"Error searching flights: {str(e)}",
            "search_date": date,
            "source": "aviationstack"
        }
    

# -----------------------------
# Tool: get_user_preferences
# -----------------------------
def get_user_preferences(user_id="user123"):
    """
    Get saved user preferences; in real app this would query a DB.
    """
    prefs = USER_PREFERENCES.get(user_id)
    if prefs:
        return {"status": "success", "preferences": prefs, "source": "db_mock"}

    return {
        "status": "no_preferences",
        "message": "No saved preferences found",
        "source": "none"
    }

# Tool: book_flight
# -----------------------------
def book_flight(flight_id, seat_type=None, meal_type=None, user_id="user123"):
    """
    Fake booking: generates a booking reference and returns details.
    In real life this would call a booking/payment API.
    """
    # Validate flight_id is not empty or invalid
    if not flight_id or flight_id.strip() == "":
        return {
            "status": "error",
            "message": "Invalid flight ID. Please search for flights first and use a valid flight ID from the search results."
        }

    # Basic validation: check if flight_id looks reasonable (alphanumeric)
    if not flight_id.replace("-", "").replace("_", "").isalnum():
        return {
            "status": "error",
            "message": f"Invalid flight ID format: '{flight_id}'. Flight ID should be alphanumeric (e.g., 'CA7972', 'NH93')."
        }

    # In a real system, you would check if the flight exists in a database
    # For now, we'll accept any reasonable-looking flight ID
    # TODO: Add actual flight validation against search results

    final_seat = seat_type or "any"
    final_meal = meal_type or "standard"

    booking_ref = f"BK{abs(hash(flight_id + user_id + str(datetime.now()))) % 10000:04d}"

    return {
        "status": "success",
        "booking_reference": booking_ref,
        "flight_id": flight_id,
        "seat": final_seat,
        "meal": final_meal,
        "message": f"Flight booked successfully! Reference: {booking_ref}"
    }


# -----------------------------
# Tool schema for OpenAI
# -----------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search available flights between two cities on a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "departure": {
                        "type": "string",
                        "description": "Departure city, e.g., 'Delhi'"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination city, e.g., 'Paris'"
                    },
                    "date": {
                        "type": "string",
                        "description": "Travel date in YYYY-MM-DD format (e.g., 2025-12-27). Must be today or a future date. If user doesn't specify, use a date 7 days from today. Never use past dates."
                    }
                },
                "required": ["departure", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_preferences",
            "description": "Get user's saved seat and meal preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID (defaults to user123 if omitted)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_flight",
            "description": "Book a specific flight with desired seat and meal preferences. IMPORTANT: Only use flight IDs that were returned from search_flights. Do NOT make up or guess flight IDs. If no flights were found in the search, do not attempt to book.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_id": {
                        "type": "string",
                        "description": "ID of the flight to book. Must be a valid flight_id from the search_flights results (e.g., 'CA7972', 'NH93'). Do NOT use made-up flight IDs."
                    },
                    "seat_type": {
                        "type": "string",
                        "description": "Seat preference: window, aisle, or any."
                    },
                    "meal_type": {
                        "type": "string",
                        "description": "Meal preference: vegetarian, non-vegetarian, vegan, or standard."
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID performing the booking."
                    }
                },
                "required": ["flight_id"]
            }
        }
    }
]

available_functions = {
    "search_flights": search_flights,
    "get_user_preferences": get_user_preferences,
    "book_flight": book_flight
}

# -----------------------------
# Agent runner (multi-tool loop)
# -----------------------------
def run_agent(user_query, user_id="user123"):
    """
    Run the multi-step agent:
    - Send user_query + tool definitions to OpenAI
    - Execute requested tools in Python
    - Feed tool results back to the model
    - Repeat until model returns a final answer
    Also returns conversation_log for debugging.
    """
    # Add system prompt with current date
    today = datetime.now().strftime('%Y-%m-%d')
    system_prompt = f"""You are a helpful flight booking assistant.
Today's date is {today}.
When searching for flights, always use today's date or future dates. Never use past dates.
If the user doesn't specify a date, assume they want flights for next week (7 days from today).
Only book flights that were actually found in the search results. Do not make up flight IDs."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]
    conversation_log = []

    iteration = 0
    max_iterations = 10

    while iteration < max_iterations:
        iteration += 1

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        msg = response.choices[0].message
        tool_calls = msg.tool_calls

        # No tool calls → final answer
        if not tool_calls:
            return {
                "response": msg.content,
                "conversation_log": conversation_log
            }

        messages.append(msg)

        for tool_call in tool_calls:
            fn_name = tool_call.function.name
            raw_args = tool_call.function.arguments or "{}"
            fn_args = json.loads(raw_args)

            # Auto-add user_id where helpful
            if fn_name in ["get_user_preferences", "book_flight"] and "user_id" not in fn_args:
                fn_args["user_id"] = user_id

            conversation_log.append({
                "type": "tool_call",
                "function": fn_name,
                "arguments": fn_args
            })

            fn = available_functions[fn_name]
            fn_result = fn(**fn_args)

            conversation_log.append({
                "type": "tool_response",
                "function": fn_name,
                "response": fn_result
            })

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": fn_name,
                "content": json.dumps(fn_result)
            })

    return {
        "response": "Maximum tool-calling iterations reached.",
        "conversation_log": conversation_log
    }