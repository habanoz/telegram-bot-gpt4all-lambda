# Telegram Bot

This is a Telegram Chat Bot that is designed to work on AWS Lambda. GPT4ALL models are used to generate chat responses. This not a real chatbot because, chat history is not provided to the chat model. 

Lambda function is container based as opposed to an archive based function. Because container based lambda functions are more flexible.

Language model file is also included in the container which makes the container size big. (Using archive based functions would not help in this situation either). In order to not to send whole language model file each time source code is modified, docker file is designed to make use of layers e.g. source code file is copied later in the process. After the initial container creation, subsequent containers tagged with `--cache-from` option.

## Initialize

Feel free to modify names to your preferences.

### Build Container


Build the initial container.
```bash
docker build --platform linux/amd64 -t ptb-llm-mistral-instruct-q40:tag1 .
```

### Push container to ECR

Login to ERC.
```bash
aws ecr get-login-password | docker login --username AWS --password-stdin <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com
```
Create repository
```bash
aws ecr create-repository --repository-name ptb-llm-lambda --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
```

```bash
docker tag ptb-llm-mistral-instruct-q40:tag1 <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
docker push <aws-user-id>.dkr.ecr.eu-west-2.amazonaws.com/ptb-llm-lambda:latest
```

[See for a list of OCI client endpoints for each region](https://docs.aws.amazon.com/general/latest/gr/ecr.html)
