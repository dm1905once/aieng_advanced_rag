from hstest import StageTest, TestedProgram, CheckResult, dynamic_test
import re
import os
import json

class RAGTest(StageTest):
    def after_all_tests(self):
        if os.path.exists("knowledge_base_clean_temp.json"):
            os.rename("knowledge_base_clean_temp.json", "knowledge_base_clean.json")

    @dynamic_test
    def test1_PreTestFileCheck(self):
        if os.path.exists("knowledge_base_clean.json"):
            os.rename("knowledge_base_clean.json", "knowledge_base_clean_temp.json")
        return CheckResult.correct()

    @dynamic_test
    def test2_RunCode(self):
        program = TestedProgram("main.py")
        output = program.start()
        if "knowledge_base_clean.json" not in os.listdir():
            return CheckResult.wrong("knowledge_base_clean.json was not created. Please check your code.")

        metadata = re.search(r"{.*}", output)
        if not metadata:
            return CheckResult.wrong(f"The output does not contain the metadata. Ensure that you are printing the metadata correctly.")

        tags = re.search(r"'tags': \[(.*?)\]", metadata.group(0))
        if not tags:
            return CheckResult.wrong(f"The output does not contain the tags. Ensure that you added the tags correctly.")
        category = re.search(r"'category': '(.*?)'", metadata.group(0))
        if not category:
            return CheckResult.wrong(f"The output does not contain the category. Ensure that you categorized the chunks correctly.")

        if not tags.group(1):
            return CheckResult.wrong(f"The tags are empty. Ensure that you added the tags correctly.")

        if not category.group(1):
            return CheckResult.wrong(f"The category is empty. Ensure that the category is set correctly.")

        tags = tags.group(1).split(", ")

        if not re.search(r"customer support", tags[0], re.IGNORECASE):
            return CheckResult.wrong(f"The documents do not contain the customer support tag. Found: {tags[0]}")
        if not re.search(r"live chat", tags[1], re.IGNORECASE):
            return CheckResult.wrong(f"The documents do not contain the live chat tag. Found: {tags[1]}")
        if not re.search(r"contact methods", tags[2], re.IGNORECASE):
            return CheckResult.wrong(f"The documents do not contain the contact methods tag. Found: {tags[2]}")

        if not re.search(r"support", category.group(1), re.IGNORECASE):
            return CheckResult.wrong(f"The documents do not contain the expected category. Found: {category.group(1)}")

        # verify that the number of qa chunks is greate than 15
        if not re.search(r"Number of qa chunks: \d+", output):
            return CheckResult.wrong("The output does not contain the number of entries found for FAQ documents. Please check your code.")
        num_qa_chunks = int(re.search(r"Number of qa chunks: (\d+)", output).group(1))
        if num_qa_chunks < 15:
            return CheckResult.wrong("The number of FAQ chunks is less than expected. Did you split the documents correctly into chunks?")
        # verify that the number of support chunks is less than 5
        if not re.search(r"Number of support chunks: \d+", output):
            return CheckResult.wrong("The output does not contain the number of entries found for support documents. Please check your code.")
        num_support_chunks = int(re.search(r"Number of support chunks: (\d+)", output).group(1))
        if num_support_chunks > 5:
            return CheckResult.wrong("Too many support chunks. Did you split the documents correctly into chunks?")
        # verify that the number of how-to chunks is less than 10
        if not re.search(r"Number of how-to chunks: \d+", output):
            return CheckResult.wrong("The output does not contain the number of entries found for how-to documents. Please check your code.")
        num_how_to_chunks = int(re.search(r"Number of how-to chunks: (\d+)", output).group(1))
        if num_how_to_chunks > 5:
            return CheckResult.wrong("Too many how-to chunks. Did you split the documents correctly into chunks?")
        # verify that the number of policy chunks is greater than 10
        if not re.search(r"Number of policy chunks: \d+", output):
            return CheckResult.wrong("The output does not contain the number of entries found for policy documents. Please check your code.")
        num_policy_chunks = int(re.search(r"Number of policy chunks: (\d+)", output).group(1))
        if num_policy_chunks < 10:
            return CheckResult.wrong("Too few policy chunks. Did you split the documents correctly into chunks?")

        return CheckResult.correct()

    @dynamic_test
    def test3_CheckFileNotEmpty(self):
        with open("knowledge_base_clean.json", "r") as file:
            data = file.read()
            if not data:
                return CheckResult.wrong("knowledge_base_clean.json is empty. Ensure that you are writing to the file correctly.")
        return CheckResult.correct()

    @dynamic_test
    def test4_CheckValidJSON(self):
        with open("knowledge_base_clean.json", "r") as file:
            try:
                json.load(file)
            except json.JSONDecodeError:
                return CheckResult.wrong("knowledge_base_clean.json is not a valid JSON file. Please check your code.")
        return CheckResult.correct()

    @dynamic_test
    def test5_CheckFileContent(self):
        with open("knowledge_base_clean.json", "r") as file:
            data = json.load(file)
            if "knowledge-base" not in data:
                return CheckResult.wrong("knowledge_base_clean.json does not contain the key 'knowledge-base'. Please check your code.")
            if not isinstance(data["knowledge-base"], list):
                return CheckResult.wrong("The value of 'knowledge-base' is not a list. Please check your code.")

            required_keys = ["question", "answer", "policy", "how-to", "support"]
            for entry in data["knowledge-base"]:
                if not any(key in entry for key in required_keys):
                    return CheckResult.wrong("The knowledge-base entries do not contain the expected keys. Please check your code.")

            for entry in data["knowledge-base"]:
                if "question" in entry and "answer" not in entry:
                    return CheckResult.wrong("The question key is present without the answer key. Please check your code.")
                if "answer" in entry and "question" not in entry:
                    return CheckResult.wrong("The answer key is present without the question key. Please check your code.")

            for entry in data["knowledge-base"]:
                if "policy" in entry and not isinstance(entry["policy"], str):
                    return CheckResult.wrong("The policy key is not a string. Please check your code.")
                if "how-to" in entry and not isinstance(entry["how-to"], list):
                    return CheckResult.wrong("The how-to key is not a list. Please check your code.")
                if "support" in entry and not isinstance(entry["support"], str):
                    return CheckResult.wrong("The support key is not a string. Please check your code.")

            unwanted_keys = ["meta", "scraped_at", "scrape_timestamp", "last_updated", "source_url", "referrer_url",
                             "user_agent", "debug_info", "geolocation", "misc"]
            for entry in data["knowledge-base"]:
                for key in unwanted_keys:
                    if key in entry:
                        return CheckResult.wrong(f"The entry contains an unwanted key: {key}. Ensure that the dataset only contains the required keys.")

            return CheckResult.correct()


if __name__ == '__main__':
    RAGTest().run_tests()