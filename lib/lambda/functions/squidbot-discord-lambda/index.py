from discord_webhook import DiscordWebhook, DiscordEmbed
import discord
from discord.ext import commands, tasks
import asyncio
import json
import boto3
import os
import ast
import copy
import urllib3

def get_emoji_value(emoji_name):
    print(f":{emoji_name}:")
    try:
        db_table = os.environ['SW_REWARDS_TABLE']
        client = boto3.client('dynamodb')
        response = client.get_item(
            TableName=db_table,
            Key={
                'reward_name': {
                    'S': str(f":{emoji_name}:"),

                }
            }
        )
        print(response['Item']['emoji_value']['S'])
        return response['Item']['emoji_value']['S']
    except Exception as e:
        print(f"Error getting secret: {e}")
        return None

def send_codes(valid_code, webhooks):
    message_ids = []
    code = valid_code
    print(f"Sending code: {code}")
    webhook = DiscordWebhook(url=webhooks)
    
    
    for i, reward in enumerate(code['Code_rewards']):
        emoji = reward[0]
        emoji = (f"<:{emoji}:{get_emoji_value(emoji)}>")
        code['Code_rewards'][i][0] = str(emoji)
        code['Code_rewards'][i] = "".join(code['Code_rewards'][i])
        print(code['Code_rewards'][i])

    code['Code_rewards'] = "  ".join(code['Code_rewards'])
    embed = DiscordEmbed(title=f"{code['Coupon_code'].split('http://withhive.me/313/')[1]}", colour=0x4262F4)
    embed.set_thumbnail(url="https://sph-sw-bot-image-hosting.s3.us-east-2.amazonaws.com/sw-logo.png")
    embed.add_embed_field(name="Code Link", value=code['Coupon_code'])
    embed.add_embed_field(name="Rewards", value=f"{code['Code_rewards']}")
    webhook.add_embed(embed)

    response = webhook.execute()
    [print(res.json().get('webhook_id')) for res in response]
    [message_ids.append(
        {
            "message_id": id.json().get('id'),
            "webhook_id": id.json().get('webhook_id')
            
        }) for id in response]
    return message_ids
      
def get_webhooks() -> list:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    
    table = dynamodb.Table(os.environ['DISCORD_WEBHOOK_TABLE'])
    
    response = table.scan()
    data_items = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data_items.extend(response['Items'])
        
    return [data.get('webhook_id') for data in data_items]
    
def write_active_codes(code, message_ids):
    print(f"Writing to table: {code}: {message_ids}")
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        table = dynamodb.Table(os.environ['SW_ACTIVE_CODES_TABLE'])
        table.put_item(Item={'code_id': code, 'message_ids': message_ids})
    except Exception as e:
        log_message = f"Error writing to dynamo: {e}"
        print(log_message)
        raise Exception(log_message)
    
    
    
    
def lambda_handler(event, context):
    #event = json.loads(event)
    print(f"event: {event}")
    webhooks = get_webhooks()
    # webhooks = ast.literal_eval(get_webhooks())
    # webhooks = ["https://discord.com/api/webhooks/1002311639309230221/_dsqpxxGsnFo9yGtgHt_4FrNJMyRP1HOxXur18flgFGES6I4o-JXsEjuG1nSbY4E1wTs", "https://discord.com/api/webhooks/1096999076282781907/tkLR4ib33D4ZvCXWHLV2D1Gmy9itG9EqdVJBXqMYKF6S4EOtHmLtoMgbOb7kq9C2e6hh"]
    for code in event['codes']:
        response = send_codes(code, webhooks)
        write_active_codes(code.get('Coupon_code').split('http://withhive.me/313/')[1], response)
    return {
        "statusCode": 200,
        "body": {"message": 'finished'}
    }