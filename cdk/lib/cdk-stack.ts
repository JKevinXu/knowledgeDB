import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as opensearchserverless from 'aws-cdk-lib/aws-opensearchserverless';
import { Construct } from 'constructs';

export class CdkStack extends cdk.Stack {
  public readonly knowledgeBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // S3 Bucket for Knowledge Base documents and metadata
    this.knowledgeBucket = new s3.Bucket(this, 'KnowledgeBaseBucket', {
      bucketName: `knowledge-base-${cdk.Aws.ACCOUNT_ID}-${cdk.Aws.REGION}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      
      // Enable intelligent tiering for cost optimization
      intelligentTieringConfigurations: [
        {
          name: 'archive-config',
          archiveAccessTierTime: cdk.Duration.days(90),
          deepArchiveAccessTierTime: cdk.Duration.days(180),
        },
      ],

      // Lifecycle rules for old versions
      lifecycleRules: [
        {
          id: 'DeleteOldVersions',
          noncurrentVersionExpiration: cdk.Duration.days(90),
          enabled: true,
        },
      ],

      // CORS configuration for web access if needed
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.HEAD],
          allowedOrigins: ['*'],
          allowedHeaders: ['*'],
        },
      ],
    });

    // IAM Policy for Bedrock Knowledge Base to access S3
    const bedrockAccessPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:ListBucket',
      ],
      resources: [
        this.knowledgeBucket.bucketArn,
        `${this.knowledgeBucket.bucketArn}/*`,
      ],
      principals: [new iam.ServicePrincipal('bedrock.amazonaws.com')],
      conditions: {
        StringEquals: {
          'aws:SourceAccount': cdk.Aws.ACCOUNT_ID,
        },
      },
    });

    this.knowledgeBucket.addToResourcePolicy(bedrockAccessPolicy);

    // OpenSearch Serverless Collection for vector storage
    const collectionName = `kb-${cdk.Aws.ACCOUNT_ID}`;
    
    // Encryption policy for OpenSearch Serverless
    const encryptionPolicy = new opensearchserverless.CfnSecurityPolicy(this, 'EncryptionPolicy', {
      name: `${collectionName}-encryption`,
      type: 'encryption',
      policy: JSON.stringify({
        Rules: [
          {
            ResourceType: 'collection',
            Resource: [`collection/${collectionName}`],
          },
        ],
        AWSOwnedKey: true,
      }),
    });

    // Network policy for OpenSearch Serverless
    const networkPolicy = new opensearchserverless.CfnSecurityPolicy(this, 'NetworkPolicy', {
      name: `${collectionName}-network`,
      type: 'network',
      policy: JSON.stringify([
        {
          Rules: [
            {
              ResourceType: 'collection',
              Resource: [`collection/${collectionName}`],
            },
            {
              ResourceType: 'dashboard',
              Resource: [`collection/${collectionName}`],
            },
          ],
          AllowFromPublic: true,
        },
      ]),
    });

    // OpenSearch Serverless Collection
    const collection = new opensearchserverless.CfnCollection(this, 'VectorCollection', {
      name: collectionName,
      type: 'VECTORSEARCH',
      description: 'Vector collection for Bedrock Knowledge Base',
    });

    collection.addDependency(encryptionPolicy);
    collection.addDependency(networkPolicy);

    // IAM Role for Bedrock Knowledge Base
    const knowledgeBaseRole = new iam.Role(this, 'BedrockKnowledgeBaseRole', {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      description: 'Role for Bedrock Knowledge Base to access S3 and OpenSearch',
    });

    // Grant S3 permissions
    this.knowledgeBucket.grantRead(knowledgeBaseRole);

    // Grant OpenSearch Serverless permissions
    knowledgeBaseRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['aoss:APIAccessAll'],
        resources: [collection.attrArn],
      })
    );

    // Grant Bedrock model invocation permissions
    knowledgeBaseRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel'],
        resources: [
          `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/amazon.titan-embed-text-v1`,
          `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/amazon.titan-embed-text-v2:0`,
        ],
      })
    );

    // Data access policy for OpenSearch Serverless
    const dataAccessPolicy = new opensearchserverless.CfnAccessPolicy(this, 'DataAccessPolicy', {
      name: `${collectionName}-access`,
      type: 'data',
      policy: JSON.stringify([
        {
          Rules: [
            {
              ResourceType: 'collection',
              Resource: [`collection/${collectionName}`],
              Permission: [
                'aoss:CreateCollectionItems',
                'aoss:DeleteCollectionItems',
                'aoss:UpdateCollectionItems',
                'aoss:DescribeCollectionItems',
              ],
            },
            {
              ResourceType: 'index',
              Resource: [`index/${collectionName}/*`],
              Permission: [
                'aoss:CreateIndex',
                'aoss:DeleteIndex',
                'aoss:UpdateIndex',
                'aoss:DescribeIndex',
                'aoss:ReadDocument',
                'aoss:WriteDocument',
              ],
            },
          ],
          Principal: [knowledgeBaseRole.roleArn],
        },
      ]),
    });

    dataAccessPolicy.node.addDependency(collection);

    // TODO: Create Knowledge Base after index is created
    // Uncomment the code below after creating the OpenSearch index manually
    // See README for instructions
    
    /*
    const knowledgeBase = new bedrock.CfnKnowledgeBase(this, 'KnowledgeBase', {
      name: 'DocumentKnowledgeBase',
      description: 'Knowledge Base for document retrieval and Q&A',
      roleArn: knowledgeBaseRole.roleArn,
      knowledgeBaseConfiguration: {
        type: 'VECTOR',
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/amazon.titan-embed-text-v2:0`,
        },
      },
      storageConfiguration: {
        type: 'OPENSEARCH_SERVERLESS',
        opensearchServerlessConfiguration: {
          collectionArn: collection.attrArn,
          vectorIndexName: 'bedrock-knowledge-base-index',
          fieldMapping: {
            vectorField: 'bedrock-knowledge-base-default-vector',
            textField: 'AMAZON_BEDROCK_TEXT_CHUNK',
            metadataField: 'AMAZON_BEDROCK_METADATA',
          },
        },
      },
    });

    knowledgeBase.node.addDependency(collection);
    knowledgeBase.node.addDependency(dataAccessPolicy);

    const dataSource = new bedrock.CfnDataSource(this, 'S3DataSource', {
      name: 'S3DocumentSource',
      description: 'S3 bucket containing documents for the knowledge base',
      knowledgeBaseId: knowledgeBase.attrKnowledgeBaseId,
      dataSourceConfiguration: {
        type: 'S3',
        s3Configuration: {
          bucketArn: this.knowledgeBucket.bucketArn,
          inclusionPrefixes: ['documents/'],
        },
      },
    });

    dataSource.node.addDependency(knowledgeBase);
    */

    // Outputs
    new cdk.CfnOutput(this, 'KnowledgeBucketName', {
      value: this.knowledgeBucket.bucketName,
      description: 'Knowledge Base S3 Bucket Name',
      exportName: 'KnowledgeBaseBucketName',
    });

    new cdk.CfnOutput(this, 'KnowledgeBucketArn', {
      value: this.knowledgeBucket.bucketArn,
      description: 'Knowledge Base S3 Bucket ARN',
      exportName: 'KnowledgeBaseBucketArn',
    });

    // Output the expected folder structure
    new cdk.CfnOutput(this, 'DocumentsPath', {
      value: `s3://${this.knowledgeBucket.bucketName}/documents/`,
      description: 'Path for uploading documents with metadata',
    });

    new cdk.CfnOutput(this, 'KnowledgeBaseRoleArn', {
      value: knowledgeBaseRole.roleArn,
      description: 'IAM Role ARN for Bedrock Knowledge Base',
      exportName: 'BedrockKnowledgeBaseRoleArn',
    });

    /*
    // Uncomment after Knowledge Base is created
    new cdk.CfnOutput(this, 'KnowledgeBaseId', {
      value: knowledgeBase.attrKnowledgeBaseId,
      description: 'Bedrock Knowledge Base ID',
      exportName: 'BedrockKnowledgeBaseId',
    });

    new cdk.CfnOutput(this, 'KnowledgeBaseArn', {
      value: knowledgeBase.attrKnowledgeBaseArn,
      description: 'Bedrock Knowledge Base ARN',
      exportName: 'BedrockKnowledgeBaseArn',
    });

    new cdk.CfnOutput(this, 'DataSourceId', {
      value: dataSource.attrDataSourceId,
      description: 'Data Source ID for S3 bucket',
      exportName: 'DataSourceId',
    });
    */

    new cdk.CfnOutput(this, 'CollectionEndpoint', {
      value: collection.attrCollectionEndpoint,
      description: 'OpenSearch Serverless Collection Endpoint',
      exportName: 'OpenSearchCollectionEndpoint',
    });
  }
}
