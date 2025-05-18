import os
from openai import OpenAI
from jinja2 import Template
from dotenv import load_dotenv

# Load environment only if not production
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

# Access your environment variables safely
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY not set. Please check .env")
client = OpenAI()  # Assumes OPENAI_API_KEY is set

def load_prompt():
    with open("app/prompts/response.j2") as f:
        return Template(f.read())

PROMPT_TEMPLATE = load_prompt()

async def generate_response(subject: str, body: str, category: str) -> str:
    prompt = PROMPT_TEMPLATE.render(subject=subject, body=body, category=category)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert support agent."},
            {"role": "user", "content": prompt},
        ]
    )
    return response.choices[0].message.content.strip()
