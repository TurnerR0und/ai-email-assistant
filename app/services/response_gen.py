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

    try:
        from openai import AsyncOpenAI
    except Exception as e:
        return f"Error: OpenAI client unavailable: {e}"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Error: OPENAI_API_KEY not set"

    client = AsyncOpenAI(api_key=api_key)
    prompt = PROMPT_TEMPLATE.render(subject=subject, body=body, category=category)

    try:
        with LLM_LATENCY.time():
            # CORRECTED API CALL for GPT-5 using the Responses API
            response = await client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-5-nano"),
                input=prompt,
                # As per the docs, nano is best for classification/instruction-following.
                # 'minimal' reasoning is a good default for speed.
                reasoning={"effort": "minimal"},
            )
        
        # The output from the Responses API is in the 'output_text' attribute
        content = getattr(response, "output_text", None)
        return content.strip() if content else "Error: Empty response from model"

    except Exception as e:
        return f"Error: Unable to get response from model: {str(e)}"