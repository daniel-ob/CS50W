import re

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def list_entries():
    """
    Returns a list of all names of encyclopedia entries.
    """
    _, filenames = default_storage.listdir("entries")
    return list(sorted(re.sub(r"\.md$", "", filename)
                for filename in filenames if filename.endswith(".md")))


def save_entry(title, content):
    """
    Saves an encyclopedia entry, given its title and Markdown
    content. If an existing entry with the same title already exists,
    it is replaced.
    """
    filename = f"entries/{title}.md"
    if default_storage.exists(filename):
        default_storage.delete(filename)
    default_storage.save(filename, ContentFile(content))


def get_entry(title):
    """
    Retrieves an encyclopedia entry by its title. If no such
    entry exists, the function returns None.
    """
    try:
        f = default_storage.open(f"entries/{title}.md", "r")
        return f.read()
    except FileNotFoundError:
        return None


def markdown_to_html(content):
    """
    Converts content string from Markdown to HTML
    """
    # Headings (from 1 to 6):
    # content = re.sub(r'(^|\n)#{2} (.*)\n', r'\1<h2>\2</h2>\n', content)
    for i in range(1, 7):
        pattern = '(^|\n)#{' + str(i) + '} (.+)\n'
        repl = '\\1<h' + str(i) + '>\\2</h' + str(i) + '>\n'
        content = re.sub(pattern, repl, content)

    # Bold
    content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)

    # Italic (needs previous bold substitution)
    content = re.sub(r'\*([^ ][^*]+)\*', r'<em>\1</em>', content)

    # Code
    content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)

    # Unordered lists
    content = re.sub(r'\n(([-|*] .*\n)+)\n', r'\n<ul>\n\1</ul>\n\n', content)
    content = re.sub(r'\n[-|*] (.*)', r'\n<li>\1</li>', content)

    # Ordered lists
    content = re.sub(r'\n((\d+\. .*\n)+)\n', r'\n<ol>\n\1</ol>\n', content)
    content = re.sub(r'\n\d+\. (.*)', r'\n<li>\1</li>', content)

    # Links
    content = re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', content)

    # Paragraphs
    content = re.sub(r'^\s(.+)\s$', r'\n<p>\1</p>\n', content, flags=re.MULTILINE)

    return content
