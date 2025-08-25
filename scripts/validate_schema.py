#!/usr/bin/env python3

"""Validate OpenAPI schema against requirements from the brief."""

import json
import sys
import requests
from typing import Dict, Any

# Configuration
API_BASE = "http://localhost:8000"
OPENAPI_URL = f"{API_BASE}/openapi.json"

def validate_schema():
    """Validate the OpenAPI schema against requirements."""
    print("🔍 Validating OpenAPI schema against requirements...")
    
    try:
        # Fetch OpenAPI schema
        response = requests.get(OPENAPI_URL, timeout=10)
        response.raise_for_status()
        schema = response.json()
    except requests.RequestException as e:
        print(f"❌ Error fetching schema: {e}")
        return False
    
    errors = []
    warnings = []
    
    # Check basic schema structure
    if schema.get("openapi") != "3.1.0":
        warnings.append(f"OpenAPI version is {schema.get('openapi')}, expected 3.1.0")
    
    if schema.get("info", {}).get("title") != "Summarizer API":
        errors.append(f"Title is '{schema.get('info', {}).get('title')}', expected 'Summarizer API'")
    
    # Check required endpoints
    paths = schema.get("paths", {})
    
    # 1. POST /api/v1/documents/
    post_documents = paths.get("/api/v1/documents/", {}).get("post", {})
    if not post_documents:
        errors.append("Missing POST /api/v1/documents/ endpoint")
    else:
        # Check 202 response
        responses = post_documents.get("responses", {})
        if "202" not in responses:
            errors.append("POST /api/v1/documents/ missing 202 response")
        elif responses["202"].get("content", {}).get("application/json", {}).get("schema", {}).get("$ref") != "#/components/schemas/DocumentResponse":
            errors.append("POST /api/v1/documents/ 202 response should use DocumentResponse schema")
    
    # 2. GET /api/v1/documents/{document_uuid}/
    get_documents = paths.get("/api/v1/documents/{document_uuid}/", {}).get("get", {})
    if not get_documents:
        errors.append("Missing GET /api/v1/documents/{document_uuid}/ endpoint")
    else:
        # Check 200 response
        responses = get_documents.get("responses", {})
        if "200" not in responses:
            errors.append("GET /api/v1/documents/{document_uuid}/ missing 200 response")
        elif responses["200"].get("content", {}).get("application/json", {}).get("schema", {}).get("$ref") != "#/components/schemas/DocumentResponse":
            errors.append("GET /api/v1/documents/{document_uuid}/ 200 response should use DocumentResponse schema")
    
    # 3. Health endpoints
    if "/healthz" not in paths:
        errors.append("Missing /healthz endpoint")
    if "/readyz" not in paths:
        errors.append("Missing /readyz endpoint")
    
    # Check schemas
    components = schema.get("components", {}).get("schemas", {})
    
    # 4. DocumentResponse schema
    doc_response = components.get("DocumentResponse", {})
    if not doc_response:
        errors.append("Missing DocumentResponse schema")
    else:
        properties = doc_response.get("properties", {})
        required_fields = [
            "document_uuid", "status", "name", "url", "summary", 
            "data_progress", "created_at", "updated_at"
        ]
        
        for field in required_fields:
            if field not in properties:
                errors.append(f"DocumentResponse missing required field: {field}")
        
        # Check data_progress constraints
        data_progress = properties.get("data_progress", {})
        if data_progress.get("minimum") != 0.0 or data_progress.get("maximum") != 1.0:
            errors.append("DocumentResponse.data_progress should have min=0.0, max=1.0")
        
        # Check summary can be null
        summary = properties.get("summary", {})
        if "anyOf" not in summary or {"type": "null"} not in summary.get("anyOf", []):
            errors.append("DocumentResponse.summary should allow null values")
    
    # 5. DocumentStatus enum
    doc_status = components.get("DocumentStatus", {})
    if not doc_status:
        errors.append("Missing DocumentStatus schema")
    else:
        expected_statuses = ["PENDING", "FETCHING", "PARSING", "SUMMARIZING", "SUCCESS", "FAILED"]
        actual_statuses = doc_status.get("enum", [])
        
        for status in expected_statuses:
            if status not in actual_statuses:
                errors.append(f"DocumentStatus missing enum value: {status}")
    
    # 6. DocumentCreateRequest schema
    doc_create = components.get("DocumentCreateRequest", {})
    if not doc_create:
        errors.append("Missing DocumentCreateRequest schema")
    else:
        properties = doc_create.get("properties", {})
        if "name" not in properties:
            errors.append("DocumentCreateRequest missing name field")
        if "url" not in properties:
            errors.append("DocumentCreateRequest missing url field")
    
    # Print results
    print(f"\n📊 Validation Results:")
    print(f"   ✅ Schema loaded successfully")
    print(f"   🛤️  Endpoints: {len(paths)} found")
    print(f"   📊 Components: {len(components)} found")
    
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")
    
    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for error in errors:
            print(f"   • {error}")
        return False
    else:
        print(f"\n✅ All validations passed! Schema complies with requirements.")
        return True

def test_live_endpoints():
    """Test live API endpoints for correct response format."""
    print("\n🧪 Testing live API endpoints...")
    
    try:
        # Test POST /api/v1/documents/
        post_data = {
            "name": "Schema Validation Test",
            "url": "https://example.com/schema-test"
        }
        
        response = requests.post(
            f"{API_BASE}/api/v1/documents/",
            json=post_data,
            timeout=10
        )
        
        if response.status_code != 202:
            print(f"❌ POST /api/v1/documents/ returned {response.status_code}, expected 202")
            return False
        
        post_json = response.json()
        required_fields = [
            "document_uuid", "status", "name", "url", "summary", 
            "data_progress", "created_at", "updated_at"
        ]
        
        for field in required_fields:
            if field not in post_json:
                print(f"❌ POST response missing field: {field}")
                return False
        
        # Check field types and values
        if not isinstance(post_json["data_progress"], (int, float)) or not (0.0 <= post_json["data_progress"] <= 1.0):
            print(f"❌ data_progress should be 0.0-1.0, got: {post_json['data_progress']}")
            return False
        
        if post_json["summary"] is not None:
            print(f"⚠️  summary should be null initially, got: {post_json['summary']}")
        
        if post_json["status"] != "PENDING":
            print(f"⚠️  status should be PENDING initially, got: {post_json['status']}")
        
        print(f"✅ POST /api/v1/documents/ response format correct")
        
        # Test GET /api/v1/documents/{uuid}/
        document_uuid = post_json["document_uuid"]
        get_response = requests.get(
            f"{API_BASE}/api/v1/documents/{document_uuid}/",
            timeout=10
        )
        
        if get_response.status_code != 200:
            print(f"❌ GET /api/v1/documents/{document_uuid}/ returned {get_response.status_code}, expected 200")
            return False
        
        get_json = get_response.json()
        
        # Should have same fields as POST response
        for field in required_fields:
            if field not in get_json:
                print(f"❌ GET response missing field: {field}")
                return False
        
        # Should return same document
        if get_json["document_uuid"] != document_uuid:
            print(f"❌ GET returned different document_uuid")
            return False
        
        print(f"✅ GET /api/v1/documents/{{uuid}}/ response format correct")
        
        # Test health endpoints
        health_response = requests.get(f"{API_BASE}/healthz", timeout=5)
        if health_response.status_code != 200:
            print(f"❌ /healthz returned {health_response.status_code}, expected 200")
            return False
        
        readyz_response = requests.get(f"{API_BASE}/readyz", timeout=5)
        if readyz_response.status_code != 200:
            print(f"❌ /readyz returned {readyz_response.status_code}, expected 200")
            return False
        
        print(f"✅ Health endpoints working correctly")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ Error testing endpoints: {e}")
        return False

def main():
    """Main validation function."""
    print("🔍 OpenAPI Schema Validation Tool")
    print("=" * 50)
    
    schema_valid = validate_schema()
    endpoints_valid = test_live_endpoints()
    
    print("\n" + "=" * 50)
    
    if schema_valid and endpoints_valid:
        print("🎉 All validations passed! API complies with requirements.")
        sys.exit(0)
    else:
        print("❌ Validation failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
