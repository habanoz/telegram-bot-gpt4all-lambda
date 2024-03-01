import os
import json
import yaml
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import GPT4All
from langchain.globals import set_debug
from loguru import logger
import datetime
import requests
from collections import namedtuple

def init_vars():
    try:
        vars = {}
        init_env_vars(vars)
        init_time_vars(vars)
        return vars
    except Exception as e:
        logger.error(f"init_vars failed: {e}")
        raise e
    
def init_env_vars(vars):
    vars['bot_name'] = os.getenv("BOT_NAME", "Vecihi")
    vars['location'] = os.getenv("BOT_LOCATION", "Istanbul/Turkey")
    vars['context_file_url'] = os.getenv("CTX_FILE_URL")

def init_time_vars(vars):
    now = datetime.datetime.now()
    vars['date'] = str(now.date())
    vars['time'] = now.strftime("%H:%M")

def read_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def dict_to_namedtuple(dict_obj):
    for key, value in dict_obj.items():
        if isinstance(value, dict):
            dict_obj[key] = dict_to_namedtuple(value)
    return namedtuple('GenericDict', dict_obj.keys())(*dict_obj.values())

def init_config():
    try:
        cfg = read_config()

        assert cfg != None, "Configuration object cannot be null"
        assert 'model_file_name' in cfg, "model_file_name configuration is not provided!"
        assert cfg['model_file_name'] != None, "model_file_name cannot be null!"
        assert os.path.exists(cfg['model_file_name']), f"File '{cfg['model_file_name']}' does not exist!"
        assert 'prompt' in cfg, "prompt configuration is not provided!"
        assert cfg['prompt'] != None, "prompt cannot be null!"
        
        return dict_to_namedtuple(cfg)
    except Exception as e:
        logger.error(f"init_config failed: {e}")
        raise e

def init_gpt4all(cfg):
    try:
        prompt_template = PromptTemplate(template=cfg.prompt, input_variables=["bot_name", "location", "date", "time", "context", "message"])
        llm = GPT4All(model=cfg.model_file_name, 
                    verbose=True, 
                    temp=cfg.model.temp, 
                    max_tokens=cfg.model.max_tokens, 
                    top_p=cfg.model.top_p)
        return LLMChain(prompt=prompt_template, llm=llm)
    except Exception as e:
        logger.error(f"init_gpt4all failed: {e}")
        raise e
    
# set_debug(True)

### initialize the lambda function
logger.info("Function initialization started!")
config = init_config()
vars = init_vars()
llm_chain = init_gpt4all(config)
logger.info("Function initialization completed!")

def get_prompt_input(context_data, question):
    return {"bot_name": vars['bot_name'], "location": vars['location'], "date": vars['date'], "time": vars['time'], "context": context_data, "question": question}

def fetch_ctx_data():
    return requests.get(vars['context_file_url']).text

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
        ctx_data = fetch_ctx_data() if vars['context_file_url'] else ""
        logger.info(f"New context data: {ctx_data}")

        prompt_input = get_prompt_input(ctx_data, message)
        response = llm_chain.invoke(prompt_input)
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

