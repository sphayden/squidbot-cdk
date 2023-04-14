import webbrowser
from discord_webhook import DiscordWebhook, DiscordEmbed
import discord
from discord.ext import commands, tasks
import asyncio
import json
import boto3
import os
import ast


def get_webhooks():
    try:
        client = boto3.client('ssm')
        #param_path = os.environ['WEBHOOKS']
        response = client.get_parameter(Name="/sph/discord/webhooks")
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Error getting secret: {e}")
        return None

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

def send_codes(valid_codes, webhooks):

    codes = valid_codes
    
    webhook = DiscordWebhook(url=webhooks)
    
    for code in codes:
        for i, reward in enumerate(code['Code_rewards']):
            emoji = reward[0]
            emoji = (f"<:{emoji}:{get_emoji_value(emoji)}>")
            code['Code_rewards'][i][0] = str(emoji)
            code['Code_rewards'][i] = "".join(code['Code_rewards'][i])
            print(code['Code_rewards'][i])
        code['Code_rewards'] = "  ".join(code['Code_rewards'])
        embed = DiscordEmbed(title=f"{code['Coupon_code'].split('http://withhive.me/313/')[1]}", colour=0x4262F4)
        embed.set_thumbnail(url="https://sph-sw-bot-image-hosting.s3.us-east-2.amazonaws.com/sw.png")
        embed.add_embed_field(name="Code Link", value=code['Coupon_code'])
        embed.add_embed_field(name="Rewards", value=f"{code['Code_rewards']}")
        webhook.add_embed(embed)
    
    
    webhook.execute()


def lambda_handler(event, context):
    #event = json.loads(event)
    print(f"event: {event}")
    webhooks = ast.literal_eval(get_webhooks())
    send_codes(event['codes'], webhooks)
    return {
        "statusCode": 200,
        "body": {"message": "Hello World"}
    }
