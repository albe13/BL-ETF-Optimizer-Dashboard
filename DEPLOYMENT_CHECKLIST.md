# Deployment checklist — BL ETF Optimizer (private GitHub + private Streamlit Community Cloud)

This checklist describes the **manual** steps the owner performs. Nothing in this package connects to GitHub or Streamlit by itself.
Target: private repository `albe13/BL-ETF-Optimizer-Dashboard`, branch `main`, entry point `streamlit_app.py` at the repository root.

## What to upload

Upload the **contents** of `BL_ETF_OPTIMIZER_STREAMLIT_DEPLOY/` — not the folder itself — so that the repository root looks like this:

```
streamlit_app.py   requirements.txt   README.md   DEPLOYMENT_CHECKLIST.md   .gitignore   .streamlit/config.toml
bldash/            artifacts/         docs/       tools/
```

`docs/PACKAGE_INVENTORY.md` lists every file with its size and sha256; compare it with the repository after the upload if in doubt.
Do **not** upload anything else from the research project (no `data/`, `outputs/`, `src/`, `research/`, Bloomberg workbooks or the
original dashboards).

## Important: hidden files and the browser upload

GitHub's browser interface (*Add file → Upload files*) relies on your operating system's file picker or drag-and-drop. Files and folders whose
names start with a dot — `.gitignore` and `.streamlit/config.toml` — are hidden by macOS Finder and Windows Explorer by default and are
frequently **skipped** in that workflow. The app still runs without them (Streamlit falls back to its default theme and toolbar), but the
intended theme, the "no usage statistics" setting and the ignore rules would be missing. Use one of the reliable methods below.

**Reliable method A — git command line (recommended).** From a terminal, inside the deployment folder:

```bash
cd BL_ETF_OPTIMIZER_STREAMLIT_DEPLOY
git init
git add -A
git status                       # confirm that .gitignore and .streamlit/config.toml are listed
git commit -m "BL ETF Optimizer dashboard — private deployment package"
git branch -M main
git remote add origin https://github.com/albe13/BL-ETF-Optimizer-Dashboard.git
git push -u origin main
```

If the private repository already contains files (for example a README created on GitHub), either delete them on GitHub first, or run
`git pull origin main --allow-unrelated-histories` before the push and resolve the README conflict by keeping this package's README.
GitHub asks for your GitHub credentials (a personal access token or the GitHub CLI login); never store them in the repository.

**Reliable method B — GitHub Desktop.** *File → Add local repository* → choose the deployment folder → *create a repository* when asked →
*Publish repository* → tick **Keep this code private** and pick the existing repository name, or publish and then move the content.
GitHub Desktop shows hidden files in its changes list, so `.gitignore` and `.streamlit/config.toml` are included.

**Fallback for the browser upload.** If you must use *Upload files*, upload the visible content first, then add the two hidden files by
hand: *Add file → Create new file*, type the path `.streamlit/config.toml` as the file name, paste the content of that file, commit; repeat
for `.gitignore`. Check afterwards that the repository root shows `streamlit_app.py`, `requirements.txt`, `bldash/` and `artifacts/`.

## Step-by-step

1. **Open the private GitHub repository** `albe13/BL-ETF-Optimizer-Dashboard` and confirm in *Settings → General → Danger zone* that its
   visibility is **Private**.
2. **Upload the CONTENTS of `BL_ETF_OPTIMIZER_STREAMLIT_DEPLOY/`** with method A or B above (or the browser fallback).
3. **Commit the uploaded files** to branch `main` (method A commits before pushing; GitHub Desktop and the browser ask for a commit message).
   Verify on GitHub that `streamlit_app.py` is at the root and that `artifacts/ARTIFACT_MANIFEST.json` and the ten `artifacts/<source>/` folders
   are present (103 data files).
4. **Open Streamlit Community Cloud** at https://share.streamlit.io and sign in with the GitHub account that owns (or can access) the repository.
   Grant the Streamlit GitHub app access to the private repository when asked.
5. **Select the GitHub repository**: *Create app* → *Deploy a public app from GitHub* (this is also the path for private repositories) →
   repository `albe13/BL-ETF-Optimizer-Dashboard`.
6. **Select branch `main`.**
7. **Set the main file path to `streamlit_app.py`.** Choose an app URL (subdomain) if you want one; it will not be public once sharing is restricted.
   Open *Advanced settings*: Python version **3.11** (3.12 also works; do **not** choose 3.13), secrets: leave empty. Click *Deploy*.
   The first build installs the pinned requirements (a few minutes); the log should end with the app running.
8. **Configure private application access.** Apps deployed from a private repository are restricted to invited viewers. Open the app's
   *Settings → Sharing* and make sure the option that limits viewing to specific people is selected (the free Community tier allows a
   limited number of private apps; check the plan if the option is greyed out).
9. **Verify the application is not public.** Open the app URL in a private browser window (not signed in): it must ask to sign in and refuse
   access. The app must not appear in any public gallery.
10. **Invite authorized viewers** in *Settings → Sharing* by e-mail address. Viewers sign in with the Google, GitHub or Streamlit account that
    matches the invited e-mail. Remind them that the data is licensed for their private use only.
11. **Test all ten pages**: Executive Overview, Portfolio Allocation, ETF Market Performance, Performance Analytics, Black-Litterman Engine,
    Macro Regime & Economic Outlook, Trend & Signal Analytics, Historical Portfolio Decisions, Model Methodology, Limitations & Future
    Improvements. The sidebar must show "Data source: deployment bundle"; move the decision date (previous / next / selector) and confirm that
    pages 2, 5, 6, 7 and 8 follow it.
12. **Verify the ETF historical charts** on *ETF Market Performance*: the comparative chart shows ten lines, section B shows ten panels
    (five rows of two) with CAGR, volatility, Sharpe, drawdown and total return, and the risk tabs (drawdowns, rolling volatility, correlation
    matrix, comparative table, identity and audit) are populated. If the page shows the yellow note "ETF total-return series not included",
    the `artifacts/m0/weights_history.csv` file did not reach the repository.

## If something goes wrong

- "No published artifacts found": `artifacts/ARTIFACT_MANIFEST.json` is missing at the repository root → re-upload `artifacts/`.
- "Artifact verification failed": a bundled file was altered during the upload (for example a CSV re-saved by a spreadsheet) → re-upload the
  original file; `docs/PACKAGE_INVENTORY.md` gives the expected sha256 of every file.
- "Required artifacts are missing": the list names the tables → re-upload the corresponding `artifacts/<source>/` folder.
- Build error mentioning numpy or pyarrow wheels: the Python version is 3.13 → set 3.11 or 3.12 in *Advanced settings* and reboot the app.
- To reboot or redeploy: *Manage app → Reboot*; every push to `main` redeploys automatically.

## Updating the data later

A new frozen run of the models requires rebuilding `artifacts/` in the source project with `python3 tools/build_bundle.py --include-review`
(from a copy of this package placed inside the project), re-running `python tools/verify_package.py`, and pushing the new `artifacts/` and
`docs/`. Never edit the CSV files by hand: any change breaks their hash and the loader refuses the table.
