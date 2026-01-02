# Testing pull requests locally

Use these steps to try a pull request while your local checkout stays on `main`.

## 1) Fetch the pull request to a local branch

```bash
git fetch origin pull/23/head:pr-23
```

- Replace `23` with another PR number if needed.
- This creates (or updates) a local branch named `pr-23` without moving your current `main` branch.

## 2) Switch to the fetched branch

```bash
git checkout pr-23
```

## 3) Install and run services (one-time setup per checkout)

From the repo root:

```bash
npm install
npm run dev
```

The dev script starts both the API (port 8000) and frontend (port 3000).

> If you prefer Docker, use `docker-compose up --build` instead; it exposes the same ports.

## 4) Seed a test user (only if needed)

```bash
./scripts/login-create-user.sh
```

This calls `POST /users` with `user@example.test` / `supersafepassword`.

## 5) Log in and test the dashboard

- Visit `http://localhost:3000/login.html` in a browser and log in with the seeded user.
- On success you should land on the dashboard with the left toolbar (Dashboard, Payroll, Employees, Time Tracking, Reports, Settings) and a Log Out button top right.
- If the token is missing/expired, dashboard should redirect you to `/`.

## 6) Optional: verify login via curl

```bash
./scripts/login-health.sh
./scripts/login-authenticate.sh
./scripts/login-authenticated-users.sh
```

These scripts check API health, obtain an access token, and perform an authenticated `/users` request using that token.

## 7) Return to main when finished

```bash
git checkout main
```

Your `main` branch remains untouched throughout; delete the temp branch with `git branch -D pr-23` if you want to clean up.
