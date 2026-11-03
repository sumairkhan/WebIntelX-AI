# WebIntelX AI Deployment Guide

## Security Alert - Immediate Action Required

**The Groq API key was previously committed to `.env.example`. Please rotate it immediately:**
1. Go to https://console.groq.com/keys
2. Revoke the old key
3. Generate a new key
4. The new key will be added only in Render/Vercel dashboards (never committed to Git)

## Deployment Architecture

- **Backend**: Render (Free Tier) - Python FastAPI with ML/CrewAI
- **Frontend**: Vercel (Free Tier) - Next.js
- **Database**: SQLite (ephemeral - data lost on redeploy)

## Step 1: Push to GitHub

```powershell
# Stage changes
git add .
git commit -m "Add deployment configuration

- Added render.yaml for backend deployment
- Added vercel.json for frontend deployment
- Added Dockerfile for containerized deployment
- Fixed security: removed real Groq API key from .env.example
- Updated .env.example with production environment variables
- Updated .gitignore to exclude .env.local files
- Added frontend/.env.example"

# Push to GitHub
git push origin main
```

## Step 2: Deploy Backend to Render

1. Go to https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the repository
5. **Important**: Select "Existing `render.yaml`" (we created this file)
6. Render will auto-detect the configuration
7. Click "Create Web Service"

### Configure Environment Variables in Render

After deployment, go to your Render service → Environment and add:

**Required (set these manually):**
- `LLM_API_KEY` - Your new Groq API key (generate from https://console.groq.com/keys)

**Optional (already set in render.yaml, but can override):**
- `JWT_SECRET_KEY` - Render will auto-generate this, but you can set your own
- `CORS_ALLOWED_ORIGINS` - Add your frontend domain after Vercel deployment

The service will be available at: `https://webintelx-backend.onrender.com`

## Step 3: Deploy Frontend to Vercel

1. Go to https://vercel.com/new
2. Connect your GitHub repository
3. **Important**: Set Root Directory to `frontend`
4. Vercel will auto-detect Next.js
5. Click "Deploy"

### Configure Environment Variables in Vercel

After deployment, go to your Vercel project → Settings → Environment Variables and add:

**Production Environment:**
- `NEXT_PUBLIC_API_URL` = `https://webintelx-backend.onrender.com`
- `NEXT_PUBLIC_WEBINTELX_SDK_URL` = `https://webintelx-backend.onrender.com/sdk/webintelx.js`
- `NEXT_PUBLIC_INGESTION_ENDPOINT` = `https://webintelx-backend.onrender.com/api/ingest/events`

Then redeploy the frontend.

The frontend will be available at: `https://webintelx-frontend.vercel.app` (or your custom domain)

## Step 4: Update CORS in Render

After Vercel deployment, update the CORS configuration in Render:

1. Go to Render → webintelx-backend → Environment
2. Find `CORS_ALLOWED_ORIGINS`
3. Update to include your Vercel domain:
   ```
   https://webintelx-frontend.vercel.app,https://localhost:3000,http://localhost:3000
   ```
4. Save and redeploy the backend

## Step 5: Verify Deployment

### Backend Health Check
```powershell
curl https://webintelx-backend.onrender.com/health
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
Visit: https://webintelx-backend.onrender.com/docs

### Frontend
Visit: https://webintelx-frontend.vercel.app

## Step 6: End-to-End Testing

### Test 1 - Backend Health
```powershell
curl https://webintelx-backend.onrender.com/health
```

### Test 2 - Frontend Login
1. Open https://webintelx-frontend.vercel.app
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
       endpoint: 'https://webintelx-backend.onrender.com/api/ingest/events',
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
uvicorn app.main:app --reload --port 8000
```

### Frontend
```powershell
cd "E:\Projects\WebIntelX AI\frontend"
npm run dev
```

## Deployment Limitations

### SQLite Persistence (CRITICAL)
- **Render's free tier has ephemeral filesystem**
- **SQLite database (`WebIntelXAI.db`) is lost on every redeploy/restart**
- **Data will persist only while the service is running**
- This is acceptable for:
  - Testing
  - Demo
  - Hackathon
  - MVP validation
- **Not suitable for production data persistence**

### Render Free Tier Limitations
- Service spins down after 15 minutes of inactivity
- Spin-up time: ~1 minute
- Monthly limit: 750 free instance hours
- After 750 hours, services are suspended until next month
- No persistent disk storage on free tier

### Vercel Free Tier Limitations
- No limitations for this use case
- Automatic deployments
- SSL included

### CrewAI/ML Limitations
- Free tier memory: 512MB RAM
- ML models (scikit-learn) should work
- CrewAI with Groq may have memory constraints for large investigations
- Set `INVESTIGATION_MAX_EVENTS=50` if experiencing issues

### Groq API Key
- **Never commit to Git**
- Only set in Render dashboard
- Monitor usage at https://console.groq.com/

## Files Changed

1. **render.yaml** - New file for Render backend deployment
2. **frontend/vercel.json** - New file for Vercel frontend deployment
3. **Dockerfile** - New file for containerized deployment (optional)
4. **.dockerignore** - New file to exclude unnecessary files from Docker
5. **.env.example** - Updated with production environment variables
6. **frontend/.env.example** - New file for frontend environment variables
7. **.gitignore** - Updated to exclude .env.local files
8. **frontend/.gitignore** - Updated to allow .env.example

## Next Steps After Deployment

1. **Monitor Render logs** for any startup errors
2. **Test health endpoint** immediately after deployment
3. **Verify database initialization** (check logs for "init_db")
4. **Test complete user flow** (register → login → website → events)
5. **Check free tier usage** (Render dashboard)
6. **Consider upgrade** if persistence is needed for production

## Troubleshooting

### Backend fails to start
- Check Render logs: Dashboard → Service → Logs
- Verify `LLM_API_KEY` is set correctly
- Check memory usage (512MB limit)

### Frontend cannot connect to backend
- Verify `NEXT_PUBLIC_API_URL` in Vercel environment variables
- Check CORS configuration in Render
- Ensure backend is running (not spun down)

### SQLite database errors
- Normal on first deploy (database will be created)
- Check logs for database initialization
- Remember: data is ephemeral on free tier

### CrewAI investigation fails
- Verify `LLM_API_KEY` is set
- Check Groq API key is valid
- Reduce `INVESTIGATION_MAX_EVENTS` if hitting memory limits
