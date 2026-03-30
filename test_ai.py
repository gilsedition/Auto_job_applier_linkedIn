import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from modules.ai.openaiConnections import ai_create_openai_client, ai_extract_skills, ai_answer_question

print("Creating client...")
client = ai_create_openai_client()
print("CLIENT OK")

print("\n--- Testing extract_skills (JSON) ---")
result = ai_extract_skills(client, "Finance analyst role. Requires Excel, SAP, 3 years accounting experience, strong communication skills.")
print("SKILLS TYPE:", type(result).__name__)
if isinstance(result, dict):
    print("SKILLS KEYS:", list(result.keys()))
    print("PASS" if "error" not in result else f"FAIL: {result}")
else:
    print("FAIL: not a dict:", result)

print("\n--- Testing ai_answer_question (text) ---")
ans = ai_answer_question(client, "How many years of accounting experience do you have?", question_type="text", job_description="Finance analyst role", user_information_all="Name: Sharon Dmello. 4 years accounting experience.")
print("ANSWER:", ans)
print("PASS" if ans and "4" in ans else "WARN: answer doesn't contain '4'")
