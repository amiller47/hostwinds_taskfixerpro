# Curling Vision Dashboard - Hostwinds Deployment

This folder contains everything needed to deploy the curling dashboard to shared hosting (Hostwinds).

## Folder Structure

Upload these files to your Hostwinds public folder (e.g., `public_html/curling/`):

```
curling/
├── index.html          (main dashboard)
├── coach.html          (coaching review)
├── bingo.html          (bingo game)
├── shot.html           (shot calling)
├── js/
│   └── config.js       (API configuration - auto-detects PHP vs Flask)
├── api/
│   ├── curling_data.php
│   ├── health.php
│   ├── games.php
│   ├── shots.php
│   ├── bingo_card.php
│   ├── bingo_functions.php
│   ├── bingo_occurred.php
│   ├── shot_suggest.php
│   └── shot_analyze.php
└── data/
    ├── games.db        (SQLite database - create if needed)
    ├── dashboard_data.json (current game state)
    └── bingo_cards/    (created automatically)
```

## Quick Deploy

1. **Create folder on Hostwinds:**
   ```
   public_html/curling/
   ```

2. **Upload static files:**
   - `index.html`, `coach.html`, `bingo.html`, `shot.html`
   - `js/config.js`

3. **Upload API folder:**
   - `api/*.php` files

4. **Create data folder:**
   ```
   public_html/curling/data/
   ```
   - Set permissions to 755 (writable by PHP)

5. **Initialize database:**
   - Upload `games.db` from Pi, or let the system create it on first run

## Testing

Once deployed, visit:
- Dashboard: `https://yourdomain.com/curling/`
- Coaching: `https://yourdomain.com/curling/coach.html`
- Bingo: `https://yourdomain.com/curling/bingo.html`
- Shot Calling: `https://yourdomain.com/curling/shot.html`

## Updating Game Data

The dashboard reads from `data/dashboard_data.json`. To update:

1. On Pi: Run `realtime_dashboard.py` to generate data
2. Upload `dashboard_data.json` to `data/` folder
3. Dashboard will auto-refresh

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/curling_data.php` | GET | Current game state |
| `/api/health.php` | GET | Health check |
| `/api/games.php` | GET | List games |
| `/api/shots.php` | GET | Search shots |
| `/api/bingo_card.php` | GET/POST | Bingo card management |
| `/api/bingo_occurred.php` | GET | Events occurred |
| `/api/shot_suggest.php` | POST | Suggest shot |
| `/api/shot_analyze.php` | POST | Analyze shot |

## Troubleshooting

**404 errors:** Make sure `.htaccess` is present (if needed) and PHP is enabled on your hosting plan.

**500 errors:** Check PHP error logs. Ensure `data/` folder is writable.

**No data showing:** Upload `dashboard_data.json` from Pi to `data/` folder.

## Security Notes

- This is a demo/development setup
- For production, add authentication to API endpoints
- Sanitize all user inputs (already done in shot_suggest/analyze)
- Consider rate limiting for public deployment