From `capstone/baskets` folder, run:

    django-admin makemessages -l LANG
    django-admin makemessages -d djangojs -l LANG

Where `LANG` can be, for example: fr_FR, de_AT, pt_BR...

This will generate translation `.po` files inside `locale/LANG/LC_MESSAGES` folder.

Once all `msgstr` in `.po` files are translated run:

    django-admin compilemessages
