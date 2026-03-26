from openai import OpenAI

client = OpenAI(
  base_url="https://zenmux.ai/api/v1",
  api_key="sk-ai-v1-e7d3e7253fd487ea49ffc26e826c2ab4e3feb90fe9ab7057ee74d9d5766e235b",
)

# # Chat Completion
# completion = client.chat.completions.create(
#   model="sapiens-ai/agnes-1.5-pro",
#   messages=[
#     {
#       "role": "user",
#       "content": "你是谁?"
#     }
#   ]
# )
# print(completion.choices[0].message.content)

# Responses API
responses = client.responses.create(
  model="sapiens-ai/agnes-1.5-pro",
  input="你是谁?"
)
print(responses)
