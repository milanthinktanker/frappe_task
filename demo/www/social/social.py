import frappe

@frappe.whitelist(allow_guest=True)
def get_published_blogs(search=None):
    """Fetch all published blogs with author info (username, city) using Frappe ORM"""
    
    filters = {"status": "Published"}
    
    if search:
        filters["title"] = ["like", f"%{search}%"]
    
    blogs = frappe.get_all(
        "Blog Post2",
        fields=["name", "title", "content", "author", "published_on", "route"],
        filters=filters,
        order_by="published_on desc"
    )

    # Fetch author info for each blog
    for blog in blogs:
        author_info = frappe.db.get_value(
            "Blog User2",
            blog.author,
            ["username", "city"],
            as_dict=True
        )
        if author_info:
            blog["author_name"] = author_info.username
            blog["author_city"] = author_info.city
        else:
            blog["author_name"] = "Unknown"
            blog["author_city"] = ""

    return blogs

def get_context(context):
    # Get all published blogs
    blogs = frappe.get_all(
        "Blog Post2",
        filters={"status": "Published"},
        fields=["title", "route", "author", "published_on", "content"],
        order_by="published_on desc"
    )

    # Truncate content preview (first 200 chars)
    for blog in blogs:
        if blog.content:
            blog.preview = blog.content[:200] + ("..." if len(blog.content) > 200 else "")
        else:
            blog.preview = ""

    context.blogs = blogs
    return context

