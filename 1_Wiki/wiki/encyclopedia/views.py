import random

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
# from markdown2 import Markdown

from . import util


def index(request):
    if request.method == "POST":
        # coming from sidebar search query
        title = request.POST["q"]
        # if query matches an entry, redirect to that entry page
        if util.get_entry(title):
            return HttpResponseRedirect(reverse("entry", kwargs={"title": title}))

        # list entries that have the query as substring
        return render(request, "encyclopedia/index.html", {
            "query": True,
            "entries": [entry for entry in util.list_entries() if title.lower() in entry.lower()]
        })

    # Request.GET: list all entries
    return render(request, "encyclopedia/index.html", {
        "query": False,
        "entries": util.list_entries()
    })


def entry(request, title):
    content = util.get_entry(title)
    if not content:
        return render(request, "encyclopedia/notfound.html", {
            "title": title,
        })
    else:
        # markdowner = Markdown()
        # content = markdowner.convert(content)
        content = util.markdown_to_html(content)
        return render(request, "encyclopedia/entry.html", {
            "title": title,
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

    # Request.GET
    return render(request, "encyclopedia/create.html")


def edit(request, title):
    if request.method == "POST":
        util.save_entry(title, request.POST["content"])
        return HttpResponseRedirect(reverse("entry", kwargs={"title": title}))

    # Request.GET
    content = util.get_entry(title)
    if not content:
        return render(request, "encyclopedia/notfound.html", {
            "title": title,
        })
    else:
        return render(request, "encyclopedia/edit.html", {
            "title": title,
            "content": content
        })


def random_entry(request):
    entries = util.list_entries()
    if entries:
        return HttpResponseRedirect(reverse("entry", kwargs={"title": random.choice(entries)}))
    else:
        return render(request, "encyclopedia/notfound.html")
