## Taiga Backend

[![Managed with Taiga.io](https://img.shields.io/badge/managed%20with-TAIGA.io-709f14.svg)](https://tree.taiga.io/project/taiga/ "Managed with Taiga.io")
[![Tests Status](https://github.com/SkiAn2007/taiga-back/actions/workflows/tests-and-coverall.yml/badge.svg)](https://github.com/SkiAn2007/taiga-back/actions/workflows/tests-and-coverall.yml "Tests Status")

## About this fork
This fork of [taigaio/taiga-back](https://github.com/taigaio/taiga-back) runs on **Django 6.1**, Python 3.12+ and PostgreSQL 15+
with current dependencies. It is a research fork built on upstream pull request 232, not an official Taiga release.
The HTTP API stays compatible with the original `taiga-front`.

### Upgrading from upstream Taiga 6.x
Your existing database is upgraded in place; no export/import is needed.

1. **Back up the database** (`pg_dump -Fc`) and stop the old backend.
2. Make sure PostgreSQL is version 15 or newer and the host runs Python 3.12+ (the Docker image already does).
3. Replace the backend code or image with this fork and install `requirements.txt` (`psycopg` needs `libpq`; use `psycopg[binary]` if it is not installed).
4. Run `python manage.py migrate`. It renames six indexes (attachments, projects, custom attributes) and changes nothing else.
5. **Check your own `config.py`.** Django 5.1 removed `DEFAULT_FILE_STORAGE`, `STATICFILES_STORAGE` and `THUMBNAIL_DEFAULT_STORAGE`;
   they are now ignored without any warning. Move them into `STORAGES` (see `docker/config.py`:
   `"default"` and `"easy_thumbnails"` use `taiga_contrib_protected.storage.ProtectedFileSystemStorage`). Otherwise media URLs lose their
   signed token, and custom storages such as S3 are silently replaced by the local filesystem.
6. Start the new backend and check it against your front end. To roll back, restore the backup and start the old backend.

Try it on a copy first: restore your dump into a second database and start a second instance from the fork's Docker image
(`docker build -f docker/Dockerfile -t taiga-back-django6 .`) against it before touching the live one.

The `upgrade-check` CI job does this automatically with a database created by the original code
(`scripts/upgrade-check/build_reference_db.sh` and `run_upgrade_check.sh`): row counts, index identity and schema are compared.

## Documentation

Currently, we have authored three main documentation hubs:

- **[API](https://docs.taiga.io/api.html)**: Our API documentation and reference for developing from Taiga API.
- **[Documentation](https://docs.taiga.io/)**: If you need to install Taiga on your own server, this is the place to find some guides.
- **[Taiga Resources](https://community.taiga.io/)**: This page is intended to be the support reference page for the users.

## Bug reports

If you **find a bug** in Taiga you can always report it:

- in [Taiga issues](https://tree.taiga.io/project/taiga/issues). **This is the preferred way**
- in [Github issues](https://github.com/taigaio/taiga-back/issues)
- send us a mail to support@taiga.io if is a bug related to [tree.taiga.io](https://tree.taiga.io)
- send us a mail to security@taiga.io if is a **security bug**

One of our fellow Taiga developers will search, find and hunt it as soon as possible.

Please, before reporting a bug, write down how can we reproduce it, your operating system, your browser and version, and if it's possible, a screenshot. Sometimes it takes less time to fix a bug if the developer knows how to find it.

## Community

If you **need help to setup Taiga**, want to **talk about some cool enhancemnt** or you have **some questions**, please go to [Taiga community](https://community.taiga.io/).

If you want to be up to date about announcements of releases, important changes and so on, you can subscribe to our newsletter (you will find it by scrolling down at [https://taiga.io](https://www.taiga.io/)) and follow [@taigaio](https://twitter.com/taigaio) on Twitter.

## Contribute to Taiga

There are many different ways to contribute to Taiga's platform, from patches, to documentation and UI enhancements, just find the one that best fits with your skills. Check out our detailed [contribution guide](https://community.taiga.io/t/how-can-i-contribute/159)

## Code of Conduct

Help us keep the Taiga Community open and inclusive. Please read and follow our [Code of Conduct](https://github.com/taigaio/code-of-conduct/blob/main/CODE_OF_CONDUCT.md).

## License

Every code patch accepted in Taiga codebase is licensed under [MPL 2.0](LICENSE). You must be careful to not include any code that can not be licensed under this license.

Please read carefully [our license](LICENSE) and ask us if you have any questions as well as the [Contribution policy](https://github.com/taigaio/taiga-back/blob/main/CONTRIBUTING.md).
