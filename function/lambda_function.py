import os
import json
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import GPT4All
from langchain.globals import set_debug
from loguru import logger
import datetime
import requests

# set_debug(True)

bot_name = os.getenv("BOT_NAME", "Vecihi")
location = os.getenv("BOT_LOCATION", "Istanbul/Turkey")
context_file_url = os.getenv("CTX_FILE_URL")

now = datetime.datetime.now()
date = now.date()
time = now.strftime("%H:%M")

template = """[INST] You are {bot_name}, a friendly chatbot.
- Today is {date}
- Current time is {time}
- Your location is {location}
- You respect anyone and expect to be respected
- You do not like vulgar language
- You do not have access to realtime data
Use the provided context to answer the question.
Context:{context}
---
Question:{question} [/INST]"""

prompt = PromptTemplate(template=template, input_variables=["bot_name","location","date","time","context","message"])
local_path = ("./mistral-7b-instruct-v0.1.Q4_0.gguf")
llm = GPT4All(model=local_path, verbose=True, temp=0.7, max_tokens=2048, top_p=0.1)
llm_chain = LLMChain(prompt=prompt, llm=llm)


def get_prompt(context, question):
    return {"bot_name": bot_name, "location": location, "date": str(date), "time": str(time), "context": context, "question": question}


def handler(event, context):
    logger.info(f"New event: {event}")

    body = json.loads(event.get("body", "{}"))

    if "body" in body:
        body = body.get("body")
        body = json.loads(body)

    message = body.get("message")
    logger.info(f"New message: {message}")

    if message is None:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No message was provided'})
        }

    try:
        ctx = requests.get(context_file_url).text if context_file_url else ""
        logger.info(f"New context: {ctx}")

        response = llm_chain.invoke(get_prompt(ctx, message))
        logger.info(f"New response: {response}")

        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }

    except Exception as e:
        logger.error(f"Handling failed: {e}")

        return {
            'statusCode': 500,
            'body': json.dumps({'Internal Error': str(e)})
        }
