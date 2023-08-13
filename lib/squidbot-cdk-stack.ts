import * as cdk from 'aws-cdk-lib';
import {  aws_stepfunctions as sfn, aws_stepfunctions_tasks as tasks, aws_s3 as s3, aws_lambda as lambda, aws_iam as iam, Tags, aws_ssm as ssm} from 'aws-cdk-lib';
import {aws_dynamodb as dynamodb} from 'aws-cdk-lib';
import { aws_events as events, aws_events_targets as targets } from 'aws-cdk-lib';
import { DynamoPutItem } from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { custom_resources as cr } from 'aws-cdk-lib';
import { AwsCustomResource } from 'aws-cdk-lib/custom-resources';
export class SquidbotCdkStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    // DynamoDB Tables for Squidbot
    const SquidbotDiscordWebhookDynamoTable = new dynamodb.Table(this, 'SquidbotDiscordWebhookTable', {
      partitionKey: {
        name: 'webhook_id',
        type: dynamodb.AttributeType.STRING,
      }
    });
    Tags.of(SquidbotDiscordWebhookDynamoTable).add('project', 'squidbot');

    const SquidbotActiveCodeDynamoTable = new dynamodb.Table(this, 'SquidbotActiveCodeTable', {
      partitionKey: {
        name: 'code_id',
        type: dynamodb.AttributeType.STRING,
      }
    });
    Tags.of(SquidbotActiveCodeDynamoTable).add('project', 'squidbot');

    const SquidbotExpiredCodeDynamoTable = new dynamodb.Table(this, 'SquidbotExpiredCodeTable', {
      partitionKey: {
        name: 'code_id',
        type: dynamodb.AttributeType.STRING,
      }
    });
    Tags.of(SquidbotExpiredCodeDynamoTable).add('project', 'squidbot');

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

    const SquidbotRequestsLayer = new lambda.LayerVersion(this, 'SquidbotRequestsLayer', {
      code: lambda.Code.fromAsset('./lib/lambda/layers/squidbot-requests-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
      description: 'Layer for using requests',
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
        'SW_REWARDS_TABLE': SquidbotDynamoDBTable.tableName,
        'DISCORD_WEBHOOK_TABLE': SquidbotDiscordWebhookDynamoTable.tableName,
        'SW_ACTIVE_CODES_TABLE': SquidbotActiveCodeDynamoTable.tableName,
        'SW_EXPIRED_CODES_TABLE': SquidbotExpiredCodeDynamoTable.tableName,
      }
    });
    Tags.of(SquidbotDiscordLambda).add('project', 'squidbot');

    const bs4_layer = new lambda.LayerVersion(this, 'SquidbotBS4Layer', {
      code: lambda.Code.fromAsset('./lib/lambda/layers/squidbot-bs4-layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
      description: 'Layer for scraping sw cods',
    });
    Tags.of(bs4_layer).add('project', 'squidbot');

    const SquidbotScrapingLambda = new lambda.Function(this, 'SquidbotSWTokenFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset('./lib/lambda/functions/squidbot-sw-codes-lambda'),
      layers: [
        SquidbotRequestsLayer,
        bs4_layer
      ],
      role: SquidbotLambdaRole,
      timeout: cdk.Duration.seconds(300),
      environment: {
        'SW_ACTIVE_CODES_TABLE': SquidbotActiveCodeDynamoTable.tableName,
        'SW_EXPIRED_CODES_TABLE': SquidbotExpiredCodeDynamoTable.tableName,
        'DISCORD_WEBHOOK_TABLE':  SquidbotDiscordWebhookDynamoTable.tableName
      }
      
    });
    Tags.of(SquidbotScrapingLambda).add('project', 'squidbot');

    const SquidbotExpireCodeLambda = new lambda.Function(this, 'SquidbotSWExpireCodeFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset('./lib/lambda/functions/squidbot-sw-expire-code-lambda'),
      layers: [bs4_layer],
      role: SquidbotLambdaRole,
      timeout: cdk.Duration.seconds(300),
      environment: {
        'SW_ACTIVE_CODES_TABLE': SquidbotActiveCodeDynamoTable.tableName,
        'SW_EXPIRED_CODES_TABLE': SquidbotExpiredCodeDynamoTable.tableName,
        'DISCORD_WEBHOOK_TABLE':  SquidbotDiscordWebhookDynamoTable.tableName
      }
    });
    Tags.of(SquidbotExpireCodeLambda).add('project', 'squidbot');
    

    const squidbotStateMachine = new sfn.StateMachine(this, 'SquidbotStateMachine', {
      definition: new tasks.LambdaInvoke(this, 'SquidbotSWTokenInvoke', {
        lambdaFunction: SquidbotScrapingLambda,
        outputPath: "$.Payload",
      }).next(new tasks.LambdaInvoke(this, 'SWCheckForCodes', {
        lambdaFunction: SquidbotDiscordLambda,
        outputPath: "$.Payload",
        inputPath: "$",
      })).next(new tasks.LambdaInvoke(this, 'CheckExpireCodes', {
        lambdaFunction: SquidbotExpireCodeLambda
      })).next(new sfn.Succeed(this, 'Succeed')),
    });

    Tags.of(squidbotStateMachine).add('project', 'squidbot');

    // Events for Squidbot
    const SquidbotEvents = new events.Rule(this, 'SquidbotTriggerTokenLambdaEvent', {
      schedule: events.Schedule.rate(cdk.Duration.hours(2)),
    });
    Tags.of(SquidbotEvents).add('project', 'squidbot');

    SquidbotEvents.addTarget(new targets.SfnStateMachine(squidbotStateMachine));
  }
}

const app = new cdk.App();

const myStack = new SquidbotCdkStack(app, 'squidbot-cdk-stack',{
  tags: {
    project: 'squidbotv2'
  }
});
