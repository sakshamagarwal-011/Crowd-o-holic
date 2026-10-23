import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

hf_token = os.getenv("HF_TOKEN")
model = os.getenv("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")

if not hf_token:
    raise RuntimeError("HF_TOKEN is not set in .env")

client = InferenceClient(api_key=hf_token)


def test_connection():
    try:
        response = client.chat_completion(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Hello Hugging Face! Are you connected?"
                }
            ],
            max_tokens=50,
            temperature=0.2
        )

        print("✅ Connection successful!")
        print("Model:", model)
        print("Response:", response.choices[0].message.content)

    except Exception as e:
        print("❌ Connection failed!")
        print("Error:", e)


if __name__ == "__main__":
    test_connection()