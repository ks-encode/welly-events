# Welly Events v1.7 — Eventfinda API

This update uses the official Eventfinda Developer API when GitHub Actions has API credentials. Credentials are **never** written into the repository or the public `events-feed.json`.

## Update GitHub

1. Upload the `WellyOddities` folder from the update ZIP into the **existing `WellyOddities/` folder** in your repository, replacing matching files and retaining your own `index_cache.json` if present.
2. Go to GitHub **Settings → Secrets and variables → Actions → Repository secrets → New repository secret** and create BOTH secrets:
   - `EVENTFINDA_USERNAME` — enter the API username received from Eventfinda.
   - `EVENTFINDA_PASSWORD` — enter the API password received from Eventfinda.
   Use the actual values privately in GitHub. Do **not** put them in the public code, issues, workflow YAML, or this chat.
3. Open `.github/workflows/refresh-and-publish.yml` in GitHub, press the pencil/edit icon, and find the step named `Refresh the public source index`. Give it these environment variables (or replace the workflow file with the included version):

   ```yaml
   - name: Refresh the public source index
     env:
       EVENTFINDA_USERNAME: ${{ secrets.EVENTFINDA_USERNAME }}
       EVENTFINDA_PASSWORD: ${{ secrets.EVENTFINDA_PASSWORD }}
       # Optional: numeric Wellington Region location ID from Eventfinda API
       EVENTFINDA_LOCATION_ID: ${{ vars.EVENTFINDA_LOCATION_ID }}
     run: python WellyOddities/refresh_for_web.py
   ```

4. Commit the changes, go to **Actions → Refresh and publish Welly Oddities → Run workflow**. The Actions log should show a line similar to `Eventfinda API: N page(s), N event records, N valid Wellington dates` if it works.
5. Check **Sources** on the Welly Events website for the new Eventfinda count.

If the log says `Wellington region ID not found`, Eventfinda's `locations` response may require a different search parameter. Look up the Wellington Region numeric ID in the API documentation, then add a repository **variable** named `EVENTFINDA_LOCATION_ID` at **Settings → Secrets and variables → Actions → Variables**. Don't confuse that public numeric ID with the private username/password.

## Behaviour and limitations

- API requests are made only by the Python scraper in GitHub Actions over HTTPS with Basic authentication; the browser only receives event data.
- The code attempts to find the Wellington Region location ID dynamically, then pages through API results, limited to 10 pages × 100 records to avoid unreasonable API usage. The exact availability and quotas of Eventfinda's free tier are controlled by Eventfinda.
- Events with explicitly non-Wellington venues are excluded; events of unknown location are displayed unless users select the hide-unknown checkbox.
- If the API is not configured, the original HTML reader remains as a fallback. If the API fails, GitHub preserves the last successful cache rather than overwriting it with an empty source.
- The test suite uses **simulated API responses**. Live authenticated retrieval is still unverified; check the GitHub Actions logs on your first run.
- If your password has been shared outside a private environment or committed into a public repository, regenerate it before continuing.
