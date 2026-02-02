# Part Vault

This is Part Vault. Yet another inventory management program that allows you to keep track of what you have, where it is and what it looks like.

## Description

Part Vault was created to keep track of my collection of vintage computers and parts, but it can be used for any collection of items.

Built with Python and Django

### Features

- Self hosted
- Multi-user
- Multi-collection
- Private / Public collections
- Photo uploads directly from mobile camera
- Attachments

### Screenshots

#### Homepage
![Image](https://github.com/user-attachments/assets/19e0e0ff-e95f-450c-845f-34517e28cb27)
#### Item List
![Image](https://github.com/user-attachments/assets/bea6b15b-7890-43da-8145-04af3a558128)
#### Item Detail
![Image](https://github.com/user-attachments/assets/7886e49a-b703-46fd-b87a-6144b14c4b62)

## Getting Started

Note, instructions below are to get started with a dev instance, instructions to run in production mode to follow later.

### Prerequisites

- [Python 3](https://www.python.org/downloads/)
- [uv](https://github.com/astral-sh/uv) (Python Package Manager)
- Django (will be installed automatically)
- Database supported by Django (defaults to SQLite)

### Install

- git clone https://github.com/andremiller/django-partvault.git
- cd django-partvault.git
- uv sync

### Configure

- Edit config/settings.py (or create local_settings.py) and edit it to configure your database, timezone and other settings
- uv run manage.py migrate (Also re-run after updating)
- uv run manage.py createsuperuser

### Usage

- uv run manage.py runserver
- Open http://localhost:8000/
- Open http://localhost:8000/admin for admin view

## Back Matter

### Legal disclaimer

Developers assume no liability and are not responsible for any misuse or damage caused by this program.

### See also

- [Snipe-IT](https://github.com/grokability/snipe-it)
- [GLPI](https://github.com/glpi-project/glpi)

### License

This project is licensed under the [GPL-3.0 license](LICENSE.md).
