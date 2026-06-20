import json
from langchain_text_splitters import RecursiveJsonSplitter
from langchain_core.documents import Document

documents = []

def create_lang_document(doc_list: list, metadata: dict) -> int:
    chunks = [doc_list[i:i + 5] for i in range(0, len(doc_list), 5)]
    for chunk in chunks:
        documents.append(Document(
            page_content="\n".join(chunk),
            metadata=metadata
        ))
    return len(chunks)

def load_knowledge_base(path: str):
    questions = []
    policies = []
    steps = []
    supports = []
    clean_records = []

    # Clean and split file by type of entry
    with open(path, 'r') as file:
        input_file = json.load(file)
    for record in input_file['knowledge-base']:
        if "question" in record:
            questions.append(f"question: {record['question']}, answer: {record['answer']}")
            clean_records.append({"question": record["question"], "answer": record["answer"]})
        elif "policy" in record:
            policies.append(f"policy: {record['policy']}")
            clean_records.append({"policy": record["policy"]})
        elif "steps" in record:
            steps.append(f"'how-to': {record['steps']}")
            clean_records.append({"how-to" : record["steps"]})
        elif "support" in record:
            supports.append(f"'support': {record['support']}")
            clean_records.append({"support": record["support"]})

    # Create langchain docs with metadata, 5 entries of each type per doc
    # splitter = RecursiveJsonSplitter(max_chunk_size=3000)
    chunks_questions = create_lang_document(questions, {"category": "faq", "tags": ["frequently asked questions", "help", "general information"]})
    chunks_policies = create_lang_document(policies, {"category": "policy","tags": ["shipping", "returns", "privacy"]})
    chunks_steps = create_lang_document(steps, {"category": "how-to","tags": ["steps", "guides", "instructions"]})
    chunks_supports = create_lang_document(supports, {"category": "support", "tags": ["customer support", "live chat", "contact methods"]})


    # Save clean records into new json file
    clean_file = { "knowledge-base": clean_records}
    with open("knowledge_base_clean.json", "w") as file:
        json.dump(clean_file, file, indent=4)

    # Print details
    totals = f"""
    Number of qa chunks: {chunks_questions}
    Number of policy chunks: {chunks_policies}
    Number of how-to chunks: {chunks_steps}
    Number of support chunks: {chunks_supports}
    """
    print(totals)

    # Print documents
    for doc in documents:
        if doc.metadata["category"] == "support":
            print(doc.page_content)
            print(doc.metadata)

    for doc in documents:
        if doc.metadata["category"] == "faq":
            print(doc.page_content)
            print(doc.metadata)


    # [print(f"{doc.page_content}\n{doc.metadata}") for doc in documents if doc.metadata["category"] == "support"]
    # [print(f"{doc.page_content}\n{doc.metadata}") for doc in documents if doc.metadata["category"] == "faq"]


# Phase 1
load_knowledge_base('knowledge_base_noisy.json')