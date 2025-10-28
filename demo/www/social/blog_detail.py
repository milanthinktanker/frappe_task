import frappe

def get_context(context):
    try:
        route = frappe.form_dict.get("route")
        frappe.logger().info(f"Route param: {route}")

        if not route:
            frappe.throw("No route provided.")

        blog = frappe.db.get_value(
            "Blog Post2",
            {"route": route, "status": "Published"},
            ["name", "title", "content", "author", "published_on", "route"],
            as_dict=True
        )

        if not blog:
            frappe.throw(f"Blog not found or unpublished for route: {route}")

        author = frappe.db.get_value(
            "Blog User2",
            blog.author,
            ["username", "city"],
            as_dict=True
        )

        context.blog = blog
        context.blog_author_name = author.username if author else "Unknown"
        context.blog_author_city = author.city if author else ""

        # # prev blog
        # context.prev_blog = frappe.db.get_value(
        #     "Blog Post2",
        #     {"status": "Published", "published_on": ["<", blog.published_on]},
        #     ["route", "title"],
        #     order_by="published_on desc",
        #     as_dict=True
        # )

        # # next blog
        # context.next_blog = frappe.db.get_value(
        #     "Blog Post2",
        #     {"status": "Published", "published_on": [">", blog.published_on]},
        #     ["route", "title"],
        #     order_by="published_on asc",
        #     as_dict=True
        # )

        return context

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Blog Detail Error")
        frappe.throw(f"Error while loading blog detail: {str(e)}")
