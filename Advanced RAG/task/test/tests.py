import os
import re

import dotenv
import psycopg
from hstest import StageTest, CheckResult, dynamic_test

dotenv.load_dotenv()

class RAGTest(StageTest):
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

    # first check postgresql connection string
    @dynamic_test
    def test2_CheckOrders(self):
        connection_string = os.getenv("PGVECTOR_CONNECTION_STRING")

        match = re.match(r"postgresql\+psycopg://(\w+):(\w+)@([\w.]+):(\d+)/(\w+)", connection_string)
        user, password, host, port, dbname = match.groups()

        # create a connection string for psycopg
        conn_string = f"dbname={dbname} user={user} password={password} host={host} port={port}"
        # attempt to connect to the database and check if it has at least 3 tables
        try:
            conn = psycopg.connect(conn_string)
            cursor = conn.cursor()
            # check if the database has at least 3 tables
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
            count = cursor.fetchone()[0]
            if count < 3:
                return CheckResult.wrong(f"The database has less than 3 tables. Found: {count}")
            # check if the database has a table called 'orders'
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='orders';")
            count = cursor.fetchone()[0]
            if count == 0:
                return CheckResult.wrong("The database does not have a table called 'orders'.")

            # check if the orders table contains columns: 'Order Date', 'Order ID', 'Product ID', 'Product Name', 'Product Category', 'Purchase Address', 'Price Each'
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='orders';")
            columns = [row[0] for row in cursor.fetchall()]
            required_columns = ['Order Date', 'Order ID', 'Product ID', 'Product Name', 'Product Category', 'Purchase Address', 'Price Each']
            for column in required_columns:
                if column not in columns:
                    return CheckResult.wrong(f"The orders table does not have a column called '{column}'.")
            # check if the orders table contains at least 100 rows
            cursor.execute("SELECT COUNT(*) FROM orders;")
            count = cursor.fetchone()[0]
            if count < 100:
                return CheckResult.wrong(f"The orders table has too few rows. Found: {count}")
            conn.close()

        except psycopg.OperationalError as e:
            return CheckResult.wrong(f"Could not connect to the database. Encountered: {e}")
        except psycopg.DatabaseError as e:
            return CheckResult.wrong(f"Could not connect to the database. Encountered: {e}")

        except Exception as e:
            return CheckResult.wrong(f"Could not connect to the database. Encountered: {e}")
        return CheckResult.correct()

    @dynamic_test
    def test3_CheckEmbeddings(self):
        connection_string = os.getenv("PGVECTOR_CONNECTION_STRING")

        match = re.match(r"postgresql\+psycopg://(\w+):(\w+)@([\w.]+):(\d+)/(\w+)", connection_string)
        user, password, host, port, dbname = match.groups()

        # create a connection string for psycopg
        conn_string = f"dbname={dbname} user={user} password={password} host={host} port={port}"
        # attempt to connect to the database and check if it has at least 3 tables
        try:
            conn = psycopg.connect(conn_string)
            cursor = conn.cursor()

            # check if the database has a table called 'langchain_pg_embedding'
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='langchain_pg_embedding';")
            count = cursor.fetchone()[0]
            if count == 0:
                return CheckResult.wrong("The database does not have a table for embeddings. Did you use LangChain's PGVector wrapper?")

            # check if the database has a table called 'langchain_pg_collection'
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='langchain_pg_collection';")
            count = cursor.fetchone()[0]
            if count == 0:
                return CheckResult.wrong("The database does not have a table for collections. Did you use LangChain's PGVector wrapper?")

            # check if the langchain_pg_embedding table contains columns: 'embedding', 'document', 'id', 'collection_id', and 'cmetadata'
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='langchain_pg_embedding';")
            columns = [row[0] for row in cursor.fetchall()]
            required_columns = ['embedding', 'document', 'id', 'collection_id', 'cmetadata']
            for column in required_columns:
                if column not in columns:
                    return CheckResult.wrong(f"The LangChain embeddings table does not have a column called '{column}'. Did you use LangChain's PGVector wrapper?")
            conn.close()

        except psycopg.OperationalError as e:
            return CheckResult.wrong(f"Could not connect to the database. Encountered: {e}")
        except psycopg.DatabaseError as e:
            return CheckResult.wrong(f"Could not connect to the database. Encountered: {e}")

        except Exception as e:
            return CheckResult.wrong(f"Could not connect to the database. Encountered: {e}")
        return CheckResult.correct()


if __name__ == '__main__':
    RAGTest().run_tests()
