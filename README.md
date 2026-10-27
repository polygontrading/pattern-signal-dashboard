# Pattern Signal Dashboard

Static dashboard for GitHub Pages. It reads the research bot's JSON API; it does not execute trades or calculate signals in the browser.

## Configure

Copy `config.example.js` to `config.js` and set the HTTPS API origin exposed by the Hostinger reverse proxy. Do not place any broker, Futu, Telegram, or database credential in this repository.

## Publish to GitHub Pages

Push this folder to a GitHub repository, enable Pages from the default branch, then set the API origin in `config.js`. The Hostinger API must allow the resulting GitHub Pages origin with CORS and require authenticated access before publication.
