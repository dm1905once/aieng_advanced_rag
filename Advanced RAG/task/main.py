import json

def clean_input_file(path: str):
    questions = []
    policies = []
    steps = []
    supports = []
    with open(path, 'r') as file:
        input_file = json.load(file)
    for record in input_file['knowledge-base']:
        if "question" in record:
            questions.append(record)
        elif "policy" in record:
            policies.append(record)
        elif "steps" in record:
            steps.append(record)
        elif "policy" in record:
            supports.append(record)
    print(len(questions))

# Phase 1
clean_input_file('knowledge_base_noisy.json')