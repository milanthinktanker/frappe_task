document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("customerForm");
  const tableBody = document.querySelector("#customerTable tbody");
  const addressesContainer = document.getElementById("addressesContainer");
  const addAddressBtn = document.getElementById("addAddress");
  const photoInput = document.getElementById("photo");
  const photoPreview = document.getElementById("photoPreview");

  let uploadedPhoto = null;

  loadCustomers();

  // Add child row
  addAddressBtn.addEventListener("click", () => addAddressRow());

  function addAddressRow(data = {}) {
    let row = document.createElement("div");
    row.classList.add("child-row");
    row.innerHTML = `
      <input type="text" class="address_line1" placeholder="Address Line 1" value="${data.address_line1 || ""}" required />
      <input type="text" class="city" placeholder="City" value="${data.city || ""}" required />
      <input type="text" class="pincode" placeholder="Pincode" value="${data.pincode || ""}" required />
      <button type="button" onclick="this.parentElement.remove()">❌</button>
    `;
    addressesContainer.appendChild(row);
  }

  // Upload Photo
  photoInput.addEventListener("change", function () {
    if (this.files.length > 0) {
      let fd = new FormData();
      fd.append("file", this.files[0]);
      fd.append("is_private", 0);
      fd.append("attached_to_doctype", "CostomerX");

      let docname = document.getElementById("docname").value;
      if (docname) {
        fd.append("attached_to_name", docname);
      }

      fetch("/api/method/upload_file", {
        method: "POST",
        body: fd,
        headers: {
          "X-Frappe-CSRF-Token": frappe.csrf_token
        }
      })
        .then(r => r.json())
        .then(data => {
          if (data.message && data.message.file_url) {
            uploadedPhoto = data.message.file_url;
            photoPreview.innerHTML = `<img src="${uploadedPhoto}" width="80"/>`;
          }
        })
        .catch(err => console.error("Upload error:", err));
    }
  });

  // Save Customer
  form.addEventListener("submit", (e) => {
    e.preventDefault();

    let addresses = [];
    document.querySelectorAll(".child-row").forEach(row => {
      addresses.push({
        address_line1: row.querySelector(".address_line1").value,
        city: row.querySelector(".city").value,
        pincode: row.querySelector(".pincode").value,
      });
    });

    let data = {
      docname: document.getElementById("docname").value,
      first_name: document.getElementById("first_name").value,
      last_name: document.getElementById("last_name").value,
      email: document.getElementById("email").value,
      photo: uploadedPhoto || "",
      customer_addressx: JSON.stringify(addresses),
    };

    frappe.call({
      method: "demo.www.customers1.customers1.save_customer",
      args: data,
      headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
      callback: function (r) {
        if (r.message.status === "success") {
          resetForm();
          loadCustomers();
          frappe.msgprint("✅ Customer Saved Successfully!");
        }
      },
    });
  });


  function resetForm() {
    form.reset();
    document.getElementById("docname").value = "";   
    addressesContainer.innerHTML = "";
    photoPreview.innerHTML = "";
    uploadedPhoto = null;
  }

  // Load Customers
  function loadCustomers() {
    frappe.call({
      method: "demo.www.customers1.customers1.get_customers",
      callback: function (r) {
        tableBody.innerHTML = "";
        r.message.forEach((c) => {
          let row = document.createElement("tr");
          row.innerHTML = `
            <td>${c.first_name} ${c.last_name}</td>
            <td>${c.email}</td>
            <td>${c.photo ? `<img src="${c.photo}" width="50"/>` : ""}</td>
            <td class="actions">
              <button id="edit" onclick="editCustomer('${c.name}')">✏️ Edit</button>
              <button id="delete" onclick="deleteCustomer('${c.name}')">🗑️ Delete</button>
            </td>`;
          tableBody.appendChild(row);
        });
      },
    });
  }

  // Edit
  window.editCustomer = function (docname) {
    frappe.call({
      method: "demo.www.customers1.customers1.get_customer",
      args: { docname },
      headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
      callback: function (r) {
        const c = r.message;
        document.getElementById("docname").value = c.name;
        document.getElementById("first_name").value = c.first_name;
        document.getElementById("last_name").value = c.last_name;
        document.getElementById("email").value = c.email;

        addressesContainer.innerHTML = "";
        c.customer_addressx.forEach(addr => addAddressRow(addr));

        photoPreview.innerHTML = c.photo ? `<img src="${c.photo}" width="80"/>` : "";
        uploadedPhoto = c.photo;
      },
    });
  };

  // Delete
  window.deleteCustomer = function (docname) {
    if (confirm("Are you sure you want to delete this customer?")) {
      frappe.call({
        method: "demo.www.customers1.customers1.delete_customer",
        args: { docname },
        headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
        callback: function (r) {
          if (r.message.status === "success") {
            loadCustomers();
            frappe.msgprint("🗑️ Customer Deleted Successfully!");
          }
        },
      });
    }
  };
});
