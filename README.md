# TheGrail
Pentesting note taking tool


# PentestNotes

A self-hosted knowledge base for penetration-testing notes. The read surface is
public and input-free (except search); everything that changes data sits behind
login and a per-folder permission system.

Built to be **manageable and long-lived**: Django + SQLite (one file), Django's
built-in admin as the management surface, WhiteNoise for static files, gunicorn
+ Caddy + systemd for an always-on service that survives reboots.

---

## What's built (this layer)

- **Content model** — a tree of Folders holding Pages. Each Page has two
  independent Markdown bodies: **Knowledge** and **Testing**, shown as tabs.
- **Public read site** — the approved layout, rendered from the database:
  folder tree, breadcrumbs, Knowledge/Testing tabs, files, tags, contributors,
  and a **Further Reading** section that is external links only (a `URLField`
  rejects internal paths).
- **Accounts & groups** — `Administrator`, `Senior`, `Junior`, each with a
  default capability loadout.
- **Permissions** — Grants give a user or group capabilities
  (`view`, `edit`, `create_child`, `upload`, `delete`) on a folder; grants
  **inherit** down the tree. Capabilities pre-fill from the group loadout and can
  be trimmed or extended per grant. Enforcement runs on the real object every
  request — private content 404s for anyone without access and is hidden from the
  tree.
- **Files** — upload/attach via admin; downloads honor the parent page's
  visibility.
- **User & password management** — an admin-only Users page (`/users/`) to
  create users with a set password and group, and to reset any user's password
  at any time. Every logged-in user can change their own password at
  `/account/password/` (needs their current one). No email/SMTP required.
  Passwords are validated (min length, not all-numeric, not common) and stored
  hashed.
- **Management** — the Django admin at `/manage/` creates folders, writes pages
  (both tabs), attaches files, adds external links, and manages grants.

- **In-page editor** — a Markdown editor with a formatting toolbar (bold,
  italic, inline code, headings, lists, quote, code block, link, table), a
  live **Preview** that uses the site's own renderer (so preview == published),
  in-page file upload/remove, tag editing, Further-Reading link rows, and
  folder/page creation. All gated by the permission engine; every save bumps the
  version and records the contributor. No JS build step, no frontend
  dependencies.

### Not yet built (possible next layers)
- Per-page version history / diffs beyond the simple `version` counter.
- Drag-to-reorder folders; move-page-between-folders UI (admin can already do this).

---

## Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # groups + the demo RDP page
python manage.py createsuperuser    # then add this user to the Administrator group in /manage/
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`. The demo page is under Lateral Movement → RDP
Protocol → Command Execution. Manage at `http://127.0.0.1:8000/manage/`.

> New admins: create the user, then in `/manage/` open Users → your user → add
> the **Administrator** group. Admin membership is what grants global access.

---

## Deploy on a Linode VM (Ubuntu)

A Nanode (1 GB / 25 GB) is plenty; the app and DB are tiny. Uploaded files are
what consume disk, so watch `media/`.

```bash
# 1. System packages
sudo apt update && sudo apt install -y python3-venv sqlite3 caddy git ufw

# 2. App user + code
sudo useradd -m -d /opt/pentestnotes -s /bin/bash pentest
sudo -u pentest bash -c '
  cd /opt/pentestnotes
  git clone <your-repo> . || true      # or copy this folder here
  python3 -m venv venv
  ./venv/bin/pip install -r requirements.txt
  cp .env.example .env                  # then edit .env (see below)
'

# 3. Configure .env — set a real PN_SECRET_KEY and your domain:
python3 -c "import secrets; print(secrets.token_urlsafe(64))"   # paste into PN_SECRET_KEY

# 4. Initialize
sudo -u pentest bash -c '
  cd /opt/pentestnotes && set -a && . ./.env && set +a
  ./venv/bin/python manage.py migrate
  ./venv/bin/python manage.py seed_demo
  ./venv/bin/python manage.py collectstatic --noinput
  ./venv/bin/python manage.py createsuperuser
'

# 5. Service (always on, restarts on reboot/crash)
sudo cp deploy/pentestnotes.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now pentestnotes

# 6. TLS + reverse proxy
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile   # edit the domain first
sudo systemctl restart caddy

# 7. Firewall
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable
```

DNS: point an A record at the Linode IP before step 6 so Caddy can get a cert.

---

## Users & passwords

Create the first administrator (do this once, on the server — the password is
passed as an argument so it never lives in a source file):

```bash
python manage.py create_user rp01_admin --group Administrator --password 'YOUR-PASSWORD'
# omit --password to be prompted securely instead
```

After that, manage everyone from the app itself (logged in as an admin):

| Task | Where |
|---|---|
| Create a user (set password + group) | `/users/` -> New user |
| Reset someone's password | `/users/` -> Reset password |
| Change your own password | `/account/password/` (top-right -> Password) |

Groups: **Administrator** (global access + user management), **Senior**,
**Junior** (both read-only until granted a folder). The same `create_user`
command works for any group, e.g. `--group Junior`.

> Optional: a self-service *forgot-password* email flow can be added if you
> configure an SMTP server. Until then, an admin reset covers it — which is
> appropriate for a small, trusted team.

## Backups (do this — it's your whole safety net)

SQLite is one file, so backups are trivial but essential:

```bash
sudo cp deploy/backup.sh /opt/pentestnotes/deploy/
sudo -u pentest crontab -e
# add:
0 3 * * * /opt/pentestnotes/deploy/backup.sh
```

This writes a consistent DB copy + a media tarball nightly and keeps the last 14.
**Copy the backups off the box too** (Linode Object Storage or `rsync` to another
host) — a backup that only lives on the same VM won't survive losing the VM.

---

## Hardening notes (this holds offensive-security content — take it seriously)

- SSH keys only; disable password auth in `/etc/ssh/sshd_config`.
- Keep the box patched (`unattended-upgrades`).
- `PN_DEBUG=false` in production (enables secure cookies, HSTS, SSL redirect —
  already wired in `settings.py`).
- Put genuinely sensitive, client-specific findings in **private** folders. Public
  means world-readable — treat it that way.
- Review grants periodically: who can see/edit what. Admin membership = global.

---

## Everyday management

| Task | Where |
|---|---|
| Create a folder / page | `/manage/` → Folders / Pages |
| Edit a page's two tabs | `/manage/` → Pages → (page) → Knowledge / Testing fields |
| Attach a file | Pages → (page) → Files inline |
| Add external reading link | Pages → (page) → External links inline |
| Make something private | set its Visibility to Private |
| Give someone access | `/manage/` → Grants → add (folder + user/group + caps) |
| Add a user to a group | `/manage/` → Users → (user) → Groups |

Content is Markdown, so it's portable and exports cleanly if you ever move hosts.
