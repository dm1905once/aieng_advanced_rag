import json
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_openai import ChatOpenAI


documents = []
load_dotenv()
api_key = os.getenv("LITELLM_API_KEY")
base_url = os.getenv("LITELLM_BASE_URL")

def create_lang_document(doc_list: list, metadata: dict) -> int:
    chunks = [doc_list[i:i + 5] for i in range(0, len(doc_list), 5)]
    for chunk in chunks:
        documents.append(Document(
            page_content="\n".join(chunk),
            metadata=metadata
        ))
    return len(chunks)

def load_knowledge_base(path: str, print_output: bool):
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
    if print_output:
        print(totals)

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



def get_vector_store() ->PGVector:
    connection = os.getenv("PGVECTOR_CONNECTION_STRING")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=api_key,
        base_url=base_url
    )
    collection_name = "knowledge_base"

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection,
        use_jsonb=True,
    )
    return vector_store

def embed_and_store():
    vector_store = get_vector_store()
    vector_store.add_documents(documents)

def get_llm(model="gpt-4o-mini") ->ChatOpenAI:
    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url
    )
    return llm

def query(question: str):
    vector_store = get_vector_store()
    llm = get_llm()
    messages = [
            {
                "role": "system",
                "content": """
                    You are a support assistant facilitating access to a knowledgebase.
                    For each user question , you need to decompose the question and provide 3 additional possible related questions that the human might ask next.
                    The format of the output is one JSON object. 
                    Example:
                       {"additional_questions" : ["question 1","question 2","question 3"]}
                """
            },
            {
                "role": "user",
                "content": question
            }
    ]
    response = llm.invoke(messages)
    responses= json.loads(str(response.text))
    for question in responses["additional_questions"]:
        retrieved_docs = vector_store.similarity_search(question, k=2)
        serialized = "\n\n".join(
            (f"{doc.page_content}\n{doc.metadata}\n") for doc in retrieved_docs
        )
        print(f"Question: {question}")
        print(serialized)


# Phase 1
#load_knowledge_base('knowledge_base_noisy.json', False)

# Phase 2
# embed_and_store()

# Phase 3
query(input())