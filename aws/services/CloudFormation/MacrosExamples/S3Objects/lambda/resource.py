# Copyright 2018-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import logging, json, base64
import boto3
import cfnresponse

s3_client = boto3.client("s3")

for logger_name in [__name__, 'boto3']:
    logger = logging.getLogger(logger_name)
    ch = logging.StreamHandler()
    logger.setLevel(logging.INFO)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(threadName)s %(filename)s:%(lineno)d - %(funcName)s() - %(levelname)s - %(message)s'))
    logger.addHandler(ch)

def handler(event, context):
    logger.info("Received request:\n" + json.dumps(event, indent=4))

    request = event["RequestType"]
    properties = event["ResourceProperties"]
    target = properties["Target"]
    bucket = event['ResourceProperties']['Target']['Bucket']
    key = event['ResourceProperties']['Target']['Key']
    
    target_uri = f's3://{bucket}/{key}'
    
    if "Target" not in properties or all(
        prop not in properties for prop in ["Body", "Base64Body", "Source"]
    ):
        return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.FAILED,
                                responseData={'Bucket': bucket, 'Key': key},
                                physicalResourceId=target_uri,
                                reason='Missing required parameters')

    # Create or update
    if request in ("Create", "Update"):
        # Full-text
        if "Body" in properties:
            logger.info(f'Creating/Updating "{target_uri}" using fulltext body')
            target.update(
                {
                    "Body": properties["Body"],
                }
            )

            try:
                s3_client.put_object(**target)
            except Exception as e:
                logger.error(f'Failed to create or update "{target_uri}" from full-text body\n{e}')
                
                return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.FAILED,
                                        responseData={'Bucket': bucket, 'Key': key},
                                        physicalResourceId=target_uri,
                                        reason=f'Failed to create or update from full-text body\n{e}')

        # Base64 encoded
        elif "Base64Body" in properties:
            logger.info(f'Creating "{target_uri}" using base64 encoded body')
            
            try:
                body = base64.b64decode(properties["Base64Body"])
            except:
                return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.FAILED,
                                        responseData={'Bucket': bucket, 'Key': key},
                                        physicalResourceId=target_uri,
                                        reason='Malformed Base64Body')
            
            try:
                target.update({"Body": body})

                s3_client.put_object(**target)
            except Exception as e:
                logger.error(f'Failed to create or update "{target_uri}" from base64 encoded body\n{e}')
                
                return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.FAILED,
                                        responseData={'Bucket': bucket, 'Key': key},
                                        physicalResourceId=target_uri,
                                        reason=f'Failed to create or update from base64 body\n{e}')
        # Copy  
        elif "Source" in properties:
            source = properties["Source"]
            source_uri = f's3://{source["Bucket"]}/{source["Key"]}'
            logger.info(f'Copying "{source_uri}" to "{target_uri}"')

            try:
                s3_client.copy_object(CopySource=source,
                                      Bucket=target["Bucket"],
                                      Key=target["Key"],
                                      MetadataDirective="COPY",
                                      TaggingDirective="COPY",
                                      ACL=target["ACL"])
            except Exception as e:
                logger.error(f'Failed to copy {source_uri} to "{target_uri}"\n{e}')
                
                return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.FAILED,
                                        responseData={'Bucket': bucket, 'Key': key},
                                        physicalResourceId=target_uri,
                                        reason=f'Failed to create or update from copy of "{source_uri}"\n{e}')
                
        else:
            return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.FAILED,
                                    responseData={'Bucket': bucket, 'Key': key},
                                    physicalResourceId=target_uri,
                                    reason='Malformed body')

        return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.SUCCESS,
                                responseData={'Bucket': bucket, 'Key': key},
                                physicalResourceId=target_uri,
                                reason=f'Created "{target_uri}"')

    # Delete
    if request == "Delete":
        logger.info(f'Deleting "{target_uri}"')
        
        try:
            s3_client.delete_object(Bucket=target["Bucket"],
                                    Key=target["Key"])
        except Exception as e:
                logger.error(f'Failed to delete "{target_uri}"\n{e}')
                
                return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.FAILED,
                                        responseData={'Bucket': bucket, 'Key': key},
                                        physicalResourceId=target_uri,
                                        reason=f'Failed to delete object\n{e}')

        return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.SUCCESS,
                            responseData={'Bucket': bucket, 'Key': key},
                            physicalResourceId=target_uri,
                            reason=f'Deleted "{target_uri}"')
        
        
    return cfnresponse.send(event=event, context=context, responseStatus=cfnresponse.FAILED,
                            responseData={'Bucket': bucket, 'Key': key},
                            physicalResourceId=target_uri,
                            reason=f'Unexpected {request}')
