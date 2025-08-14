# Kidsnote backup photo extraction

I found the original script here https://gist.github.com/Leuconoe/21f6a07f50389c4de1ec127944af7008

I'm adding info to be able to easier use it.

## Installation

```
pipenv install
```

## How to use:

1. Copy the env-sample file to .env
2. Put in your username and password
3. Put in the path where you want the pictures stored, it will create a YYYY/MM/DD structure there
4. Run `pipenv run ./get_report.py` to get the report, it stores it in a file report.json
5. Run `pipenv run ./report_json_down.py` to download all the reports and pictures

## Run automatically with a systemd timer

This will run the script every day at midnight or once you wake up your computer:

1. `cp systemd/kidsnote.service ~/.config/systemd/user/`
2. `cp systemd/kidsnote.timer ~/.config/systemd/user/`
3. `systemctl --user daemon-reload`
4. `systemctl --user enable --now kidsnote.timer`

It assumes you already set up the .env file.

## Why username and password?

In the old script you had to get the report manually from the browser.
I added get_report.py which logs in with a headless chromium browser,
gets the report for you so it's possible to automate it with cron.
