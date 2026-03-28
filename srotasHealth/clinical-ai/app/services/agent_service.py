

from app.schemas.patient_schema import Patient
from app.services.ai_matching import ai_match


def run_matching_agent(trial, patients):
    results = []

    for patient_data in patients:
        patient = Patient(**patient_data)
        result = ai_match(trial, patient)

        # Debug: print what the LLM returned
        print(f"Patient age {patient.age}: score={result.get('score')}, eligible={result.get('eligible')}")
        
        results.append({
            "patient": patient,
            "score": result.get("score", 0),
            "eligible": result.get("eligible", False),
            "reasons": result.get("reasons", [])
        })
    
    print("results agent service:", results)

    top_matches = [r for r in results if r["score"]>70 and r["eligible"]]
    #sort by score
    top_matches.sort(key=lambda x: x["score"], reverse=True)

    return top_matches