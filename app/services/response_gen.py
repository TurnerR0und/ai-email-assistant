import os
from jinja2 import Template
from dotenv import load_dotenv
from prometheus_client import Histogram

LLM_LATENCY = Histogram(
    "llm_api_latency_seconds",
    "Time spent processing LLM API requests"
)

# Load environment only if not production
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

def load_prompt():
    with open("app/prompts/response.j2") as f:
        return Template(f.read())

PROMPT_TEMPLATE = load_prompt()

async def generate_response(subject: str, body: str, category: str) -> str:
    # Allow mocking to avoid network dependency and credentials in CI
    if os.getenv("APP_MOCK_AI") == "1" or os.getenv("MOCK_OPENAI") == "1":
        return f"[MOCK RESPONSE] Category={category}. Thank you for your message about '{subject}'."

    # Lazy import + client creation so tests/CI can run without openai installed
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        return f"Error: OpenAI client unavailable: {e}"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Error: OPENAI_API_KEY not set"

    client = OpenAI()  # Uses env OPENAI_API_KEY
    prompt = PROMPT_TEMPLATE.render(subject=subject, body=body, category=category)
    with LLM_LATENCY.time():
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-nano"),
            system="You are an expert support agent.",
            input=prompt,
        )
    # Prefer SDK helper when available
    content = getattr(response, "output_text", None)
    if content:
        return content.strip()
    # Fallback: try to navigate structured output
    try:
        first = response.output[0]
        part = first.content[0]
        text = getattr(part, "text", "") or part.get("text", "")
        return (text or "").strip()
    except Exception:
        return "Error: Unable to parse response from model"
