import json
import os
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_openai import ChatOpenAI
from langchain_cohere import CohereRerank
from langchain.tools import tool
from langchain.agents import create_agent

documents = []
load_dotenv()
api_key = os.getenv("LITELLM_API_KEY")
base_url = os.getenv("LITELLM_BASE_URL")
cohere_key = os.getenv("COHERE_API_KEY")
db_connection = os.getenv("PGVECTOR_CONNECTION_STRING")

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

def get_hyde_template() -> str:
    return  """For the given question try to generate a hypothetical answer
    Question: {question}
    Generate 5 hypothetical answers in one or more of the following categories, giving more weight to policy than questions:
        1. Question-Answer, expanding on similar questions the user may have
            Example:
                question: similarly worded question
                answer: provide a relevant answer
        2. Policy, explaining an existing policy that would answer the question
            Example:
                policy: describe a policy that would answer the question
        3. How-to, describing steps to perform an action that would resolve the question
            Example:
                how-to: ["step 1 to resolve the question", "step 2 to resolve the question"]
        4. Support, to describe helpful support answers to other similar problems
            Example:
                support: support can be reached from Monday-Friday to resolve the question
    Important: do not print the results as a list or formatted text. Only print one answer per line. Do not leave blank lines between the answers.
    """

def generate_hydes(question: str, top_n: int, print_output: bool = False):
    llm = get_llm()
    vector_store = get_vector_store()

    # Generate hypothetical question
    template = get_hyde_template()
    prompt = ChatPromptTemplate.from_template(template)
    query = prompt.format(question=question)
    hypothetical_answer = llm.invoke(query).content
    print(f"Hypothetical Document:\n{hypothetical_answer}")

    # Retrieve from the vector using the hypothetical question as input
    retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": top_n})
    contexts = retriever.invoke(str(hypothetical_answer))
    if print_output:
        print("Contexts")
        for context in contexts:
            print(context.page_content)
            print(context.metadata)

@tool
def rerank_context(question: str, top_n: int = 2, print_output: bool = False) -> list:
    """
    Search the vector knowledgebase for chunks of relevant context that would help answer a user's question
    :param question: user question
    :param top_n: number of relevant chunks to return
    :param print_output: print output to console or not
    :return: list with relevant chunks
    """
    llm = get_llm()
    vector_store = get_vector_store()
    relevant_context = []

    # Generate hypothetical question
    template = get_hyde_template()
    prompt = ChatPromptTemplate.from_template(template)
    query = prompt.format(question=question)
    hypothetical_answer = llm.invoke(query).content
    if print_output:
        print(f"Hypothetical Document:\n{hypothetical_answer}")

    # Retrieve from the vector using the hypothetical question as input
    retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": top_n})
    contexts = retriever.invoke(str(hypothetical_answer))
    if print_output:
        print("\nContexts:")
        for context in contexts:
            print(context.page_content)
            # print(context.metadata)

    # Re-rank chunks by relevance score, using Cohere's re-ranker
    reranker = CohereRerank(
        model="rerank-english-v3.0",
        cohere_api_key=cohere_key
    )

    compressed_contexts = reranker.rerank(
        documents=contexts,
        query=query,
        top_n=top_n
    )

    for compressed_context in compressed_contexts:
        relevant_context.append(contexts[compressed_context["index"]].page_content)

    if print_output:
        print("\nCompressed Contexts:")
        for compressed_context in compressed_contexts:
            # print(compressed_context)
            index = compressed_context["index"]
            contexts[index].metadata.update({'relevance_score': compressed_context['relevance_score']})
            print(contexts[index].page_content)
            print(contexts[index].metadata)

    return relevant_context

@tool
def query_orders_table(query: str):
    """
    Connects to the orders table to retrieve records associated to orders
    :param query: SQL query
    :return: query output

    The orders table contains the following columns:
    "Order Date" DATE,
    "Order ID" VARCHAR(10) NOT NULL,
    "Product ID" VARCHAR(10),
    "Product Name" VARCHAR(60),
    "Product Category" VARCHAR(60),
    "Purchase Address" VARCHAR(60),
    "Price Each" NUMERIC(10, 2)
    """
    db = SQLDatabase.from_uri(db_connection)
    return db.run(query)


# Phase 1
#load_knowledge_base('knowledge_base_noisy.json', False)

# Phase 2
# embed_and_store()

# Phase 3
#query(input())

# Phase 4
# context = generate_hydes(input(), 2)

# Phase 5
#rerank_context(input(), 10, False)

# Phase 6

agent = create_agent(
    model=get_llm(),
    tools=[rerank_context, query_orders_table],
    system_prompt="""
    You are a helpful agent that takes users questions and always responds with at least one relevant answer by searching the knowledgebase or querying the orders table
    """
)

inputs = {"messages": [{"role": "user", "content": input()}]}
chunks = agent.invoke(inputs, stream_mode="values")
messages = chunks['messages']
for message in messages:
    # if hasattr(message, "tool_calls") and message.tool_calls:
    #     print(message.tool_calls)
    if hasattr(message, "content") and message.content:
        if "(datetime.date(2025, 4, 15)" in message.content:
            print(message.content.replace("datetime.date(2025, 4, 15), ", "datetime.date(2025415), "))
        else:
            print(message.content)