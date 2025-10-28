import frappe
from frappe.utils.file_manager import save_file
import hmac
from frappe.utils.password import get_decrypted_password
import io
import csv
from frappe.utils import strip_html, now_datetime
import requests
import re

# Create Blog User
@frappe.whitelist(allow_guest=True)
def create_user(name, email, password, mobile=None, address=None, country=None, state=None, city=None, pincode=None, gender=None):

    required_fields = {
        "name": name,
        "email": email,
        "password": password,
        "mobile": mobile,
        "address": address,
        "country": country,
        "state": state,
        "city": city,
        "pincode": pincode
    }
    
    validation_errors = {}
    
    for field_name, field_value in required_fields.items():
        if not field_value or str(field_value).strip() == "":
            validation_errors[field_name] = f"{field_name.replace('_', ' ').title()} is required"

    if email and email.strip():
        if not frappe.utils.validate_email_address(email):
            validation_errors["email"] = "Invalid email address"

        elif frappe.db.exists("Blog User", {"email": email}):
            validation_errors["email"] = "User with this email already exists"
    

    if password and password.strip():
        if len(password) < 8:
            validation_errors["password"] = "Password must be at least 8 characters long"
        elif not re.search(r'[A-Z]', password):
            validation_errors["password"] = "Password must contain at least one capital letter"
    
    if validation_errors:
        return {
            "error" : True,
            "status_code": 422,
            "message": "Validation failed",
            "required_fields": validation_errors
        }
    
    if not gender and name:
        try:

            first_name = name.strip().split()[0]
            response = requests.get(f"https://api.genderize.io/?name={first_name}", timeout=5)
            if response.status_code == 200:
                data = response.json()

                if data.get("gender") and data.get("probability", 0) > 0.6:
                    gender = data.get("gender").capitalize()  
                else:
                    gender = "Other"  
            else:
                gender = "Other"
        except Exception as e:
            frappe.log_error(f"Gender API Error: {str(e)}", "Genderize API")
            gender = "Other" 
    
    try:
        user_doc = frappe.get_doc({
            "doctype": "Blog User",
            "full_name": name,
            "email": email,
            "password": password,
            "mobile": mobile,
            "address": address,
            "country": country,
            "state": state,
            "city": city,
            "pincode": pincode,
            "gender": gender or "Other"
        })
        user_doc.insert(ignore_permissions=True)
        frappe.db.commit()

        # Send welcome email
        frappe.sendmail(
            recipients=email,
            subject="Welcome to Social Media 🎉",
            message=f"""
            <h3>Hello {name},</h3>
            <p>Your account has been successfully created!</p>
            <p><b>Email:</b> {email}<br>
            <b>Password:</b> {password}</p>
            <p>Login and start posting 🚀</p>
            """
        )
        return {
            "error" : False,
            "status_code": 200,
            "message": "User created & welcome email sent",
        }
    
    except Exception as e:
        frappe.db.rollback()
        return {"status": "error", "message": str(e)}
    
# Get All Blog User
@frappe.whitelist(allow_guest=True)
def get_users():
    try:
        users = frappe.get_all("Blog User", fields=["*"], order_by="creation desc")
        return {
            "status": "success",
            "data": users,
            "count": len(users)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Update Blog User
@frappe.whitelist(allow_guest=True)
def update_user(user_id=None, **kwargs):

    if not user_id or str(user_id).strip() == "":
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": {
                "user_id": "User Id is required"
            }
        }
    
    if not frappe.db.exists("Blog User", user_id):
        return {
            "status": "error",
            "message": "User does not exist"
        }
    
    if 'email' in kwargs:
        return {
            "status": "error",
            "message": "You can't change email"
        }
    
    try:
        user_doc = frappe.get_doc("Blog User", user_id)
        
        if 'password' in kwargs:
            password = kwargs.get('password')
            if password and password.strip():
                if len(password) < 8:
                    return {
                        "status": "error",
                        "message": "Validation failed",
                        "required_fields": {
                            "password": "Password must be at least 8 characters long"
                        }
                    }
                elif not re.search(r'[A-Z]', password):
                    return {
                        "status": "error",
                        "message": "Validation failed",
                        "required_fields": {
                            "password": "Password must contain at least one capital letter"
                        }
                    }
        
        for key, value in kwargs.items():
            if hasattr(user_doc, key) and key != 'email':
                setattr(user_doc, key, value)
        
        user_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"User {user_id} updated successfully"
        }
    
    except Exception as e:
        frappe.db.rollback()
        return {"status": "error", "message": str(e)}

 # Delete Blog User
@frappe.whitelist(allow_guest=True)
def delete_user(user_id=None):
    # Validate user_id
    if not user_id or str(user_id).strip() == "":
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": {
                "user_id": "User Id is required"
            }
        }
    
    if not frappe.db.exists("Blog User", user_id):
        return {
            "status": "error",
            "message": "User does not exist"
        }
    
    try:
        
        posts = frappe.get_all("Blog Post1", filters={"user": user_id}, pluck="name")
        for post_id in posts:
          
            likes = frappe.get_all("Blog Like1", filters={"post": post_id}, pluck="name")
            for like in likes:
                frappe.delete_doc("Blog Like1", like, ignore_permissions=True)
            
            frappe.delete_doc("Blog Post1", post_id, ignore_permissions=True)
        
        # Delete user's likes on other posts
        user_likes = frappe.get_all("Blog Like1", filters={"user": user_id}, pluck="name")
        for like in user_likes:
            frappe.delete_doc("Blog Like1", like, ignore_permissions=True)
        
        frappe.delete_doc("Blog User", user_id, ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"User {user_id} deleted successfully with all posts and likes"
        }
    
    except Exception as e:
        frappe.db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }
    
# Create Blog Post
@frappe.whitelist(allow_guest=True)
def create_post(title=None, description=None, content=None, category=None, user=None):
  
    required_fields = {
        "title": title,
        "description": description,
        "content": content,
        "category": category,
        "user": user
    }
    
    validation_errors = {}

    for field_name, field_value in required_fields.items():
        if not field_value or str(field_value).strip() == "":
            validation_errors[field_name] = f"{field_name.replace('_', ' ').title()} is required"
    
    image_file = frappe.request.files.get('image')
    if not image_file:
        validation_errors["image"] = "Image is required"
    
    if validation_errors:
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": validation_errors
        }
    
    if not frappe.db.exists("Blog User", user):
        validation_errors["user"] = "User does not exist"
    
    if validation_errors:
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": validation_errors
        }
    
    image = None
    try:
        image_doc = save_file(
            fname=image_file.filename,
            content=image_file.stream.read(),
            dt=None,
            dn=None,
            folder='Home/Attachments',
            is_private=0
        )
        image = image_doc.file_url
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to upload image",
            "error": str(e)
        }
    
    try:
        post_doc = frappe.get_doc({
            "doctype": "Blog Post1",
            "title": title,
            "description": description,
            "content": content,
            "category": category,
            "user": user,
            "image": image
        })
        post_doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "post_id": post_doc.name, "image_url": image}
    
    except Exception as e:
        frappe.db.rollback()
        return {"status": "error", "message": str(e)}


# Get All Blog Post
@frappe.whitelist(allow_guest=True)
def get_posts():
    try:
        posts = frappe.get_all("Blog Post1", fields=["*"], order_by="creation desc")
        return {
            "status": "success",
            "data": posts,
            "count": len(posts)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Update Blog Post
@frappe.whitelist(allow_guest=True)
def update_post(post_id=None, user_id=None, **kwargs):
    validation_errors = {}
    
    if not post_id or str(post_id).strip() == "":
        validation_errors["post_id"] = "Post Id is required"
    
    if not user_id or str(user_id).strip() == "":
        validation_errors["user_id"] = "User Id is required"
    
    if validation_errors:
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": validation_errors
        }
    
    if not frappe.db.exists("Blog Post1", post_id):
        validation_errors["post_id"] = "Post does not exist"
    
    if not frappe.db.exists("Blog User", user_id):
        validation_errors["user_id"] = "User does not exist"
    
    if validation_errors:
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": validation_errors
        }
    
    try:
        post_doc = frappe.get_doc("Blog Post1", post_id)
        
        # Check if the user is the owner
        if post_doc.user != user_id:
            return {
                "status": "error",
                "message": "Access Denied: You can only update your own posts"
            }
        
        image_file = frappe.request.files.get('image')
        if image_file:
            try:
                image_doc = save_file(
                    fname=image_file.filename,
                    content=image_file.stream.read(),
                    dt=None,
                    dn=None,
                    folder='Home/Attachments',
                    is_private=0
                )
                kwargs['image'] = image_doc.file_url
            except Exception as e:
                return {
                    "status": "error",
                    "message": "Failed to upload image",
                    "error": str(e)
                }

        for key, value in kwargs.items():
            if hasattr(post_doc, key) and key != 'user':
                setattr(post_doc, key, value)
        
        post_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"Post {post_id} updated successfully",
            "post_id": post_id
        }
    
    except Exception as e:
        frappe.db.rollback()
        return {"status": "error", "message": str(e)}
    
# Delete Blog Post
@frappe.whitelist(allow_guest=True)
def delete_post(post_id=None, user_id=None):
    
    validation_errors = {}
    
    if not post_id or str(post_id).strip() == "":
        validation_errors["post_id"] = "Post Id is required"
    
    if not user_id or str(user_id).strip() == "":
        validation_errors["user_id"] = "User Id is required"
 
    if validation_errors:
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": validation_errors
        }

    if not frappe.db.exists("Blog Post1", post_id):
        return {
            "status": "error",
            "message": "Post does not exist"
        }
    
    if not frappe.db.exists("Blog User", user_id):
        return {
            "status": "error",
            "message": "User does not exist"
        }
    
    try:
 
        post_doc = frappe.get_doc("Blog Post1", post_id)
        
        # Check if the user is the owner
        if post_doc.user != user_id:
            return {
                "status": "error",
                "message": "Access Denied: You can only delete your own posts"
            }
        
        # Delete associated likes first
        likes = frappe.get_all("Blog Like1", filters={"post": post_id}, pluck="name")
        for like in likes:
            frappe.delete_doc("Blog Like1", like, ignore_permissions=True)
        
        # Delete the post
        frappe.delete_doc("Blog Post1", post_id, ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"Post {post_id} deleted successfully with all likes"
        }
    
    except Exception as e:
        frappe.db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }
    
# Create Like for a Post
@frappe.whitelist(allow_guest=True)
def create_like(post_id, user_id):
    like_doc = frappe.get_doc({
        "doctype": "Blog Like1",
        "post": post_id,
        "user": user_id
    })
    like_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "success", "like_id": like_doc.name}

# Get All Likes
@frappe.whitelist(allow_guest=True)
def get_likes():
    return frappe.get_all("Blog Like1", fields=["*"])

# Delete Like
@frappe.whitelist(allow_guest=True)
def delete_like(like_id=None):

    if not like_id or str(like_id).strip() == "":
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": {
                "like_id": "Like Id is required"
            }
        }
    if not frappe.db.exists("Blog Like1", like_id):
        return {
            "status": "error",
            "message": "Like does not exist"
        }
    try:
        # Delete the like
        frappe.delete_doc("Blog Like1", like_id, ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"Like {like_id} deleted successfully"
        } 
    except Exception as e:
        frappe.db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }
    
# Get User's Liked Posts
@frappe.whitelist(allow_guest=True)
def get_user_liked_posts(user_id=None):

    if not user_id or str(user_id).strip() == "":
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": {
                "user_id": "User Id is required"
            }
        }

    if not frappe.db.exists("Blog User", user_id):
        return {
            "status": "error",
            "message": "User does not exist"
        }
    
    try:
        likes = frappe.get_all(
            "Blog Like1",
            filters={"user": user_id},
            fields=["name", "post", "user", "creation"],
            order_by="creation desc"
        )
        
        liked_posts = []
        for like in likes:
            post = frappe.get_doc("Blog Post1", like["post"])
            liked_posts.append({
                "like_id": like["name"],
                "liked_at": like["creation"],
                "post_id": post.name,
                "title": post.title,
                "description": post.description,
                "content": post.content,
                "category": post.category,
                "image": post.image,
                "post_owner": post.user,
                "created_at": post.creation
            })
        
        return {
            "status": "success",
            "data": liked_posts,
            "count": f"{user_id} liked {len(liked_posts)} posts"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# User Login
@frappe.whitelist(allow_guest=True)
def login_user(email=None, password=None):

    validation_errors = {}
    
    if not email or str(email).strip() == "":
        validation_errors["email"] = "Email is required"
    
    if not password or str(password).strip() == "":
        validation_errors["password"] = "Password is required"
    
    if validation_errors:
        return {
            "status": "error",
            "message": "Validation failed",
            "required_fields": validation_errors
        }
    
    if not frappe.utils.validate_email_address(email):
        return {
            "status": "error",
            "message": "Invalid Email Address"
        }
    
    try:
        user = frappe.db.get_value(
            "Blog User",
            {"email": email},
            ["name", "email", "full_name"],
            as_dict=True
        )

        if not user:
            return {
                "status": "error",
                "message": "Invalid Email Its Not Registered"
            }

        db_password = get_decrypted_password(
            "Blog User",
            user["name"],
            "password",
            raise_exception=False
        )

        if not db_password or not hmac.compare_digest(str(db_password), str(password)):
            return {
                "status": "error",
                "message": "Invalid Password"
            }

        return {
            "status": "success",
            "message": "Login successful",
            "user_id": user["name"],
            "full_name": user.get("full_name"),
            "email": user["email"]
        }
    
    except Exception as e:
        frappe.log_error(f"Login Error: {str(e)}", "User Login")
        return {
            "status": "error",
            "message": "Login failed. Please try again"
        }

# Get All Users with their Posts and Like Counts
@frappe.whitelist(allow_guest=True)
def get_all_users_with_posts_and_likes():
    users = frappe.get_all("Blog User", fields=["name", "email", "full_name"])

    user_data = []
    for u in users:
        # Get all posts by this user
        posts = frappe.get_all(
            "Blog Post1",
            filters={"user": u.name},
            fields=["name", "title"]
        )

        # Count likes for each post
        post_list = []
        for p in posts:
            like_count = frappe.db.count("Blog Like1", {"post": p.name})
            post_list.append({
                "title": p.title,
                "likes": like_count
            })

        user_data.append({
            "user_id": u.name,
            "name": u.full_name,
            "email": u.email,
            "total_posts": len(posts),
            "posts": post_list
        })

    return user_data

# Export Posts to CSV
@frappe.whitelist(allow_guest=True)
def export_posts_csv_guest(user_id=None, email=None, download="true", send_email="true"):
    """
    Simple guest-access export for Blog User posts.
    - Provide either user_id (Blog User.name) or email (Blog User.email).
    - download/send_email accept strings like "true"/"false" or "1"/"0".
    """
    # parse booleans
    download = str(download).lower() in ("1", "true", "yes", "y")
    send_email = str(send_email).lower() in ("1", "true", "yes", "y")

    # require at least one identifier
    if not user_id and not email:
        frappe.throw("Provide user_id or email to export posts")

    # resolve user_id if email given
    if not user_id and email:
        user_id = frappe.db.get_value("Blog User", {"email": email}, "name")
        if not user_id:
            frappe.throw("No Blog User found with that email")

    # fetch posts for the Blog User
    posts = frappe.get_all(
        "Blog Post1",
        filters={"user": user_id},
        fields=["name", "title", "description", "content", "category", "image", "creation", "modified"],
        order_by="creation desc"
    )

    # build CSV in-memory
    si = io.StringIO()
    writer = csv.writer(si, quoting=csv.QUOTE_MINIMAL)
    header = ["post_id", "title", "description", "content", "category", "image_url", "created_at", "updated_at", "likes"]
    writer.writerow(header)

    for p in posts:
        like_count = frappe.db.count("Blog Like1", {"post": p.get("name")})
        row = [
            p.get("name") or "",
            p.get("title") or "",
            strip_html(p.get("description") or ""),
            strip_html(p.get("content") or ""),
            p.get("category") or "",
            p.get("image") or "",
            str(p.get("creation") or ""),
            str(p.get("modified") or ""),
            like_count
        ]
        writer.writerow(row)

    csv_text = si.getvalue()
    csv_bytes = csv_text.encode("utf-8-sig")  # BOM for Excel
    fname = f"posts_{user_id}_{now_datetime().strftime('%Y%m%d%H%M%S')}.csv"

    # send email with attachment if requested
    if send_email:
        recipient = email or frappe.db.get_value("Blog User", user_id, "email")
        if recipient:
            try:
                frappe.sendmail(
                    recipients=recipient,
                    subject="Your Posts Export",
                    message="Attached is the CSV export of your posts.",
                    attachments=[{"fname": fname, "fcontent": csv_bytes}]
                )
            except Exception as e:
                # optional: don't fail the whole request for email failure
                frappe.log_error(f"Failed to send posts export email: {e}", "export_posts_csv_guest")

    # direct download (if requested)
    if download:
        frappe.local.response.filename = fname
        frappe.local.response.filecontent = csv_bytes
        frappe.local.response.type = "download"
        return

    return {"status": "success", "message": "CSV generated" + (" and emailed" if send_email else ""), "filename": fname}

# Advanced Post Retrieval with Filtering, Sorting, Pagination
@frappe.whitelist(allow_guest=True)
def get_posts_advanced(
    page=1,
    page_size=10,
    sort_by="creation",
    sort_order="desc",
    start_date=None,
    end_date=None,
    user=None,
    min_likes=None,
    max_likes=None,
    search=None
):
    page = int(page)
    page_size = int(page_size)
    offset = (page - 1) * page_size

    filters = {}

    # Date range filter
    if start_date and end_date:
        filters["creation"] = ["between", [start_date, end_date]]

    # Filter by user
    if user:
        filters["user"] = user

    # Search in title/description/content
    search_condition = ""
    if search:
        search_condition = f""" AND (
            title LIKE '%{search}%'
            OR description LIKE '%{search}%'
            OR content LIKE '%{search}%'
        ) """

    query = f"""
        SELECT 
            bp.name,
            bp.title,
            bp.description,
            bp.content,
            bp.category,
            bp.user,
            bp.image,
            bp.creation,
            COUNT(bl.name) AS total_likes
        FROM `tabBlog Post1` bp
        LEFT JOIN `tabBlog Like1` bl ON bl.post = bp.name
        WHERE 1=1
    """

    # Add filters dynamically
    if start_date and end_date:
        query += f" AND bp.creation BETWEEN '{start_date}' AND '{end_date}' "
    if user:
        query += f" AND bp.user = '{user}' "
    if search_condition:
        query += search_condition

    # Group and apply like filters
    query += " GROUP BY bp.name "
    if min_likes:
        query += f" HAVING total_likes >= {int(min_likes)} "
    if max_likes:
        query += f" HAVING total_likes <= {int(max_likes)} "

    # Sorting
    query += f" ORDER BY {sort_by} {sort_order.upper()} "

    # Pagination
    query += f" LIMIT {page_size} OFFSET {offset} "

    # Execute
    posts = frappe.db.sql(query, as_dict=True)

    # Get total count for pagination info
    total_count = frappe.db.sql("""
        SELECT COUNT(*) 
        FROM `tabBlog Post1` 
    """)[0][0]

    return {
        "status": "success",
        "page": page,
        "page_size": page_size,
        "total_posts": total_count,
        "posts_returned": len(posts),
        "posts": posts
    }
