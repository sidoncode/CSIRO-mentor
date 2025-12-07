# CSIRO Mentor - Azure App Service Deployment Guide

## 📁 Project Structure

```
csiro-mentor-deploy/
├── .env                    # Environment variables (KEEP SECRET!)
├── .env.example            # Template for environment variables
├── requirements.txt        # Python dependencies
├── startup.txt             # Azure startup command
├── backend/
│   └── app.py              # FastAPI backend application
└── static/
    └── index.html          # Frontend application
```

---

## 🚀 Step-by-Step Deployment

### Step 1: Prerequisites

Make sure you have:
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) installed
- An Azure subscription
- Your Azure credentials ready

### Step 2: Login to Azure

```bash
# Login to Azure
az login

# Set your subscription (if you have multiple)
az account set --subscription "Azure subscription 1"
```

### Step 3: Create Resource Group (if not exists)

```bash
# Create a resource group in Australia East
az group create \
    --name rg-csiro-mentor \
    --location australiaeast
```

### Step 4: Create App Service Plan

```bash
# Create an App Service Plan (B1 = Basic tier, good for testing)
az appservice plan create \
    --name plan-csiro-mentor \
    --resource-group rg-csiro-mentor \
    --sku B1 \
    --is-linux
```

### Step 5: Create the Web App

```bash
# Create the Web App with Python 3.11
az webapp create \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor \
    --plan plan-csiro-mentor \
    --runtime "PYTHON:3.11"
```

> **Note:** The app name must be globally unique. If `csiro-mentor-app` is taken, try `csiro-mentor-app-123` or similar.

### Step 6: Configure Environment Variables

```bash
# Set all environment variables at once
az webapp config appsettings set \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor \
    --settings \
    AZURE_OPENAI_ENDPOINT="https://csiro7757517966.openai.azure.com" \
    AZURE_OPENAI_API_KEY="Fz4PuTyevDZPjxtFF0auXqoLwe67uyYJ09VhyNcQAFN7w9kE1gY1JQQJ99BLACL93NaXJ3w3AAAAACOGpXgp" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    AZURE_OPENAI_API_VERSION="2024-02-15-preview" \
    AZURE_SEARCH_ENDPOINT="https://csiro-ai-search.search.windows.net" \
    AZURE_SEARCH_API_KEY="b9YK7YAOfRGhKTEqHibQZcyajJhoxgnPy4d2o47RfaAzSeDyqaFs" \
    AZURE_SEARCH_INDEX="yellow-bird-2s3zjlv6bj" \
    ENABLE_RAG="true" \
    MAX_TOKENS="4096" \
    TEMPERATURE="0.7" \
    TOP_N_DOCUMENTS="5" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

### Step 7: Configure Startup Command

```bash
# Set the startup command
az webapp config set \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor \
    --startup-file "gunicorn --bind=0.0.0.0:8000 --workers=4 --worker-class=uvicorn.workers.UvicornWorker backend.app:app"
```

### Step 8: Deploy the Application

**Option A: Deploy using ZIP (Recommended)**

```bash
# Navigate to the project directory
cd csiro-mentor-deploy

# Create a ZIP file of your application
zip -r deploy.zip . -x "*.git*" -x "__pycache__/*" -x "*.pyc" -x ".env"

# Deploy the ZIP file
az webapp deployment source config-zip \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor \
    --src deploy.zip
```

**Option B: Deploy using Local Git**

```bash
# Enable local git deployment
az webapp deployment source config-local-git \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor

# Get the deployment URL
az webapp deployment list-publishing-profiles \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor \
    --query "[?publishMethod=='MSDeploy'].publishUrl" -o tsv

# Initialize git and push
git init
git add .
git commit -m "Initial deployment"
git remote add azure <deployment-url>
git push azure master
```

### Step 9: Verify Deployment

```bash
# Get your app URL
az webapp show \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor \
    --query "defaultHostName" -o tsv

# Check the health endpoint
curl https://csiro-mentor-app.azurewebsites.net/health
```

### Step 10: View Logs (if needed)

```bash
# Enable logging
az webapp log config \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor \
    --web-server-logging filesystem

# Stream logs
az webapp log tail \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor
```

---

## 🔧 Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint | Yes |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Yes |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name (e.g., gpt-4o) | Yes |
| `AZURE_OPENAI_API_VERSION` | API version | Yes |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint | Yes (for RAG) |
| `AZURE_SEARCH_API_KEY` | Azure AI Search API key | Yes (for RAG) |
| `AZURE_SEARCH_INDEX` | Search index name | Yes (for RAG) |
| `ENABLE_RAG` | Enable RAG (true/false) | No (default: true) |
| `MAX_TOKENS` | Max response tokens | No (default: 4096) |
| `TEMPERATURE` | Response temperature | No (default: 0.7) |
| `TOP_N_DOCUMENTS` | Documents to retrieve | No (default: 5) |

---

## 🌐 After Deployment

Your app will be available at:
```
https://csiro-mentor-app.azurewebsites.net
```

### API Endpoints:
- `GET /` - Main application (frontend)
- `GET /health` - Health check
- `GET /api/config` - Public configuration
- `POST /api/chat` - Chat endpoint with RAG

---

## 🔒 Security Notes

1. **Never commit `.env` to git** - Add it to `.gitignore`
2. **Use Azure Key Vault** for production secrets
3. **Enable HTTPS only** in Azure Portal
4. **Configure CORS** if needed for custom domains

### Enable HTTPS Only:
```bash
az webapp update \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor \
    --https-only true
```

---

## 🔄 Updating the Application

```bash
# Make your changes, then:
zip -r deploy.zip . -x "*.git*" -x "__pycache__/*" -x "*.pyc" -x ".env"

az webapp deployment source config-zip \
    --name csiro-mentor-app \
    --resource-group rg-csiro-mentor \
    --src deploy.zip
```

---

## ❓ Troubleshooting

### App not starting?
```bash
# Check logs
az webapp log tail --name csiro-mentor-app --resource-group rg-csiro-mentor
```

### 500 Error?
- Check environment variables are set correctly
- Verify Azure OpenAI and Search services are accessible
- Check the deployment name matches your Azure OpenAI deployment

### CORS Issues?
Add your domain to `ALLOWED_ORIGINS` environment variable.

---

## 📞 Support

For issues with:
- **Azure App Service**: [Azure Support](https://azure.microsoft.com/support/)
- **Azure OpenAI**: Check [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- **Azure AI Search**: Check [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
