import * as cdk from 'aws-cdk-lib';
import { aws_s3 as s3, aws_lambda as lambda, aws_iam as iam, Tags, aws_ssm as ssm} from 'aws-cdk-lib';
import {aws_dynamodb as dynamodb} from 'aws-cdk-lib';
import { aws_events as events, aws_events_targets as targets } from 'aws-cdk-lib';
import { DynamoPutItem } from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { custom_resources as cr } from 'aws-cdk-lib';
import { AwsCustomResource } from 'aws-cdk-lib/custom-resources';
export class SquidbotCdkStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    // SSM Parameter for webhook URLS
    // const SquidbotDiscordWebhooks = ssm.StringParameter.fromStringParameterAttributes(this, 'SSMValue', {
    //   parameterName: '/sph/discord/webhooks',
    //   // 'version' can be specified but is optional.
    // }).stringValue;

    // DynamoDB Table for Squidbot
    const SquidbotDynamoDBTable = new dynamodb.Table(this, 'SquidbotRewardsMappingTable', {
      partitionKey: {
        name: 'reward_name',
        type: dynamodb.AttributeType.STRING,
      }
    });
    Tags.of(SquidbotDynamoDBTable).add('project', 'squidbot');


    // IAM for Squidbot
    const SquidbotLambdaRole = new iam.Role(this, 'SquidbotLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: []

    });
    Tags.of(SquidbotLambdaRole).add('project', 'squidbot');

    SquidbotLambdaRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaRole'));
    SquidbotLambdaRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonDynamoDBFullAccess'));
    SquidbotLambdaRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMFullAccess'));
    SquidbotLambdaRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AWSLambdaExecute'));

    // Lambda for Squidbot
    const SquidbotDiscordLayer = new lambda.LayerVersion(this, 'SquidbotDiscordLayer', {
      code: lambda.Code.fromAsset('./lib/lambda/layers/squidbot-discord-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
      description: 'Layer for sending webhooks to Discord',
    });
    Tags.of(SquidbotDiscordLayer).add('project', 'squidbot');

    const SquidbotDiscordLambda = new lambda.Function(this, 'SquidbotSWDiscordFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset('./lib/lambda/functions/squidbot-discord-lambda'),
      layers: [SquidbotDiscordLayer],
      role: SquidbotLambdaRole,
      timeout: cdk.Duration.seconds(300),
      environment: {
        'SW_REWARDS_TABLE': SquidbotDynamoDBTable.tableName
      }
    });
    Tags.of(SquidbotDiscordLambda).add('project', 'squidbot');

    const bs4_layer = new lambda.LayerVersion(this, 'SquidbotBS4Layer', {
      code: lambda.Code.fromAsset('./lib/lambda/layers/squidbot-bs4-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_7],
      description: 'Layer for scraping sw cods',
    });
    Tags.of(bs4_layer).add('project', 'squidbot');

    const scraping_layer = lambda.LayerVersion.fromLayerVersionArn(this, 'SquidbotScrapingLayer', 'arn:aws:lambda:us-east-2:682620560068:layer:selenium_chrome:1');

    const SquidbotScrapingLambda = new lambda.Function(this, 'SquidbotSWTokenFunction', {
      runtime: lambda.Runtime.PYTHON_3_7,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset('./lib/lambda/functions/squidbot-sw-codes-lambda'),
      layers: [scraping_layer, bs4_layer],
      role: SquidbotLambdaRole,
      timeout: cdk.Duration.seconds(300),
      environment: {
        'DISCORD_LAMBDA': SquidbotDiscordLambda.functionName
      }
      
    });
    Tags.of(SquidbotScrapingLambda).add('project', 'squidbot');

    // Events for Squidbot
    const SquidbotEvents = new events.Rule(this, 'SquidbotTriggerTokenLambdaEvent', {
      schedule: events.Schedule.rate(cdk.Duration.hours(2)),
    });
    Tags.of(SquidbotEvents).add('project', 'squidbot');

    SquidbotEvents.addTarget(new targets.LambdaFunction(SquidbotScrapingLambda));
  }
}

const app = new cdk.App();

const myStack = new SquidbotCdkStack(app, 'squidbot-cdk-stack',{
  tags: {
    project: 'squidbotv2'
  }
});
