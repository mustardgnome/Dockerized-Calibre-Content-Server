# Dockerized Calibre Content Server

A fully containerized setup for running **Calibre** with support for:

- Multiple libraries
- Clean, portable directory structure
- Automatic reverse-proxying through **Caddy**
- Scripts for restoring backups from cloud storage (or any storage location)

Fair warning, this will probably require some fiddling to get the paths correctly with all your libaries, and to get the content server setup. I recommend fiddling with calibres content server first before trying this out. I personally run calibre on my desktop and have this backup script run on a schedule. On a separate computer, i run this setup which pulls from my backup folder periodically through a cron, scans for changes, and redeploys the libraries to the content server. When you first run the docker container, you will have to mount your libraries (and any future libraries). But from there it should work without much issue. 

---

## 📁 Project Structure

```
Dockerized-Calibre-Content-Server
├── docker-compose.yml       # Main Docker service definitions
├── caddy/
│   └── Caddyfile            # Reverse proxy config for domain hosting
├── calibre-config/
│   └── .gitkeep             # Config directory placeholder (real config ignored)
├── calibre-libraries/
│   ├── .gitkeep             # Library directory placeholder (real content ignored)
│   ├── Books Library/       # Your main Calibre library (ignored by git)
│   └── Manga Library/       # Secondary manga library (ignored by git)
└── scripts/
    └── restore_backup.py    # Example restore script for backups
    └── backup_library.py    # Example backup script for your calibre libaries
```

---

## 🐳 Running Calibre via Docker

### Start the service

```bash
docker compose up -d
```

### Stop the service

```bash
docker compose down
```

### Access Calibre

- **Main UI:** http://localhost:8080  
- **Content server:** http://localhost:8082  

If you're using Caddy, the content server is also available at: 

```
https://your-domain-here/library
```

---

## Library Mounts

When you first run the container, you will have to do some setup for calibre at http://localhost:8080. Inside the container it looks as follows:

- `/books` → `./calibre-libraries/Books Library`
- `/manga` → `./calibre-libraries/Manga Library`
- `/config` → `./calibre-config/config`

This allows Calibre to run anywhere without modifying internal paths.

### Adding your real libraries

Copy your existing Calibre libraries into the repo:

```bash
cp -a "/path/to/your/Books Library" "calibre-libraries/"
cp -a "/path/to/your/Manga Library" "calibre-libraries/"
```

Restart Docker:

```bash
docker compose down
docker compose up -d
```

In Initial Setup:

- You will have to find the books mount that we set up in the docker file. You do not want to set up /config/Calibre Library. Click change then search for /books. It should pop up:
<img width="628" height="569" alt="Screenshot 2025-11-25 at 11 47 32 AM" src="https://github.com/user-attachments/assets/9c5a7ab8-fdf4-4599-a729-7de36d4bd845" />

In the Calibre UI:

- Set the library path to `/books`
- Add `/manga` via *Library → Switch/Create Library*
- You will have to the same steps as we did in startup to find the library correctly
- You will also want to change some settings for the content server. Like requiring users, and you will most definitely need to check "Run server automatically when calibre starts".

---

## 🌐 Reverse Proxy (Caddy)

The `caddy/Caddyfile` routes traffic to the Calibre content server. If you want to host this publicly to the internet (at your own risk), this is how it would do it. I set up the /library subdomain here and in the calibre prefrences:
<img width="581" height="80" alt="Screenshot 2025-11-25 at 12 37 31 PM" src="https://github.com/user-attachments/assets/da4e9e69-0186-4685-ac89-97798a9d0932" />

```caddy
replacewithyourdomain.com {
    tls internal
    @calibre path /library*
    reverse_proxy @calibre 127.0.0.1:8082
}
```

### Restart Caddy

If installed via Homebrew:

```bash
brew services restart caddy
```

### Validate config

```bash
caddy validate --config Caddyfile
```

---

## Backup + Restore

A sample restore script (`scripts/restore_backup.py`) shows how to:

- Pull backups from storage
- Extract them into `calibre-libraries/`
- Restart the container

You can adapt it to automate:

- Restoring from Google Drive
- Keeping monthly snapshots
- Detecting changes via `metadata.db` hashing

---

## Useful Commands

Check what the container can see:

```bash
docker exec -it calibre ls /books
docker exec -it calibre ls /manga
```

Tail logs:

```bash
docker logs -f calibre
```

---

## Notes

- Spaces in “Books Library” and “Manga Library” require quotes in `docker-compose.yml`.
- The folders may be **empty in the repo**, but Docker requires them to exist.

---

## Credits

Built using:

- [LinuxServer Calibre Docker image](https://github.com/linuxserver/docker-calibre)
- [Caddy](https://caddyserver.com/)
- Calibre by Kovid Goyal
