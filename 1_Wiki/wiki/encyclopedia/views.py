from django.shortcuts import render

from . import util


def index(request):
    return render(request, "encyclopedia/index.html", {
        "entries": util.list_entries()
    })


def entry(request, title):
    content = util.get_entry(title)
    if not content:
        content = f"Requested page was not found: {title}"

    return render(request, "encyclopedia/entry.html", {
        "name": title,
        "content": content
    })
