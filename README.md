# Regnværktøj

A Danish-language browser app for exploring municipal precipitation data from the Danish Meteorological Institute (DMI). [Open the hosted app](https://mlyngsoe.github.io/kommunal_regn/).

## Website

The app is a static HTML page. It has no build step and can be hosted with GitHub Pages. The page loads Leaflet from unpkg and fetches DMI and municipality-boundary data from external services, so those services must be reachable in the visitor's browser.

To run it locally, open [`docs/index.html`](docs/index.html) in a browser. For local testing, a simple static HTTP server also works:

```powershell
python -m http.server 8000 --directory docs
```

Then visit <http://localhost:8000>.

## Development workflow

Create a branch for each change, make and test the change locally, then commit and push it:

```powershell
git switch -c my-change
git add .
git commit -m "Describe the change"
git push -u origin my-change
```

Open a pull request on GitHub and merge it into `main` when ready to publish. Git history keeps earlier versions of the app.

## DMI test script

[`dmi_test.py`](dmi_test.py) is a separate helper script for querying DMI municipal precipitation data. It requires Python plus `requests` and `pandas`:

```powershell
python -m pip install requests pandas
python dmi_test.py --municipality 0751 --name Aarhus --start 2016 --end 2025
```

Generated files go into `dmi_test_output/`, which is intentionally excluded from Git.
