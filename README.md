# Kidsnote photo extraction

I found the original script here https://gist.github.com/Leuconoe/21f6a07f50389c4de1ec127944af7008

I'm adding info to be able to easier use it.

## Installation

```
pipenv install
```

## How to use:

1. Copy the env-sample file to .env
2. Put in your username and password in there
3. Put in the path where you want the pictures stored, it will create a YYYY/MM/DD structure there
4. Run `pipenv run ./get_report.py` to get the report, it stores it in a file report.json
5. Run `pipenv run ./report_json_down.py` to download all the reports and pictures


