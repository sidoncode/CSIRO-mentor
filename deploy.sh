#!/bin/bash

# ============================================
# CSIRO Mentor - Quick Deployment Script
# ============================================

set -e

# Configuration
RESOURCE_GROUP="rg-csiro-mentor"
APP_NAME="csiro-mentor-app"
PLAN_NAME="plan-csiro-mentor"
LOCATION="australiaeast"

echo "🚀 CSIRO Mentor Deployment Script"
echo "=================================="

# Check if logged in
echo "📋 Checking Azure login..."
if ! az account show &> /dev/null; then
    echo "Please login to Azure first:"
    az login
fi

# Create Resource Group
echo "📁 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION --output none 2>/dev/null || true

# Create App Service Plan
echo "📦 Creating App Service Plan..."
az appservice plan create \
    --name $PLAN_NAME \
    --resource-group $RESOURCE_GROUP \
    --sku B1 \
    --is-linux \
    --output none 2>/dev/null || true

# Create Web App
echo "🌐 Creating Web App..."
az webapp create \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan $PLAN_NAME \
    --runtime "PYTHON:3.11" \
    --output none 2>/dev/null || true

# Configure Environment Variables
echo "⚙️  Configuring environment variables..."
az webapp config appsettings set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
    AZURE_OPENAI_ENDPOINT="https://csiro7757517966.openai.azure.com" \
    AZURE_OPENAI_API_KEY="Fz4PuTyevDZPjxtFF0auXqoLwe67uyYJ09VhyNcQAFN7w9kE1gY1JQQJ99BLACL93NaXJ3w3AAAAACOGpXgp" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    AZURE_OPENAI_API_VERSION="2024-02-15-preview" \
    AZURE_SEARCH_ENDPOINT="https://csiro-ai-search.search.windows.net" \
    AZURE_SEARCH_API_KEY="b9YK7YAOfRGhKTEqHibQZcyajJhoxgnPy4d2o47RfaAzSeDyqaFs" \
    AZURE_SEARCH_INDEX="yellow-bird-2s3zjlv6bj" \
    ENABLE_RAG="true" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true" \
    --output none

# Set Startup Command
echo "🔧 Setting startup command..."
az webapp config set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "gunicorn --bind=0.0.0.0:8000 --workers=4 --worker-class=uvicorn.workers.UvicornWorker backend.app:app" \
    --output none

# Create deployment package
echo "📦 Creating deployment package..."
zip -r deploy.zip . -x "*.git*" -x "__pycache__/*" -x "*.pyc" -x ".env" -x "deploy.zip" -x "deploy.sh"

# Deploy
echo "🚀 Deploying application..."
az webapp deployment source config-zip \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --src deploy.zip

# Cleanup
rm -f deploy.zip

# Get URL
APP_URL=$(az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "defaultHostName" -o tsv)

echo ""
echo "✅ Deployment Complete!"
echo "========================"
echo "🌐 App URL: https://$APP_URL"
echo "❤️  Health:  https://$APP_URL/health"
echo ""
echo "📝 To view logs:"
echo "   az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
