# Accounts

Create these before the data session. Do not put secrets in this repository.

## Earthdata Login

Create a free account at [Earthdata Login](https://urs.earthdata.nasa.gov/).

Searching NASA Earthdata often works without a login. Downloading usually does not. The next sessions will need the login when they pull MODIS, SRTM, or other Earthdata granules.

## GitHub

Create a GitHub repository for Partial Match that can be made public before the Space Apps submission. The project form needs a link a judge can open.

## What stays outside the repo

Passwords, tokens, Earthdata cookies, and the contents of `.netrc` stay on the local machine. Do not paste a username, a password, or a token into this file or any other file in the repo. `.gitignore` ignores `.netrc`, `.env`, and Earthdata cookie files.
