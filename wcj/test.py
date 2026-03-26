from openai import OpenAI

client = OpenAI(
  base_url="https://zenmux.ai/api/v1",
  api_key="sk-ai-v1-e7d3e7253fd487ea49ffc26e826c2ab4e3feb90fe9ab7057ee74d9d5766e235b",
)

completion = client.chat.completions.create(
  model="kuaishou/kat-coder-pro-v1-free",
  messages=[
    {
      "role": "user",
      "content": "你是谁?"
    }
  ]
)
print(completion.choices[0].message.content)

# Responses API
# responses = client.responses.create(
#   model="kuaishou/kat-coder-pro-v1-free",
#   input="你是谁?"
# )
# print(responses)
