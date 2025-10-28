import frappe

@frappe.whitelist()
def save_customer(docname=None, first_name=None, last_name=None, email=None, photo=None, customer_addressx=None):
    customer_addressx = frappe.parse_json(customer_addressx or [])

    if docname:
        # Update existing
        doc = frappe.get_doc("CostomerX", docname)
        doc.first_name = first_name
        doc.last_name = last_name
        doc.email = email
        if photo:
            doc.photo = photo

        # Reset child table
        doc.customer_addressx = []
        for row in customer_addressx:
            doc.append("customer_addressx", {
                "doctype": "Customer AddressX",
                "address_line1": row.get("address_line1"),
                "city": row.get("city"),
                "pincode": row.get("pincode"),
            })
        doc.save()

    else:
        # New insert
        doc = frappe.get_doc({
            "doctype": "CostomerX",
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "photo": photo,
            "customer_addressx": [
                {
                    "doctype": "Customer AddressX",
                    "address_line1": row.get("address_line1"),
                    "city": row.get("city"),
                    "pincode": row.get("pincode"),
                } for row in customer_addressx
            ]
        })
        doc.insert()

    frappe.db.commit()
    return {"status": "success", "docname": doc.name}


@frappe.whitelist()
def get_customers():
    return frappe.get_all("CostomerX", fields=["name", "first_name", "last_name", "email", "photo"])


@frappe.whitelist()
def get_customer(docname):
    return frappe.get_doc("CostomerX", docname).as_dict()


@frappe.whitelist()
def delete_customer(docname):
    frappe.delete_doc("CostomerX", docname)
    frappe.db.commit()
    return {"status": "success"}
