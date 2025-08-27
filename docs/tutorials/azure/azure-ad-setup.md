### Azure AD Setup for Authentication and Authorization

1. Register an app in Azure AD
- Note the following:
  - Display Name
  - Application (client) ID
  - Directory (tenant) ID
  - Create a client secret
  - Set Redirect URI to `http://localhost:8080/auth/azure/callback` (for local UI on port 8080)

2. Set environment variables for the API
```
AZURE_AD_ENABLED=true
AZURE_AD_CLIENT_ID=<Application (client) ID>
AZURE_AD_CLIENT_SECRET=<Client secret value>
AZURE_AD_TENANT_ID=<Directory (tenant) ID>
AZURE_AD_REDIRECT_URI=http://localhost:8080/auth/azure/callback
AZURE_AD_ADMIN_GROUP_ID=<Azure AD group ID for admin>
AZURE_AD_USER_GROUP_ID=<Azure AD group ID for user>
```

3. Install Azure dependencies
```
pip install -r api/requirements-azure-ad.txt
```

4. Run API locally and UI
- Ensure API CORS allows `http://localhost:8080`
- Start UI at `http://localhost:8080`

5. Test authentication
- Visit Sign In and click "Continue with Azure AD"
- On successful login, tokens are returned and a session established

6. Authorization via Azure AD groups -> Prowler roles
- Assign users to Azure AD groups whose IDs you configured in `AZURE_AD_ADMIN_GROUP_ID` and `AZURE_AD_USER_GROUP_ID`
- On login, group membership is synced and mapped to local roles 