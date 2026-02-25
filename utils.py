def calculate_risk(attendance, marks, behavior):
    score = (100 - attendance) * 0.4 + (100 - marks) * 0.4 + (100 - behavior) * 0.2

    if score >= 60:
        return score, "HIGH"
    elif score >= 35:
        return score, "MEDIUM"
    else:
        return score, "LOW"
