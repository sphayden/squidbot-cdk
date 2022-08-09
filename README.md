# SquidBot-cdk
<h3>CDK app to deploy infrastructure for automatically posting Summoners War codes to discord.</h3>

Uses Discord webhooks to post embeds with the reward info taken from https://swq.jp/l/en-US/. Embed look like this ![Embed example](example-images/squidbot-example.jpg)


<h1>Infrastructure Info</h1>

The infrastructure for this application is hosted on AWS and uses the [AWS CDK](https://aws.amazon.com/cdk/) to deploy and update it programatically. 

Total costs for this app depends on how often the EventBridge event is set to trigger but can easily be less than $1 a month.
