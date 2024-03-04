# Telegram Bot

This is a Telegram Chat Bot that is designed to work on AWS Lambda. GPT4ALL models are used to generate chat responses. This is not a real chatbot because chat history is not provided to the chat model. 

A lambda function is container-based as opposed to an archive-based function. Because container-based lambda functions are more flexible.

Language model file is also included in the container which makes the container size big. (Using archive-based functions would not help in this situation either). To not send a whole language model file each time the source code is modified, the docker file is designed to make use of layers e.g. source code file is copied later in the process. After the initial container creation, subsequent containers are tagged with the `--cache-from` option.

## AWS CLI

Here are resources to prepare the AWS environment.

[Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

[Configure AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html)

[Using ECR with AWS CLI ](https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html)

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

Push to ECR Hub. Note that your endpoint may be different according to the region you work. See references for a list of endpoints to choose from.
```bash
docker tag ptb-llm-mistral-instruct-q40:tag1 <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
docker push <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
```
Then create a lambda function using the container. After that, you may create a lambda function URL.

### Update Container

#### Build updated Container

Build the initial container. `--cache-from` option is important to keep the change delta small.
```bash
docker build --platform linux/amd64 -t ptb-llm-mistral-instruct-q40:tag2 --cache-from ptb-llm-mistral-instruct-q40:tag1 .
```

#### Push updated container to ECR

Login to ERC (Only if the old login is expired).
```bash
aws ecr get-login-password | docker login --username AWS --password-stdin <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com
```

```bash
docker tag ptb-llm-mistral-instruct-q40:tag2 <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
docker push <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
```

## Local Testing

Before pushing the latest changes it is recommended to do local testing.

Start container.
```bash
docker run -e TELEGRAM_TOKEN=<TELEGRAM_TOKEN> -p 9000:8080 ptb-llm-mistral-instruct-q40:tag1
```

Send test request. Note that **YOU NEED TO EDIT** `messages_event.json` file to include a valid chat definition before you can apply this command:
```bash
curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d  @test/sample_events/message_event.json
```

For a chat definition, you may send a message to the bot and check AWS lambda logs for the event definitions. It is best if you replace file content with the event definition from the logs. You may need to modify the formatting of the event definition to have a valid JSON document.

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

As of the first quarter of 2024:

The selected model fits an environment with at least 5.5GB of memory. x64 architecture is selected. 10G disk space is allocated, not included in price calculations.

In my tests, I used input prompts for roughly 100 tokens and generated at most 100 tokens. Lambda execution times took up to 55 seconds, the hard limit for execution time was 60 seconds. 
This is roughly equivalent to having 200 tokens for a 60*5.5GB = 330GB-second execution time. Considering AWS lambda offers 400,000GB-seconds of free compute time per month, this is equivalent of processing 1200 requests and generating 120K tokens (240K tokens in total including input tokens).

What if we took another approach and utilized OpenAI GPT-3.5 Turbo for this purpose, which is a very efficient and capable model? Its price is $0.5/1M input tokens and $1.5/1M output tokens. Let's take the average which means it costs $1/M input and output tokens. It costs a quarter of a dollar for the same amount of tokens (240K tokens), which is next to free.

Let's move forward and put it to scale. Let's consider moving to 1M tokens (input+output), which costs $1 with GPT-3.5 Turbo. For the lambda function, we need 5000 executions to reach 1M tokens. According to AWS Lambda Pricing Calculator, 5000 executions on an x64 platform with 5.5GB memory cost around $20 after deducing free usage. 

It may be possible to optimize the lambda function to increase the efficiency and decrease the costs. Still, when combined with cost and quality I do not see how it would be possible for the studied configuration to beat the GPT-3.5-Turbo configuration. After all, AWS Lambda is not optimized for such loads and it is not surprising to see that it is not the best option. Also, note that this study targets the telegram bot use case, other use cases may involve different dynamics and conclusions.

#### Alternative Approach: Using GPT-3.5-Turbo

In light of these findings, a compelling alternative to the studied configuration is to utilize GPT-3.5-Turbo. A lambda function can make GPT-3.5-Turbo calls instead of using a local model. This can diminish memory requirements down to 1GB or less. Assuming GPT-3.5-Turbo will generate 100 tokens within 5 seconds, within this configuration, the AWS lambda function can process 80000 requests freely, per month. Within the same 100 tokens input and 100 tokens output schema, 80000 requests correspond to 1.6M tokens which costs only $1.6 per month.

This approach is much more scalable. Increasing prompt and completion lengths without worrying about lambda function limitations is possible.

## References:
1. [List of OCI client endpoints for each region](https://docs.aws.amazon.com/general/latest/gr/ecr.html)
2. [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
3. [AWS Lambda Pricing Calculator](https://s3.amazonaws.com/lambda-tools/pricing-calculator.html)
