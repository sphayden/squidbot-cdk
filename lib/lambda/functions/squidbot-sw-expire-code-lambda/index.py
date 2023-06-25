import json
from bs4 import BeautifulSoup
import boto3
from datetime import datetime
import urllib3
import time
import os

http = urllib3.PoolManager()

print("All Modules are ok ...")


def get_webhooks() -> list:
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        
        table = dynamodb.Table(os.environ['DISCORD_WEBHOOK_TABLE'])
        
        response = table.scan()
        data_items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data_items.extend(response['Items'])
            
        return [data.get('webhook_id') for data in data_items]
    except Exception as e:
        log_message = f"Error getting webhooks: {e}"
        print(log_message)
        raise Exception(log_message)

def get_active_codes() -> list:
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        
        table = dynamodb.Table(os.environ['SW_ACTIVE_CODES_TABLE'])
        
        response = table.scan()
        data_items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data_items.extend(response['Items'])
            
        return data_items
    except  Exception as e:
        log_message = f"Error getting active codes: {e}"
        print(log_message)
        raise Exception(log_message)

def is_inactive(code: str) -> bool:
    try:
        formatted_link = f'http://withhive.me/313/{code}'
        headers_mobile = { 'User-Agent' : 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B137 Safari/601.1'}
        B_response = http.request('GET',formatted_link, headers=headers_mobile)
        B_soup = BeautifulSoup(B_response.data, 'html.parser')
        if B_soup.find_all("h1", {"class": "pop_tit"}):
            print(f'Expired Code: {formatted_link}')
            return True
        else:
            print(f'Active Code: {formatted_link}')
            return False
    except  Exception as e:
        log_message = f"Error checking code: {e}"
        print(log_message)
        raise Exception(log_message)
    
def expire_code(code: dict, webhooks: list) -> None:
    print(f"EXPIRE ME: {code}")
    try:
        #current_time = datetime.now().strftime("%B %d %Y %H:%M:%S %p")
        current_time = f"<t:{int(round(time.time()))}:f>"
        for i, message in enumerate(code.get('message_ids')):
            url = f'{webhooks[i]}/messages/{message}'
            print(f"Expiring message for {url}")
            http = urllib3.PoolManager()
            response = http.request('GET',url)
            data = json.loads(response.data)
            print(data)
            for i, embed in enumerate(data['embeds']):
                data['embeds'][i]['title'] = f"EXPIRED: {current_time}"
                data['embeds'][i]['thumbnail']['url'] = "https://sph-sw-bot-image-hosting.s3.us-east-2.amazonaws.com/sw-x.png"
            data_dump = json.dumps(data)
            print(type(data))
            response = http.request("PATCH", url, body=data_dump, headers={'Content-Type': 'application/json'})
            print(response.data)
    except Exception as e:
        log_message = f"Error updating expired message: {e}"
        print(log_message)
        raise Exception(log_message)
    
def delete_code_from_db(code: str) -> None:
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        
        table = dynamodb.Table(os.environ['SW_ACTIVE_CODES_TABLE'])
        
        table.delete_item(
            Key={
                'code_id': code
            }
        )
        print(f"Deleted Code: {code}")
    except  Exception as e:
        log_message = f"Error deleting expired code: {e}"
        print(log_message)
        raise Exception(log_message)

def update_code_in_db(code: str) -> None:
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        
        table = dynamodb.Table(os.environ['SW_EXPIRED_CODES_TABLE'])
        
        table.put_item(
            Item={
                'code_id': code,
                'expired_date': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
        )
        print(f"Put code in expired table: {code}")
    except Exception as e:
        log_message = f"Error updating expired code: {e}"
        print(log_message)
        raise Exception(log_message)

def lambda_handler(event, context):
    # Get Active Codes
    webhooks = get_webhooks()
    active_codes = get_active_codes()
    print(active_codes)
    for code in active_codes:
        if is_inactive(code.get('code_id')):
            expire_code(code, webhooks)
            delete_code_from_db(code.get('code_id'))
            update_code_in_db(code.get('code_id'))
            

    # Get Webhooks
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
