document.addEventListener("DOMContentLoaded", function () {

    function loadDropdown(input, list, hidden, url) {

        function fetchData(q = "") {
            fetch(url + "?q=" + encodeURIComponent(q))
                .then(r => r.json())
                .then(data => {
                    list.innerHTML = "";
                    list.style.display = "block";

                    if (!data.length) {
                        list.innerHTML =
                            '<div class="dropdown-item text-muted">لا يوجد نتائج</div>';
                        return;
                    }

                    data.forEach(obj => {
                        const div = document.createElement("div");
                        div.className = "dropdown-item";
                        div.textContent = obj.name;
                        div.onclick = () => {
                            input.value = obj.name;
                            hidden.value = obj.id;
                            list.style.display = "none";
                        };
                        list.appendChild(div);
                    });
                });
        }

        // عند الضغط → كل البيانات
        input.addEventListener("focus", () => fetchData(""));

        // عند الكتابة → فلترة
        input.addEventListener("keyup", () => fetchData(input.value));

        // إغلاق عند الضغط خارج
        document.addEventListener("click", e => {
            if (!input.parentElement.contains(e.target)) {
                list.style.display = "none";
            }
        });
    }

    /* ========== المورد ========== */
    const supplierInput = document.getElementById("supplier_search");
    const supplierList  = document.getElementById("supplier_list");
    const supplierId    = document.getElementById("supplier_id");

    if (supplierInput && supplierList && supplierId) {
        loadDropdown(
            supplierInput,
            supplierList,
            supplierId,
            "/suppliers/api/search/"
        );
    }

    /* ========== المنتجات (كل صف) ========== */
    document.querySelectorAll(".product-input").forEach(input => {

        const box    = input.closest(".dropdown-box");
        const list   = box.querySelector(".dropdown-list");
        const hidden = box.querySelector(".product-id");

        loadDropdown(
            input,
            list,
            hidden,
            "/products/search/"
        );
    });

});
