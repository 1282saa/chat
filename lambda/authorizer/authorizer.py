#!/usr/bin/env python3
"""
AWS Lambda Authorizer for Cognito JWT Token Validation
Validates JWT tokens from Cognito User Pool and provides user context
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional
import requests
import jwt
from jwt import PyJWKClient
import boto3
from botocore.exceptions import ClientError

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
USER_POOL_ID = os.environ.get("USER_POOL_ID")
USER_POOL_CLIENT_ID = os.environ.get("USER_POOL_CLIENT_ID")
AWS_REGION = os.environ.get("REGION", "ap-northeast-2")

# Cognito settings
COGNITO_DOMAIN = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{USER_POOL_ID}"
JWKS_URI = f"{COGNITO_DOMAIN}/.well-known/jwks.json"

# Initialize JWKS client for token verification
jwks_client = PyJWKClient(JWKS_URI)


class AuthorizerError(Exception):
    """Custom exception for authorization errors"""
    pass


def extract_token_from_header(authorization_header: str) -> str:
    """Extract JWT token from Authorization header"""
    if not authorization_header:
        raise AuthorizerError("Missing Authorization header")
    
    if not authorization_header.startswith("Bearer "):
        raise AuthorizerError("Invalid Authorization header format. Must be 'Bearer <token>'")
    
    return authorization_header.split("Bearer ")[1].strip()


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token from Cognito"""
    try:
        # Get signing key
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=USER_POOL_CLIENT_ID,
            issuer=COGNITO_DOMAIN,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True
            }
        )
        
        # Additional validation - accept both access and id tokens
        token_use = payload.get("token_use")
        if token_use not in ["access", "id"]:
            raise AuthorizerError(f"Invalid token use. Expected 'access' or 'id' token, got '{token_use}'")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise AuthorizerError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthorizerError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise AuthorizerError(f"Token verification failed: {str(e)}")


def generate_policy(principal_id: str, effect: str, resource: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate IAM policy for API Gateway"""
    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource
                }
            ]
        }
    }
    
    if context:
        policy["context"] = {k: str(v) for k, v in context.items()}
    
    return policy


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda authorizer handler function"""
    try:
        logger.info("Authorizer invoked")
        logger.debug(f"Event: {json.dumps(event, default=str)}")
        
        # Extract token from authorization header
        auth_header = event.get("headers", {}).get("Authorization") or event.get("headers", {}).get("authorization")
        
        if not auth_header:
            logger.warning("No Authorization header found")
            raise AuthorizerError("Unauthorized")
        
        token = extract_token_from_header(auth_header)
        
        # Verify JWT token
        payload = verify_jwt_token(token)
        
        # Extract user information
        user_id = payload.get("sub")
        username = payload.get("username")
        email = payload.get("email")
        client_id = payload.get("client_id")
        
        # Extract Cognito groups information
        cognito_groups = payload.get("cognito:groups", [])
        groups_str = ",".join(cognito_groups) if cognito_groups else ""
        
        logger.info(f"Token validated successfully for user: {username} ({user_id}) with groups: {cognito_groups}")
        
        # Create context for downstream Lambda functions
        user_context = {
            "userId": user_id,
            "username": username or "",
            "email": email or "",
            "clientId": client_id or "",
            "groups": groups_str,
            "tokenPayload": json.dumps(payload)
        }
        
        # Generate allow policy
        policy = generate_policy(
            principal_id=user_id,
            effect="Allow",
            resource=event["methodArn"],
            context=user_context
        )
        
        logger.info("Authorization successful")
        return policy
        
    except AuthorizerError as e:
        logger.warning(f"Authorization failed: {str(e)}")
        # For authorization failures, we can either:
        # 1. Return "Deny" policy (recommended)
        # 2. Raise exception (causes 401 error)
        
        # Return deny policy
        return generate_policy(
            principal_id="unknown",
            effect="Deny", 
            resource=event["methodArn"]
        )
        
    except Exception as e:
        logger.error(f"Authorizer error: {str(e)}", exc_info=True)
        # Return deny policy for unexpected errors
        return generate_policy(
            principal_id="unknown",
            effect="Deny",
            resource=event["methodArn"]
        )


if __name__ == "__main__":
    # Test handler locally
    test_event = {
        "type": "REQUEST",
        "methodArn": "arn:aws:execute-api:ap-northeast-2:123456789012:abcdef123/prod/POST/chat",
        "headers": {
            "Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9..."  # Replace with actual token
        }
    }
    
    result = handler(test_event, None)
    print(json.dumps(result, indent=2))