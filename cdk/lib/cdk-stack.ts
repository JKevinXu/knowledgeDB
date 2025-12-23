import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
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
  }
}
