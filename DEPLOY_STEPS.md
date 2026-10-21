# Put Blood Bridge online — step by step

You need 3 free accounts. Each one has one job:

| Service | Job |
|---|---|
| **Neon** | Stores the data (PostgreSQL database) |
| **GitHub** | Stores your code so Render can read it |
| **Render** | Runs your website + backend 24/7 and gives you the public link |

Time needed: about 30 minutes. No credit card needed.

---

## Step 1 — Neon (database)

1. Go to **https://neon.com** → **Sign up** (use Google or GitHub).
2. Create a project:
   - Project name: `bloodbridge`
   - Region: **AWS US East 2 (Ohio)** (the default). Render is set to run in Ohio too, so they sit next to each other.
   - Click **Create project**.
3. Click **Connect** (top right) → turn on **Show password** → **Copy** the connection string.
   It looks like:
   `postgresql://neondb_owner:XXXX@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
4. Paste it into Notepad and keep it safe. It is like a password; never share it publicly.

**Optional test on your laptop:** in `backend` create a file named `.env` containing
`DATABASE_URL=` followed by your Neon string. Start with `start_bloodbridge.bat` and open
http://localhost:8000/api/health. It should say `"database_engine":"postgresql"`. In Neon → **Tables** you
will see the Blood Bridge tables.

---

## Step 2 — GitHub (upload the code)

1. Create an account at **https://github.com** (if you don't have one).
2. Install **GitHub Desktop** from **https://desktop.github.com** and sign in.
3. In GitHub Desktop: **File → Add local repository…** → choose the `BloodBridge` folder
   (the one that contains `backend`, `frontend` and `render.yaml`) → **Add repository**.
4. Click **Publish repository**:
   - Name: `bloodbridge`
   - Untick **Keep this code private** if your teacher needs to see it.
   - Click **Publish repository**.

Your `.env` file (with the Neon password), `.venv`, `node_modules` and the local database file are **not**
uploaded. They are excluded automatically.

---

## Step 3 — Render (website + backend online)

1. Go to **https://render.com** → **Get Started** → sign up **with GitHub** (allow access to your `bloodbridge` repository).
2. Click **New +** → **Blueprint**.
3. Choose your **bloodbridge** repository → **Connect**.
4. Render reads `render.yaml` and shows one service called **bloodbridge**.
   It asks for **DATABASE_URL** → paste your **Neon connection string** from Step 1.
5. Click **Apply** (or **Deploy Blueprint**).
6. Wait 5–10 minutes. Open the **bloodbridge** service → **Logs**. When you see
   `Application startup complete` it is live.
7. Your public link is shown at the top of the service page, for example:
   **https://bloodbridge-xxxx.onrender.com**
8. Check it: open `https://bloodbridge-xxxx.onrender.com/api/health`. It should say
   `"database":"ok","database_engine":"postgresql"`.

---

## Step 4 — Create your admin account (in Render, no commands)

Admins can't sign up on the website (for security). Render creates the admin for you:

1. Render → your **bloodbridge** service → **Environment** (left menu).
2. Click **+ Add Environment Variable** and add two variables:
   | Key | Value |
   |---|---|
   | `ADMIN_EMAIL` | your email, e.g. `youremail@gmail.com` |
   | `ADMIN_PASSWORD` | a password with at least 8 characters |
3. Click **Save, rebuild, and deploy** (or **Save Changes**). Render restarts in a few minutes.
4. On your site: **Login** → role **ADMIN** → that email and password.

Forgot it later? Change `ADMIN_PASSWORD` in the same place and save. The admin password is updated on the next start.
(Alternative on your own computer: put `DATABASE_URL=...` in `backend/.env` and run `python create_admin.py --email you@example.com`.)

---

## Step 5 — Try it

Open your Render link and:
1. Register a **Hospital / Blood Bank** (set its location) → as Admin, click **Verify Now** for it.
2. Register a **Donor** (set location, tick the screening box).
3. Log out → click **Emergency Blood Request** → fill in your details + the request → submit.
4. The donor gets the alert → **Accept** → the hospital clicks **Confirm Donation**.

---

## Good to know

- **First visit is slow:** the free Render service sleeps after 15 minutes without visitors; the next
  visit takes about a minute. Open the link a minute before your demo.
- **Updating the site later:** change the code, then in GitHub Desktop click **Commit** → **Push origin**.
  Render redeploys automatically.
- **Seeing the data:** Neon → **Tables** or **SQL Editor**, e.g. `SELECT name, email, role FROM users;`
- **Old Netlify link:** not used any more. You can delete that site in Netlify (Site configuration → General → Delete this site) or leave it.

### If something goes wrong

| Problem | Fix |
|---|---|
| Render build fails | Open **Logs**, copy the red lines and ask for help. |
| Health page says `"database":"unreachable"` | Render → service → **Environment** → check `DATABASE_URL` is the full Neon string. Save, then **Manual Deploy**. |
| Error mentions `channel_binding` | Remove `&channel_binding=require` from the end of `DATABASE_URL`. |
| Site shows "Cannot reach the Blood Bridge server" | The service was asleep or still deploying. Wait a minute and refresh. |
