# WebIntelX AI Deployment Guide

## Deployment Architecture

- **Backend**: Railway - Python FastAPI with ML/CrewAI
- **Frontend**: Vercel - Next.js
- **Database**: SQLite (ephemeral - data lost on redeploy)

## Security Alert

**Never commit API keys to Git.** All secrets must be set in Railway/Vercel dashboards only.

## Step 1: Push to GitHub

```powershell
# Stage changes
git add .
git commit -m "Separate frontend and Python backend deployment

- Added .vercelignore to prevent Vercel from bundling Python backend
- Added railway.json for Railway backend deployment
- Updated frontend/vercel.json to remove hardcoded backend URLs
- Updated frontend/.env.example for Railway backend
- Updated Dockerfile for Railway compatibility
- Deprecated render.yaml (now using Railway)
- Updated DEPLOYMENT.md for Railway deployment"

# Push to GitHub
git push origin main
```

## Step 2: Deploy Backend to Railway

1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect Python/FastAPI from `railway.json`
5. Click "Deploy"

### Configure Environment Variables in Railway

After deployment, go to your Railway project → Variables and add:

**Required (set these manually):**
- `LLM_API_KEY` - Your Groq API key (generate from https://console.groq.com/keys)
- `CORS_ALLOWED_ORIGINS` - Add your frontend domain after Vercel deployment (e.g., `https://your-vercel-app.vercel.app,https://localhost:3000,http://localhost:3000`)

**Optional (Railway will use defaults, but you can override):**
- `JWT_SECRET_KEY` - Railway will auto-generate this
- `DATABASE_URL` - Default: `sqlite:///./WebIntelXAI.db`
- `APP_ENV` - Default: `production`
- `DEBUG` - Default: `false`

The service will be available at: `https://your-project-name.up.railway.app`

## Step 3: Deploy Frontend to Vercel

1. Go to https://vercel.com/new
2. Connect your GitHub repository
3. **IMPORTANT**: Set Root Directory to `frontend`
4. Vercel will auto-detect Next.js
5. Click "Deploy"

### Configure Environment Variables in Vercel

After deployment, go to your Vercel project → Settings → Environment Variables and add:

**Production Environment:**
- `NEXT_PUBLIC_API_URL` = `https://YOUR-RAILWAY-BACKEND-URL.railway.app`
- `NEXT_PUBLIC_WEBINTELX_SDK_URL` = `https://YOUR-RAILWAY-BACKEND-URL.railway.app/sdk/webintelx.js`
- `NEXT_PUBLIC_INGESTION_ENDPOINT` = `https://YOUR-RAILWAY-BACKEND-URL.railway.app/api/ingest/events`

Then redeploy the frontend.

The frontend will be available at: `https://your-project.vercel.app` (or your custom domain)

## Step 4: Update CORS in Railway

After Vercel deployment, update the CORS configuration in Railway:

1. Go to Railway → your project → Variables
2. Find `CORS_ALLOWED_ORIGINS`
3. Update to include your Vercel domain:
   ```
   https://your-vercel-app.vercel.app,https://localhost:3000,http://localhost:3000
   ```
4. Save and redeploy the backend

## Step 5: Verify Deployment

### Backend Health Check
```powershell
curl https://YOUR-RAILWAY-BACKEND-URL.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "application": "WebIntelX AI",
  "environment": "production",
  "database": "connected"
}
```

### Swagger Documentation
Visit: https://YOUR-RAILWAY-BACKEND-URL.railway.app/docs

### Frontend
Visit: https://your-vercel-app.vercel.app

## Step 6: End-to-End Testing

### Test 1 - Backend Health
```powershell
curl https://YOUR-RAILWAY-BACKEND-URL.railway.app/health
```

### Test 2 - Frontend Login
1. Open https://your-vercel-app.vercel.app
2. Register a new user
3. Login

### Test 3 - Website Registration
1. Go to Websites → Add Website
2. Enter name and domain
3. Register the website

### Test 4 - Generate SDK Credential
1. Go to website → Integration
2. Generate WebIntelX credential
3. Copy the credential

### Test 5 - SDK Integration
1. Update the demo HTML file with your backend URL:
   ```html
   <script>
     WebIntelX.init({
       credential: 'YOUR_CREDENTIAL_HERE',
       endpoint: 'https://YOUR-RAILWAY-BACKEND-URL.railway.app/api/ingest/events',
       enabled: true,
       autoTrack: true
     });
   </script>
   ```
2. Open the demo HTML in a browser
3. Generate events

### Test 6 - Verify Telemetry
1. Go to the dashboard
2. Check the website's telemetry
3. Verify events are received

### Test 7 - Findings
1. Check the Findings page
2. Verify detection engine is working

### Test 8 - Investigation
1. Create an investigation
2. Verify CrewAI executes (if LLM API key is configured)

### Test 9 - Risk & Incidents
1. Test risk evaluation
2. Create incidents

## Local Development (After Deployment)

Local development continues to work with the existing configuration:

### Backend
```powershell
cd "E:\Projects\WebIntelX AI"
.venv\Scripts\activate
python start.py
```

Or for development with hot reload:
```powershell
cd "E:\Projects\WebIntelX AI"
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

### Frontend
```powershell
cd "E:\Projects\WebIntelX AI\frontend"
npm run dev
```

## Deployment Limitations

### SQLite Persistence (CRITICAL)
- **Railway's filesystem is ephemeral**
- **SQLite database (`WebIntelXAI.db`) is lost on every redeploy/restart**
- **Data will persist only while the service is running**
- This is acceptable for:
  - Testing
  - Demo
  - Hackathon
  - MVP validation
- **Not suitable for production data persistence**

### Railway Free Tier Limitations
- Service spins down after inactivity
- Spin-up time: varies
- Monthly limit: 500 free hours (may change)
- After free hours, services are suspended until next month
- No persistent disk storage on free tier

### Vercel Free Tier Limitations
- No limitations for this use case
- Automatic deployments
- SSL included

### CrewAI/ML Limitations
- Free tier memory: varies by plan
- ML models (scikit-learn) should work
- CrewAI with Groq may have memory constraints for large investigations
- Set `INVESTIGATION_MAX_EVENTS=50` if experiencing issues

### Groq API Key
- **Never commit to Git**
- Only set in Railway dashboard
- Monitor usage at https://console.groq.com/

## Files Changed

1. **.vercelignore** - New file to prevent Vercel from bundling Python backend
2. **railway.json** - New file for Railway backend deployment
3. **nixpacks.toml** - New file to configure NIXPACKS builder for Railway
4. **Procfile** - New file for alternative Railway startup configuration
5. **start.py** - New startup script that properly reads Railway's PORT environment variable
6. **frontend/vercel.json** - Updated to remove hardcoded backend URLs
7. **frontend/.env.example** - Updated for Railway backend
8. **Dockerfile** - Updated for Railway compatibility and to use start.py
9. **render.yaml** - Deprecated (now using Railway)

## Next Steps After Deployment

1. **Monitor Railway logs** for any startup errors
2. **Test health endpoint** immediately after deployment
3. **Verify database initialization** (check logs for "init_db")
4. **Test complete user flow** (register → login → website → events)
5. **Check free tier usage** (Railway dashboard)
6. **Consider upgrade** if persistence is needed for production

## Troubleshooting

### Backend fails to start
- Check Railway logs: Dashboard → Project → Logs
- Verify `LLM_API_KEY` is set correctly
- Check memory usage

### Frontend cannot connect to backend
- Verify `NEXT_PUBLIC_API_URL` in Vercel environment variables
- Check CORS configuration in Railway
- Ensure backend is running (not spun down)

### SQLite database errors
- Normal on first deploy (database will be created)
- Check logs for database initialization
- Remember: data is ephemeral on free tier

### CrewAI investigation fails
- Verify `LLM_API_KEY` is set
- Check Groq API key is valid
- Reduce `INVESTIGATION_MAX_EVENTS` if hitting memory limits

### Vercel bundle size error
- Ensure Root Directory is set to `frontend` in Vercel
- Check that `.vercelignore` is present at repository root
- Verify no Python files are being bundled

### Railway PORT error
- If you see "'$PORT' is not a valid integer", the deployment should now be fixed
- The fix uses `nixpacks.toml` and `Procfile` to configure Railway's NIXPACKS builder
- `start.py` properly reads the PORT environment variable
- Railway will automatically redeploy after the git push
- Check Railway logs to verify the server starts successfully
