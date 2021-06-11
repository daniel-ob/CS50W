from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from . import util


def index(request):
    if request.method == "POST":
        # coming from search query
        title = request.POST["q"]
        # if query matches an entry, redirect to that entry page
        if util.get_entry(title):
            return HttpResponseRedirect(reverse("entry", kwargs={"title": title}))

        # list entries that have the query as substring
        return render(request, "encyclopedia/index.html", {
            "query": True,
            "entries": [entry for entry in util.list_entries() if title.lower() in entry.lower()]
        })

    # list all entries
    return render(request, "encyclopedia/index.html", {
        "query": False,
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


def create(request):
    if request.method == "POST":
        title = request.POST["title"]
        content = request.POST["content"]
        error_message = ""
        if not (title and content):
            error_message = "Please enter a title and a content"
        if util.get_entry(title):
            error_message = "This page already exists"
        if error_message:
            # present error message and keep form content
            return render(request, "encyclopedia/create.html", {
                "error_message": error_message,
                "title": title,
                "content": content
            })
        else:
            # save entry and redirect user to the new entry's page
            util.save_entry(title, content)
            return HttpResponseRedirect(reverse("entry", kwargs={"title": title}))
    else:
        return render(request, "encyclopedia/create.html")
