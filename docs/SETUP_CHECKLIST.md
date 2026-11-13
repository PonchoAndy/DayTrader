# DayTrader — Setup Checklist

Accounts and credentials to set up before we write the collector. Do them in order;
only steps 1–2 are needed to start. Everything here is free at our scale.

> **Golden rule:** never paste a secret (Client Secret, access keys) into chat, a file in the
> repo, or a commit. Secrets only go into the secret stores named below.

---

## 1. Battle.net Developer Portal — the auction data (required now)

Site: **https://develop.battle.net**

- [ ] Log in with your normal Battle.net account. (The portal may ask you to accept the
      developer terms or secure your account first — follow its prompts.)
- [ ] Go to **API Access** → **Create Client**.
  - Client name: `DayTrader`
  - Redirect URLs: `http://localhost` (we don't use it, but the form wants one)
  - Service URL: leave blank or put the GitHub repo URL
  - Intended use: e.g. "Personal tool to collect and analyze WoW Forever auction house data"
- [ ] Copy the **Client ID** and **Client Secret** into a password manager.
      (If you lose the secret you can generate a new one from the same page.)
- [ ] Note your region (US or EU). The API host is `us.api.blizzard.com` or `eu.api.blizzard.com`.

Rate limits are generous (around 36,000 requests/hour); we'll use about 15–20 per hour.

## 2. Let Claude test with your key (required now, ~1 minute)

So I can write and run the probe script in these cloud sessions without you pasting the key:

- [ ] Tell me "key's ready". I'll pop up a **secure form** for `oauth.battle.net`.
      Put the Client ID as the username and the Client Secret as the password.
- The key is saved on your **DayTrader** cloud environment (only your sessions use it), never
  in chat or the repo. The environment already allows `oauth.battle.net`,
  `us.api.blizzard.com` and `eu.api.blizzard.com`.

## 3. GitHub — scheduler and secret storage (needed when we automate)

Repo: **https://github.com/PonchoAndy/DayTrader**

- [ ] **Decide public vs. private.** This matters for the free Actions budget:
  - **Public repo:** Actions minutes are unlimited and free. Secrets stay secret even in a
    public repo. Your code and analysis would be visible to anyone.
  - **Private repo:** 2,000 free minutes/month. An hourly run that takes ~3 minutes uses
    ~2,200/month, which is just over. We'd run every 2 hours or keep runs short.
- [ ] Add secrets: repo **Settings → Secrets and variables → Actions → New repository secret**
  - `BLIZZARD_CLIENT_ID`
  - `BLIZZARD_CLIENT_SECRET`
  - `BLIZZARD_REGION` (`us` or `eu` — could be a plain variable instead of a secret)
- [ ] Check **Settings → Actions → General** allows actions to run (on by default).
- Gotcha: GitHub turns off scheduled workflows in public repos after 60 days without
  commits. We'll handle that when we get there.

## 4. Cloudflare R2 — where the data lives (needed when we automate)

One full pull of all auction houses is roughly 50–100 MB, every hour. That's too big for
git, so we store files in cheap object storage. R2's free tier: 10 GB storage, no download
fees.

Site: **https://dash.cloudflare.com** (sign up free)

- [ ] Create an account. R2 requires adding a payment card even on the free tier; you won't
      be charged below the free limits. (Alternative with no card: Backblaze B2, 10 GB free.)
- [ ] **R2 → Create bucket** → name `daytrader-data`, location Automatic.
- [ ] **R2 → Manage API tokens → Create API token**
  - Permission: **Object Read & Write**
  - Scope: only the `daytrader-data` bucket
- [ ] Copy the **Access Key ID**, **Secret Access Key** and your **Account ID**
      (shown on the R2 overview page).
- [ ] Add them as GitHub secrets: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.

## 5. Streamlit Community Cloud — the dashboard (later)

Site: **https://share.streamlit.io**

- [ ] Sign in with GitHub and authorize Streamlit to see the DayTrader repo.
- Later, when there's a dashboard to deploy: **Create app** → pick the repo and file, then
  paste the R2 read credentials into the app's **Settings → Secrets**.
- Free apps are public by default; you can limit viewers to specific emails.

## 6. Your own computer (optional)

Not needed — Claude's cloud sessions can do the coding. Only if you want to run things yourself:

- [ ] Python 3.12+ (https://www.python.org/downloads/)
- [ ] Git, and optionally VS Code
- [ ] A `.env` file in the repo folder for your keys (already in `.gitignore`)

---

## Summary: what goes where

| Credential | Get it from | Store it in |
|---|---|---|
| Blizzard Client ID + Secret | develop.battle.net | Password manager, GitHub secrets, Claude's secure form |
| R2 Access Key + Secret + Account ID | Cloudflare dashboard | Password manager, GitHub secrets, Streamlit secrets |
| GitHub login | — | Already connected |
| Streamlit | Sign in with GitHub | No separate credential |
