from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import os
import uvicorn
import requests
from groq import Groq
from database import db_manager

app = FastAPI()

class Customer(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    country: Optional[str] = None
    # Qualification inputs
    goal: Optional[str] = None  # e.g., "Become an AI PM"
    budget: Optional[str] = None  # "company" | "self"
    webinar_join: Optional[datetime] = None
    webinar_leave: Optional[datetime] = None
    asked_q: Optional[bool] = None  # Spoke in chat during webinar
    referred: Optional[bool] = None  # Alumni or partner introduction
    past_touchpoints: Optional[int] = None  # Downloads, visits, interactions
    # Derived outputs
    engaged_mins: Optional[int] = None
    score: Optional[int] = None  # 0-100 qualification score
    reasoning: Optional[str] = None  # LLM explanation
    status: Optional[str] = None  # "Qualified" | "Nurture"
    address: Optional[str] = None

# --- Lead Qualification Engine ---
GROQ_MODEL = "llama-3.3-70b-versatile"

FEW_SHOT_PROMPT = '''You are a lead qualification expert for 100xEngineers, an applied AI education company.\nAnalyze customer data and assign a qualification score (0-100) with reasoning.\n\nEXAMPLES:\n\nCustomer: Sarah Chen\nGoal: "Become an AI Product Manager"  \nBudget: company\nEngagement: 90 minutes\nAsked Questions: Yes\nReferred: Yes\nPast Touchpoints: 3\nScore: 85\nReasoning: "Strong professional goal alignment with AI PM career track. Company budget indicates decision-making authority. High engagement (90 min) and active participation demonstrate genuine interest. Alumni referral validates fit with program."\nStatus: Qualified\n\nCustomer: John Smith  \nGoal: "Learn AI for hobby"\nBudget: self\nEngagement: 20 minutes  \nAsked Questions: No\nReferred: No\nPast Touchpoints: 0\nScore: 25\nReasoning: "Hobby-focused goal doesn't align with professional career outcomes. Short engagement (20 min) and no interaction suggest limited commitment. Self-funded with no referral indicates lower purchase intent."\nStatus: Nurture\n\nNow analyze this customer:\n'''

def get_engaged_minutes(join: Optional[datetime], leave: Optional[datetime]) -> Optional[int]:
    if join and leave:
        return int((leave - join).total_seconds() // 60)
    return None

def build_customer_prompt(customer: Customer) -> str:
    engaged_mins = get_engaged_minutes(customer.webinar_join, customer.webinar_leave)
    return f"Customer: {customer.name}\nGoal: {customer.goal}\nBudget: {customer.budget}\nEngagement: {engaged_mins if engaged_mins is not None else 'unknown'} minutes\nAsked Questions: {'Yes' if customer.asked_q else 'No'}\nReferred: {'Yes' if customer.referred else 'No'}\nPast Touchpoints: {customer.past_touchpoints if customer.past_touchpoints is not None else 0}"

def call_groq_llm(prompt: str) -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=GROQ_MODEL,
    )
    return chat_completion.choices[0].message.content

def parse_llm_response(llm_response: str):
    # Extract score, reasoning, status from LLM output
    import re
    score = None
    status = None
    reasoning = None
    score_match = re.search(r"Score:\s*(\d+)", llm_response)
    if score_match:
        score = int(score_match.group(1))
    status_match = re.search(r"Status:\s*([A-Za-z]+)", llm_response)
    if status_match:
        status = status_match.group(1)
    reasoning_match = re.search(r'Reasoning:\s*"([^"]+)"', llm_response)
    if reasoning_match:
        reasoning = reasoning_match.group(1)
    else:
        # fallback: get the first paragraph after 'Reasoning:'
        reasoning_match = re.search(r"Reasoning:\s*(.*?)(?:\n|$)", llm_response)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()
    return score, reasoning, status

def qualify_customer(customer: Customer) -> Customer:
    customer.engaged_mins = get_engaged_minutes(customer.webinar_join, customer.webinar_leave)
    prompt = FEW_SHOT_PROMPT + build_customer_prompt(customer)
    llm_response = call_groq_llm(prompt)
    score, reasoning, status = parse_llm_response(llm_response)
    customer.score = score
    customer.reasoning = reasoning
    customer.status = status
    return customer

@app.post("/customers/", response_model=Customer)
def create_customer(customer: Customer):
    qualified_customer = qualify_customer(customer)
    # Convert to dict for database storage
    customer_dict = qualified_customer.dict()
    created_customer = db_manager.create_customer(customer_dict)
    if not created_customer:
        raise HTTPException(status_code=500, detail="Failed to create customer")
    return Customer(**created_customer)

@app.get("/customers/", response_model=list[Customer])
def get_customers():
    customers_data = db_manager.get_all_customers()
    return [Customer(**customer) for customer in customers_data]

@app.put("/customers/{id}", response_model=Customer)
def update_customer(id: int, customer: Customer):
    # Check if customer exists
    existing_customer = db_manager.get_customer_by_id(id)
    if not existing_customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    qualified_customer = qualify_customer(customer)
    # Convert to dict for database storage
    customer_dict = qualified_customer.dict()
    updated_customer = db_manager.update_customer(id, customer_dict)
    if not updated_customer:
        raise HTTPException(status_code=500, detail="Failed to update customer")
    return Customer(**updated_customer)

@app.delete("/customers/{id}", response_model=Customer)
def delete_customer(id: int):
    # Check if customer exists
    existing_customer = db_manager.get_customer_by_id(id)
    if not existing_customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    deleted_customer = db_manager.delete_customer(id)
    if not deleted_customer:
        raise HTTPException(status_code=500, detail="Failed to delete customer")
    return Customer(**deleted_customer)

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port =7860)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port =7860)
