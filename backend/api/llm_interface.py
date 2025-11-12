from openai import OpenAI


def call_openai_model(
    model: str, system_prompt: str, user_prompt: str, temperature: float = 0.0, **kwargs
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
