#!/bin/bash

# Export OpenAPI specification from running FastAPI server
# This script dumps the live schema to openapi.yaml

set -e

# Configuration
API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
OUTPUT_FILE="${OUTPUT_FILE:-openapi.yaml}"
SCHEMA_URL="http://${API_HOST}:${API_PORT}/openapi.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Exporting OpenAPI schema from ${SCHEMA_URL}${NC}"

# Check if API is running
if ! curl -s -f "${SCHEMA_URL}" > /dev/null; then
    echo -e "${RED}❌ Error: API is not responding at ${SCHEMA_URL}${NC}"
    echo -e "${YELLOW}💡 Make sure the API server is running:${NC}"
    echo -e "   make dev    # For development server"
    echo -e "   make up     # For Docker setup"
    exit 1
fi

# Export OpenAPI JSON schema
echo -e "${BLUE}📥 Fetching OpenAPI schema...${NC}"
if ! curl -s -f "${SCHEMA_URL}" -o "openapi.json"; then
    echo -e "${RED}❌ Error: Failed to fetch OpenAPI schema${NC}"
    exit 1
fi

# Convert JSON to YAML if yq is available
if command -v yq >/dev/null 2>&1; then
    echo -e "${BLUE}🔄 Converting JSON to YAML...${NC}"
    yq eval '.' openapi.json > "${OUTPUT_FILE}"
    rm openapi.json
    echo -e "${GREEN}✅ OpenAPI schema exported to ${OUTPUT_FILE} (YAML format)${NC}"
elif command -v python3 >/dev/null 2>&1; then
    echo -e "${BLUE}🔄 Converting JSON to YAML using Python...${NC}"
    python3 -c "
import json
import yaml
import sys

try:
    with open('openapi.json', 'r') as f:
        data = json.load(f)
    
    with open('${OUTPUT_FILE}', 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
    
    print('✅ Conversion successful')
except ImportError:
    print('⚠️  PyYAML not available, keeping JSON format')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
"
    if [ $? -eq 0 ]; then
        rm openapi.json
        echo -e "${GREEN}✅ OpenAPI schema exported to ${OUTPUT_FILE} (YAML format)${NC}"
    else
        # Fallback to JSON
        mv openapi.json "${OUTPUT_FILE%.yaml}.json"
        echo -e "${YELLOW}⚠️  YAML conversion failed, saved as JSON: ${OUTPUT_FILE%.yaml}.json${NC}"
    fi
else
    # Fallback to JSON
    mv openapi.json "${OUTPUT_FILE%.yaml}.json"
    echo -e "${YELLOW}⚠️  No YAML converter found, saved as JSON: ${OUTPUT_FILE%.yaml}.json${NC}"
fi

echo -e "${BLUE}📄 Schema summary:${NC}"

# Show basic schema info
if [ -f "${OUTPUT_FILE}" ]; then
    SCHEMA_FILE="${OUTPUT_FILE}"
elif [ -f "${OUTPUT_FILE%.yaml}.json" ]; then
    SCHEMA_FILE="${OUTPUT_FILE%.yaml}.json"
fi

if command -v jq >/dev/null 2>&1 && [[ "${SCHEMA_FILE}" == *.json ]]; then
    echo -e "   📋 Title: $(jq -r '.info.title // "N/A"' "${SCHEMA_FILE}")"
    echo -e "   🏷️  Version: $(jq -r '.info.version // "N/A"' "${SCHEMA_FILE}")"
    echo -e "   🛤️  Paths: $(jq -r '.paths | keys | length' "${SCHEMA_FILE}") endpoints"
    echo -e "   📊 Schemas: $(jq -r '.components.schemas | keys | length' "${SCHEMA_FILE}") components"
elif command -v yq >/dev/null 2>&1 && [[ "${SCHEMA_FILE}" == *.yaml || "${SCHEMA_FILE}" == *.yml ]]; then
    echo -e "   📋 Title: $(yq eval '.info.title // "N/A"' "${SCHEMA_FILE}")"
    echo -e "   🏷️  Version: $(yq eval '.info.version // "N/A"' "${SCHEMA_FILE}")"
    echo -e "   🛤️  Paths: $(yq eval '.paths | keys | length' "${SCHEMA_FILE}") endpoints"
    echo -e "   📊 Schemas: $(yq eval '.components.schemas | keys | length' "${SCHEMA_FILE}") components"
fi

echo -e "${GREEN}🎉 OpenAPI export completed successfully!${NC}"

# Show endpoint summary
echo -e "\n${BLUE}📍 Available endpoints:${NC}"
if command -v jq >/dev/null 2>&1 && [[ "${SCHEMA_FILE}" == *.json ]]; then
    jq -r '.paths | to_entries[] | "   \(.key): \(.value | keys | join(", ") | ascii_upcase)"' "${SCHEMA_FILE}"
elif command -v yq >/dev/null 2>&1 && [[ "${SCHEMA_FILE}" == *.yaml || "${SCHEMA_FILE}" == *.yml ]]; then
    yq eval '.paths | to_entries | .[] | "   " + .key + ": " + (.value | keys | join(", ") | upcase)' "${SCHEMA_FILE}"
fi

echo ""
echo -e "${BLUE}💡 Usage examples:${NC}"
echo -e "   📖 View schema: cat ${SCHEMA_FILE}"
echo -e "   🔍 Validate: swagger-codegen validate -i ${SCHEMA_FILE}"
echo -e "   🌐 Serve docs: swagger-ui-serve ${SCHEMA_FILE}"
echo -e "   📝 Generate client: openapi-generator generate -i ${SCHEMA_FILE} -g python"