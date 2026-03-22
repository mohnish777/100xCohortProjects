

def calculate_score(inclusion_met, inclusion_total, exclusion_violated):
    if inclusion_total == 0:
        return 0
    
    inclusion_score = (inclusion_met/inclusion_total)*70
    exclusion_penalty = exclusion_violated*30

    final_score = max(0, inclusion_score - exclusion_penalty)

    return final_score

