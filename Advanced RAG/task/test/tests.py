import os
import re

import dotenv
import psycopg
from hstest import StageTest, CheckResult, dynamic_test
from hstest import TestedProgram

dotenv.load_dotenv()
class RAGTest(StageTest):
    test_data = [
        ("I need to return a shirt", r"return|question|policy|shipping|return|refund|30|days"),
        ("I need to exchange a product", r"exchange|question|policy|shipping|exchange|refund|30|days"),
    ]

    # first check postgresql connection string
    @dynamic_test
    def test1_PostgresConnection(self):
        connection_string = os.getenv("PGVECTOR_CONNECTION_STRING")
        if not connection_string:
            return CheckResult.wrong("PGVECTOR_CONNECTION_STRING is not set. Please set it to your PostgreSQL connection string.")
        # attempt to extract the database name, user, host, and password from the connection string formatted at PGVECTOR_CONNECTION_STRING="postgresql+psycopg://hyper:hyper2025@localhost:5432/hyperdb"
        match = re.match(r"postgresql\+psycopg://(\w+):(\w+)@([\w.]+):(\d+)/(\w+)", connection_string)

        if not match:
            return CheckResult.wrong("PGVECTOR_CONNECTION_STRING is not in the correct format. Please set it to a valid PostgreSQL connection string.")
        user, password, host, port, dbname = match.groups()
        # create a connection string for psycopg
        conn_string = f"dbname={dbname} user={user} password={password} host={host} port={port}"
        # attempt to connect to the database
        try:
            conn = psycopg.connect(conn_string)
            conn.close()
        except psycopg.OperationalError as e:
            return CheckResult.wrong(f"Could not connect to the database. Encountered: {e}")
        except psycopg.DatabaseError as e:
            return CheckResult.wrong(f"Could not connect to the database. Encountered: {e}")

        except Exception as e:
            return CheckResult.wrong(f"Could not connect to the database. Encountered: {e}")
        return CheckResult.correct()

    @dynamic_test(time_limit=0)
    def test2_RunCode(self):
        for question, expected_output in self.test_data:
            program = TestedProgram("main.py")
            program.start()
            output = program.execute(question)

            if not re.findall(r"policy:|question:|answer:", output, re.IGNORECASE):
                return CheckResult.wrong(f"The output does not match the expected output. Please check your code.")
            if not re.findall(expected_output, output, re.IGNORECASE):
                return CheckResult.wrong(f"The output does not match the expected output. Please check your code.")

            metadata = re.search(r"{.*}", output)
            if not metadata:
                return CheckResult.wrong(f"The output does not contain the metadata. Please check your code.")

            tags = re.search(r"'tags': \[(.*?)\]", metadata.group(0))
            if not tags:
                return CheckResult.wrong(f"The output does not contain the tags. Please check your code.")
            category = re.search(r"'category': '(.*?)'", metadata.group(0))
            if not category:
                return CheckResult.wrong(f"The output does not contain the category. Please check your code.")

            relevance_score = re.search(r"'relevance_score': (.*?)}", metadata.group(0))
            if not relevance_score:
                return CheckResult.wrong(f"The output does not contain the relevance score. Did you use Cohere to rank the retrieved documents?")

            if not (0 <= float(relevance_score.group(1)) <= 1):
                return CheckResult.wrong(f"The relevance score is not between 0 and 1. Please check your code.")

            if not tags.group(1):
                return CheckResult.wrong(f"The tags are empty. Please check your code.")

            if not category.group(1):
                return CheckResult.wrong(f"The category is empty. Please check your code.")

            if not re.search(r"shipping|returns|privacy", tags.group(1), re.IGNORECASE):
                return CheckResult.wrong(f"The documents do not contain the expected tags. Please check your code.")

            if not re.search(r"policy|question|answer", category.group(1), re.IGNORECASE):
                return CheckResult.wrong(f"The documents do not contain the expected category. Please check your code.")

        return CheckResult.correct()


if __name__ == '__main__':
    RAGTest().run_tests()
