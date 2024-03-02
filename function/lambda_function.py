import os
import json
import yaml
import asyncio
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import GPT4All
from langchain.globals import set_debug
from loguru import logger
import datetime
import requests
from collections import namedtuple
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

def init_vars():
    try:
        vars = {}
        init_env_vars(vars)
        init_time_vars(vars)
        return vars
    except Exception as e:
        logger.exception("init_vars failed: {}", e)
        raise e
    
def init_env_vars(vars):
    vars['bot_name'] = os.getenv("BOT_NAME", "Vecihi")
    vars['location'] = os.getenv("BOT_LOCATION", "Istanbul/Turkey")
    vars['context_file_url'] = os.getenv("CTX_FILE_URL")
    vars['bot_token'] = os.getenv("TELEGRAM_TOKEN")
    vars['echo_enabled'] = os.getenv("ECHO_ENABLED", "false")

    assert vars['bot_token']!=None, "TELEGRAM_TOKEN must be provided!"
    assert len(vars['bot_token'])>0, "TELEGRAM_TOKEN must be set!"

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
        logger.exception("init_config failed: {}", e)
        raise e

def init_gpt4all(cfg):
    try:
        prompt_template = PromptTemplate(template=cfg.prompt, input_variables=["bot_name", "location", "date", "time", "context", "message"])
        llm = GPT4All(model=cfg.model_file_name, 
                    verbose=True, 
                    temp=cfg.model.temp, 
                    n_predict = cfg.model.n_generate, 
                    top_p=cfg.model.top_p)
        return LLMChain(prompt=prompt_template, llm=llm)
    except Exception as e:
        logger.exception("init_gpt4all failed: {}", e)
        raise e

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm an AI based chatbot, ask questions to me in English!")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text

    if vars['echo_enabled'].lower()=='true':
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Echoed:"+message)
        return "done" 

    ctx_data = fetch_ctx_data() if vars['context_file_url'] else ""
    logger.info(f"New context data: {ctx_data}")
    
    prompt_input = get_prompt_input(ctx_data, message)
    response = llm_chain.invoke(prompt_input)
    logger.info(f"New response: {response}")

    await context.bot.send_message(chat_id=update.effective_chat.id, text=response['text'])

    return response

def init_ptb(vars):
    bot_token = vars['bot_token']
    application = ApplicationBuilder().token(bot_token).build()

    help_handler = CommandHandler('help', help)
    application.add_handler(help_handler)

    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), reply)
    application.add_handler(message_handler)

    return application

def get_prompt_input(context_data, question):
    return {"bot_name": vars['bot_name'], "location": vars['location'], "date": vars['date'], "time": vars['time'], "context": context_data, "question": question}

def fetch_ctx_data():
    return requests.get(vars['context_file_url'])

# set_debug(True)

### initialize the lambda function
logger.info("Function initialization started!")
config = init_config()
vars = init_vars()
llm_chain = init_gpt4all(config)
application = init_ptb(vars)
logger.info("Function initialization completed!")

def handler(event, context):
    return asyncio.run(handle_event(event))

async def handle_event(event):
    try:
        logger.info(f"New event: {event}")

        async with application:
            await asyncio.wait_for(application.process_update(Update.de_json(json.loads(event["body"]), application.bot)), timeout=config.handler_timeout)

        return {
            'statusCode': 200,
            'body': 'Success'
        }
    
    except asyncio.TimeoutError:
        logger.warn("handle_event expired")
        return {
            'statusCode': 200, # do not retry
            'body': 'Timeout'
        }
    except Exception as e:
        logger.exception("handle_event failed: {}", e)
        return {
            'statusCode': 200, # do not retry
            'body': 'Failure'
        }
    