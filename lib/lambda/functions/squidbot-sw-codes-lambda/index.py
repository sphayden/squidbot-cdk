try:
    import json
    from bs4 import BeautifulSoup
    import os
    import boto3
    import urllib3

    http = urllib3.PoolManager()

    print("All Modules are ok ...")

except Exception as e:

    print(f"Error in Imports {e}")

def validate_codes(code_links):
    valid_codes = []
    headers_mobile = { 'User-Agent' : 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B137 Safari/601.1'}
    for link in code_links:
        B_response = http.request('GET',link.get('Coupon_code'), headers=headers_mobile)
        B_soup = BeautifulSoup(B_response.data, 'html.parser')

        if B_soup.find_all("h1", {"class": "pop_tit"}):
            print(f'Invalid code link: {link}')
        else:
            valid_codes.append(link)
    return valid_codes
      
def get_active_codes() -> list:
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        
        table = dynamodb.Table(os.environ['SW_ACTIVE_CODES_TABLE'])
        
        response = table.scan()
        data_items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data_items.extend(response['Items'])
            
        return [data.get('code_id') for data in data_items]
    except  Exception as e:
        log_message = f"Error getting active codes: {e}"
        print(log_message)
        raise Exception(log_message)
        
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
        
def lambda_handler(event, context):
    existing_codes = get_active_codes('active_codes')
    #existing_codes = ast.literal_eval(existing_codes)
    new_codes, existing_codes = get_valid_codes(existing_codes)
    valid_codes = validate_codes(new_codes)
    response = {'codes': valid_codes}
    print(response)
    return response
    


