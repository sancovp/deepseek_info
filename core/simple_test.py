from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

print("Testing connection to DeepSeek API...")
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Say hello"}],
    stream=False
)
print("Response:", response.choices[0].message.content)