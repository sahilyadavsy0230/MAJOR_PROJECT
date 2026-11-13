# Deploying Prashant Group to Vercel (Free Serverless Deployment)

This guide walks you through deploying the complete **Prashant Group Workforce Platform** on **Vercel** for 100% free temporary or demo hosting.

---

## ⚡ Architecture Overview

| Layer | Service | Cost |
|---|---|---|
| **Frontend & FastAPI API** | Vercel Serverless Functions (`api/index.py`) | Free (Hobby Tier) |
| **Database** | Neon.tech Serverless PostgreSQL | Free Forever (0.5 GiB) |
| **Email Service** | Gmail SMTP / Resend | Free |
| **SSL / HTTPS** | Automatic wildcard SSL on `*.vercel.app` | Free |

---

## Step 1: Push Latest Changes to GitHub

In your PowerShell terminal, run:

```powershell
cd "C:\Users\sahil\OneDrive\Attachments\Desktop\PrashantGroup"
git push origin main
```

---

## Step 2: Get a Free Cloud PostgreSQL Database (2 Minutes)

Because Vercel runs in the cloud, it cannot reach `localhost:5432` on your laptop. You need a free cloud database:

1. Go to **[https://neon.tech](https://neon.tech)** and click **Sign Up** (Sign in with your GitHub account).
2. Click **Create Project**:
   - Project Name: `prashant-group`
   - Region: `AWS / ap-southeast-1 (Singapore)` or `eu-central-1` (or whichever is closest)
   - PostgreSQL version: `16` or `17`
3. Click **Create Project**.
4. In the dashboard, copy the **Connection details** (Select **SQLAlchemy** or **Connection String**):
   ```
   postgresql://prashant_owner:password@ep-xyz.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
   *(Keep this connection string handy for Step 4)*

> **Automatic Schema Setup:** Our app is already pre-configured to detect new databases and automatically create all tables and the default admin user (`admin@prashantgroupindia.in` / `admin123`) on startup!

---

## Step 3: Import Project into Vercel

1. Go to **[https://vercel.com](https://vercel.com)** and sign in with your GitHub account (`sahilyadavsy0230`).
2. Click the **Add New...** button and select **Project**.
3. Under **Import Git Repository**, locate your repo (`MAJOR_PROJECT` or `PrashantGroup`) and click **Import**.

---

## Step 4: Configure Project & Environment Variables

1. In the Vercel project configuration screen:
   - **Framework Preset:** Leave as `Other`
   - **Root Directory:** `./` (default)
2. Expand the **Environment Variables** section and add the following 7 variables:

| Variable Name | Value | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | Enables security headers & HSTS |
| `DEBUG` | `False` | Disables debug mode in prod |
| `SECRET_KEY` | `5b019183bf8e05259c46ae69e44810aa70613317ee92f8d599956d3d8f1ff8cc` | 256-bit cryptographic secret |
| `DATABASE_URL` | *(Paste your Neon.tech connection string from Step 2)* | Cloud PostgreSQL database |
| `ALLOWED_ORIGINS` | `["*"]` | Cross-Origin permissions |
| `SMTP_USER` | `sahilyadavsy0230@gmail.com` | Email notifications |
| `SMTP_PASS` | `rqugkogbvdncxnev` | Gmail App Password |

---

## Step 5: Click "Deploy"

1. Click the blue **Deploy** button.
2. Vercel will install dependencies from `requirements.txt`, bundle `api/index.py`, and launch your app.
3. Once complete, you will see confetti and your live URL:
   ```
   https://prashant-group.vercel.app (or your project slug)
   ```

---

## Step 6: Verify Live Deployment

1. Open your live URL in the browser: `https://your-app.vercel.app`
2. Test the public pages:
   - `/` (Home)
   - `/jobs` (Careers)
   - `/contact` (Submit an inquiry)
3. Check the health check:
   - `https://your-app.vercel.app/health` (Should return `{"status": "healthy", "database": "connected"}`)
4. Log into the Admin Dashboard:
   - URL: `https://your-app.vercel.app/login`
   - Email: `admin@prashantgroupindia.in`
   - Password: `admin123`
