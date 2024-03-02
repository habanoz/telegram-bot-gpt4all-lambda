# Telegram Bot

This is a Telegram Chat Bot that is designed to work on AWS Lambda. GPT4ALL models are used to generate chat responses. This not a real chatbot because, chat history is not provided to the chat model. 

Lambda function is container based as opposed to an archive based function. Because container based lambda functions are more flexible.

Language model file is also included in the container which makes the container size big. (Using archive based functions would not help in this situation either). In order to not to send whole language model file each time source code is modified, docker file is designed to make use of layers e.g. source code file is copied later in the process. After the initial container creation, subsequent containers tagged with `--cache-from` option.


## Working With Container

Feel free to modify names to your preferences.

### Initialize

Start by downloading the model weights file.

```bash
wget -P model https://gpt4all.io/models/gguf/mistral-7b-instruct-v0.1.Q4_0.gguf
```

#### Build Container

Build the initial container.
```bash
docker build --platform linux/amd64 -t ptb-llm-mistral-instruct-q40:tag1 .
```

#### Push container to ECR

Login to ERC.
```bash
aws ecr get-login-password | docker login --username AWS --password-stdin <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com
```
Create repository
```bash
aws ecr create-repository --repository-name ptb-llm-lambda --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
```

Push to ECR Hub. Note that your endpoint maybe different according to the region you work. See references for a list of endpoints to choose from.
```bash
docker tag ptb-llm-mistral-instruct-q40:tag1 <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
docker push <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
```
Then create a lambda function using the container. After than you may create a lambda function URL.

### Update Container

#### Build updated Container

Build the initial container. `--cache-from` option is important to keep change delta small.
```bash
docker build --platform linux/amd64 -t ptb-llm-mistral-instruct-q40:tag2 --cache-from ptb-llm-mistral-instruct-q40:tag1 .
```

#### Push updated container to ECR

Login to ERC (Only if old login is expired).
```bash
aws ecr get-login-password | docker login --username AWS --password-stdin <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com
```

```bash
docker tag ptb-llm-mistral-instruct-q40:tag2 <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
docker push <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
```

## Local Testing

Before pushing latest changes it is recommend to make local testing.

Start container.
```bash
docker run -e TELEGRAM_TOKEN=<TELEGRAM_TOKEN> -p 9000:8080 ptb-llm-mistral-instruct-q40:tag1
```

Send test request. Note that **YOU NEED TO EDIT** `messages_event.json` file to include a valid chat definition, before you can apply this command:
```bash
curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d  @test/sample_events/message_event.json
```

For a chat definition, you may send a message to the bot and check aws lambda logs for the event definitions. It is best if you replace file content with the event definition from the logs. You may need to modify formatting of the event definition to have a valid json document.


## Telegram Configuration

Use the renowned BotFather to obtain a telegram token. 

Update telegram webhook (After obtaining a lambda function URL):
```bash
curl https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebHook?url=<LAMBDA_FUNCTION_URL>
```

Get web hook processing info e.g. last errors.
```bash
curl https://api.telegram.org/bot<TELEGRAM_TOKEN>/getWebHookInfo
```

### Cost Effectiveness

As of first quarter of 2024:

In my tests I used input prompts roughly 100 tokens and generated at most 100 tokens. Lambda execution times took up to 55 seconds, hard limit for execution time being 60 seconds, in an environment with 5500MB of memory and x64 architecture. 
This is roughly equivalent to having 200 tokens for a 60*5.5GB = 330GB-seconds execution time. Considering AWS lambda offers 400,000GB-seconds of free compute time per month, this is equivalent of processing 1200 requests and generating 120K tokens (240K tokens in total including input tokens).

What if we took another approach and utilized OpenAI GPT-3.5 Turbo for this purpose, which is a very efficient and capable model. Its price is $0.5/1M input tokens and $1.5/1M output tokens. Let's take average which means it costs $1/M input and output tokens. It costs a quarter of a dollar for the same amount of tokens (240K tokens), which is next to free.

Let's move forward and put it to scale. Let's consider moving to 1M tokens (input+output), which costs for $1 with GPT-3.5 Turbo. For the lambda function, we need 5000 executions to reach 1M tokens. According to AWS Lambda Pricing Calculator, 5000 executions on a x64 platform with a 5.5GB memory costs around $20 after deducing free usages. 

It may be possible to optimize lambda function to increase efficiency and decrease costs but when combined with cost and quality I do not see how it would be possible to beat GPT-3.5 Turbo. After all, AWS Lambda is not optimized for such loads and it is not surprising to see that it is not the best option. Also note that this study targets the telegram bot use case, other use cases may involve different dynamics and conclusions.

## References:
1- [List of OCI client endpoints for each region](https://docs.aws.amazon.com/general/latest/gr/ecr.html)
2- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
3- [AWS Lambda Pricing Calculator](https://s3.amazonaws.com/lambda-tools/pricing-calculator.html)