try:
    import json
    import itertools
    from selenium.webdriver import Chrome
    from selenium.webdriver.chrome.options import Options
    import time
    from bs4 import BeautifulSoup
    import os
    import shutil
    import uuid
    import boto3
    from datetime import datetime
    import datetime
    import ast
    import urllib3

    http = urllib3.PoolManager()

    print("All Modules are ok ...")

except Exception as e:

    print(f"Error in Imports {e}")

def get_existing_codes() -> list:
    print("Getting used codes...")
    try:
        client = boto3.client('ssm')
        response = client.get_parameter(Name="/sph/sw/used-codes-list")
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Error getting secret: {e}")
        return None
        
def write_to_ssm(existing_codes):
    print("Updating used codes...")
    try:
        client = boto3.client('ssm')
        response = client.put_parameter(
            Name='/sph/sw/used-codes-list',
            Description='SW used codes',
            Value=str(existing_codes),
            Type='String',
            Overwrite=True
        )
        return True
    except Exception as e:
        print(f"Error getting secret: {e}")
        return None
    
def get_valid_codes(used_codes):
    valid_codes = []
    existing_codes = used_codes
    try:
        url = "https://swq.jp/_special/rest/Sw/Coupon"
        
        querystring = {"results_per_page":"50"}
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "X-Requested-With": "XMLHttpRequest",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": "https://swq.jp/l/en-US/"
        }
        
        response = http.request("GET", url, fields=querystring, headers=headers)
        data = json.loads(response.data)
        for code in data['data']:
            rewards = []
            if code['Status'] == 'verified':
                for reward in code['Resources']:
                    reward_obj = [reward['Sw_Resource']['Code'],f'x{reward["Quantity"]}']
                    rewards.append(reward_obj)
                    #print(f"Reward: {reward['Sw_Resource']['Code']}x{reward['Quantity']}")
                reward_name = 'http://withhive.me/313/' + code['Label']
                code_obj = {'Coupon_code': reward_name, 'Code_rewards': rewards}
                if code['Label'] not in existing_codes:
                    existing_codes.append(code['Label'])
                    valid_codes.append(code_obj)
        return (valid_codes, existing_codes)
    except Exception as e:
        print(f"Failed due to {e}")
        return False
        
def invoke_discord_lambda(valid_codes):
    print(f"Invoking webooks")
    payload = {'codes': valid_codes}
    payload = json.dumps(payload)
    try:
        client = boto3.client('lambda')
        response = client.invoke(
            FunctionName=os.environ['DISCORD_LAMBDA'],
            InvocationType='RequestResponse',
            Payload=payload
        )
        return response
    except Exception as e:
        print(f"Error invoking lambda function: {e}")
        return False

def lambda_handler(event, context):
    existing_codes = get_existing_codes()
    existing_codes = ast.literal_eval(existing_codes)
    valid_codes, existing_codes = get_valid_codes(existing_codes)
    response = False
    if len(valid_codes) >= 1:
        response = invoke_discord_lambda(valid_codes)
    if response:
        write_to_ssm(existing_codes)
    print(valid_codes)
    return None
    


