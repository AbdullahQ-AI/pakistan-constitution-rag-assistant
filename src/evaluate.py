"""
evaluate.py
Automated evaluation of the RAG pipeline against a fixed test set.
Checks whether expected Article numbers appear in each answer, and
reports pass/fail with a summary accuracy score.
"""

import time
from qa_chain import load_vectorstore, load_article_index, load_page_index, build_llm, answer_question

# Each test case: (question, list of article numbers that MUST appear
# in a correct answer, or None if it's a loosely-checked case)
TEST_CASES = [
    ("What is Article 25 about?", ["25"]),
    ("What does Article 19 say?", ["19"]),
    ("What is Article 9 about?", ["9"]),
    ("Explain Article 199.", ["199"]),
    ("What does Article 6 say?", ["6"]),
    ("What is Article 62 about?", ["62"]),
    ("What does Article 175 say?", ["175"]),
    ("What are the fundamental rights guaranteed to citizens?", ["9", "25"]),
    ("How can the Constitution be amended?", ["238", "239"]),
    ("Who can become Prime Minister of Pakistan?", ["91"]),
    ("What are the qualifications to become a member of the National Assembly?", ["62"]),
    ("What is the role of the Supreme Court?", ["175"]),
    ("What is the process for removing the President?", ["47"]),
    ("Can the government restrict freedom of speech?", ["19"]),
    ("How is the Chief Justice appointed?", None),  # loosely checked
    ("What rights do religious minorities have?", ["20", "21", "22"]),
]

OFF_TOPIC_CASES = [
    "What is Article 500 about?",
    "What does the Constitution say about cryptocurrency regulations?",
    "Who won the 2024 general election?",
    "What's a good recipe for biryani?",
]

REFUSAL_PHRASES = ["couldn't find", "not able to help", "designed specifically"]

DELAY_SECONDS = 13  # stay under free-tier rate limit (5 requests/minute)


def run_citation_tests(vectorstore, llm, article_index, page_index):
    print("\n" + "=" * 60)
    print("CITATION ACCURACY TESTS")
    print("=" * 60)
    passed = 0
    for question, expected_articles in TEST_CASES:
        time.sleep(DELAY_SECONDS)
        answer, _ = answer_question(question, vectorstore, llm, article_index, page_index)
        if expected_articles is None:
            print(f"~SKIP  {question}")
            continue
        found = any(f"Article {num}" in answer or f"**Article {num}" in answer for num in expected_articles)
        status = "PASS" if found else "FAIL"
        if found:
            passed += 1
        print(f"{status}  {question}")
        if not found:
            print(f"      Expected one of: {expected_articles}")
    total = len([t for t in TEST_CASES if t[1] is not None])
    print(f"\nCitation accuracy: {passed}/{total} ({passed/total*100:.0f}%)")
    return passed, total


def run_refusal_tests(vectorstore, llm, article_index, page_index):
    print("\n" + "=" * 60)
    print("OFF-TOPIC REFUSAL TESTS")
    print("=" * 60)
    passed = 0
    for question in OFF_TOPIC_CASES:
        time.sleep(DELAY_SECONDS)
        answer, _ = answer_question(question, vectorstore, llm, article_index, page_index)
        declined = any(phrase in answer.lower() for phrase in REFUSAL_PHRASES)
        status = "PASS" if declined else "FAIL"
        if declined:
            passed += 1
        print(f"{status}  {question}")
    total = len(OFF_TOPIC_CASES)
    print(f"\nRefusal accuracy: {passed}/{total} ({passed/total*100:.0f}%)")
    return passed, total


if __name__ == "__main__":
    print("Loading pipeline...")
    vectorstore = load_vectorstore()
    article_index = load_article_index()
    page_index = load_page_index()
    llm = build_llm()

    cite_passed, cite_total = run_citation_tests(vectorstore, llm, article_index, page_index)
    refuse_passed, refuse_total = run_refusal_tests(vectorstore, llm, article_index, page_index)

    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    total_passed = cite_passed + refuse_passed
    total_tests = cite_total + refuse_total
    print(f"Total: {total_passed}/{total_tests} ({total_passed/total_tests*100:.0f}%)")