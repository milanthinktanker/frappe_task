# Copyright (c) 2025, demo and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class BlogPost2(Document):
    def validate(self):
        # Prevent duplicate titles
        if frappe.db.exists("Blog Post2", {"title": self.title, "name": ["!=", self.name]}):
            frappe.throw("A blog post with this title already exists.")

        # Auto-generate clean route (replace spaces/underscores → dashes)
        new_route = frappe.scrub(self.title).replace("_", "-")

        # If route not set or title changed, update it
        if not self.route or self.route != new_route:
            self.route = new_route

        # Ensure route is unique
        existing = frappe.db.exists("Blog Post2", {"route": self.route, "name": ["!=", self.name]})
        if existing:
            # Add a numeric suffix if duplicate route exists
            count = frappe.db.count("Blog Post2", {"route": ["like", f"{self.route}%"]})
            self.route = f"{self.route}-{count + 1}"

    def before_insert(self):
        # Just ensure route exists before insert
        if not self.route:
            self.route = frappe.scrub(self.title).replace("_", "-")


