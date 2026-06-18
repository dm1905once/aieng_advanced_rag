import json

def clean_input_file(path: str):
    questions = []
    policies = []
    steps = []
    supports = []
    clean_records = []

    with open(path, 'r') as file:
        input_file = json.load(file)
    for record in input_file['knowledge-base']:
        clean_record = None
        if "question" in record:
            clean_record = {"question": record["question"], "answer": record["answer"]}
            questions.append(clean_record)
        elif "policy" in record:
            clean_record = {"policy": record["policy"]}
            policies.append(clean_record)
        elif "steps" in record:
            clean_record = {"how-to" : record["steps"]}
            steps.append(clean_record)
        elif "support" in record:
            clean_record = {"support": record["support"]}
            supports.append(clean_record)
        if clean_record:
            clean_records.append(clean_record)

    clean_file = { "knowledge-base": clean_records}
    with open("knowledge_base_clean.json", "w") as file:
        json.dump(clean_file, file, indent=4)


# Phase 1
clean_input_file('knowledge_base_noisy.json')