from openai import OpenAI
import json


def call_openai_model(
    model: str, system_prompt: str, user_prompt: str, temperature: float = 1.0, **kwargs
) -> str:
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        **kwargs,
    )
    return response.choices[0].message.content


def call_model_with_json_response(
    system_prompt, user_prompt, retries=5, temperature=1.0
):
    for _ in range(retries):
        try:
            result = call_openai_model(
                model="gpt-5",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            return json.loads(result)
        except Exception as e:
            print(f"Error calling model: {e}")
    return None
