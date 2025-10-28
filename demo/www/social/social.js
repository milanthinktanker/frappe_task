document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("search");
  const blogList = document.getElementById("blogList");

  if (blogList) {
    loadBlogs();

    if (searchInput) {
      searchInput.addEventListener("input", () => {
        loadBlogs(searchInput.value);
      });
    }
  }

  function loadBlogs(search = "") {
    frappe.call({
      method: "social_media.www.social.social.get_published_blogs",
      args: { search },
      callback: function (r) {
        const blogs = r.message || [];
        blogList.innerHTML = "";
        blogs.forEach((b) => {
          const card = document.createElement("div");
          card.classList.add("blog-card");
          card.innerHTML = `
          <a class="title" href="/blogs/${b.route}">${b.title}</a>
          <div class="meta">By ${b.author_name || "Unknown"} (${b.author_city || ""}) | ${b.published_on}</div>
          <div class="content">${b.content.substring(0, 200)}...</div>
        `;
          blogList.appendChild(card);
        });
      },
    });
  }
});
