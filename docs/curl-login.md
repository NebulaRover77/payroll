# Login testing with curl

Use these curl commands to verify the login flow end-to-end from the API that powers `public/login.html`.

## 1) Make sure the API is running

```bash
curl -i http://localhost:8000/health
```

You should see a `200 OK` response with a short JSON body (e.g., `{"status":"ok"}`). If the service is not running, start it according to the project README (for example, `docker compose up backend db` or your preferred dev command).

## 2) Create or reset a user

The login endpoint expects users whose passwords were created via the API so they are hashed correctly. Create a test admin user:

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.test","password":"supersafepassword","role":"admin"}'
```

- On success you should see the user JSON with `id`, `email`, `role`, and `created_at`.
- If the email already exists, delete it from your DB first or pick another email.

## 3) Log in and capture the token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.test","password":"supersafepassword"}'
```

Expected response:

```json
{"access_token":"<JWT>","token_type":"bearer","email":"user@example.test","role":"admin"}
```

If you see `401` with `detail`, the password/email combo does not match a stored user.

To save the token for follow-up requests:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.test","password":"supersafepassword"}' | jq -r .access_token)
echo "$TOKEN"
```

## 4) Use the token against an authenticated endpoint

Replace `<token>` with the token from the previous step (or use `$TOKEN`):

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/users
```

You should receive the list of users. A `401` here indicates the token is missing or invalid.

## 5) Compare with the browser form

The login page posts to `http://localhost:8000/auth/login` with `Content-Type: application/json`. If the curl flow works but the page still fails:

- Open devtools Network tab and confirm the POST matches the curl request (URL, method, headers, and JSON body).
- Check the console for CORS or mixed-content errors (the page expects the API on port 8000).

These steps mirror exactly what the frontend does, so a passing curl flow isolates issues to the browser or environment (e.g., wrong API port, blocked request, or missing HTTPS when required).

## Helper scripts

For quicker iteration, you can run the equivalent curl flows via helper scripts in `scripts/` (override `API_BASE`, `EMAIL`, `PASSWORD`, or `ROLE` as needed):

- `scripts/login-health.sh` — check `GET /health`.
- `scripts/login-create-user.sh` — create a test user via `POST /users`.
- `scripts/login-authenticate.sh` — log in and print the `access_token` to stdout.
- `scripts/login-authenticated-users.sh` — fetch `/users` using a token (reuses `login-authenticate.sh` when `TOKEN` is unset).
