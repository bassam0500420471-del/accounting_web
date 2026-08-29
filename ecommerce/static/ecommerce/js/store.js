/* ==========================================================
   ALRAED ERP STORE
========================================================== */

document.addEventListener("DOMContentLoaded", () => {

    console.log("START STORE JS");


    /* ==========================================
       PAGE LOADER
    ========================================== */

    window.addEventListener("load", () => {

        document.body.classList.add("loaded");

    });


    /* ==========================================
       BACK TO TOP
    ========================================== */

    const backTop =
        document.getElementById("backToTop");


    if (backTop) {

        window.addEventListener("scroll", () => {

            if (window.scrollY > 400) {

                backTop.classList.add("show");

            } else {

                backTop.classList.remove("show");

            }

        });


        backTop.addEventListener("click", () => {

            window.scrollTo({

                top: 0,

                behavior: "smooth"

            });

        });

    }


    /* ==========================================
       MOBILE MENU
    ========================================== */

    const menuBtn =
        document.getElementById("mobileMenuBtn");


    const closeBtn =
        document.getElementById("closeMobileMenu");


    const mobileMenu =
        document.getElementById("mobileMenu");


    const overlay =
        document.getElementById("menuOverlay");


    function openMenu() {

        if (mobileMenu) {

            mobileMenu.classList.add("active");

        }


        if (overlay) {

            overlay.classList.add("active");

        }


        document.body.style.overflow = "hidden";

    }


    function closeMenu() {

        if (mobileMenu) {

            mobileMenu.classList.remove("active");

        }


        if (overlay) {

            overlay.classList.remove("active");

        }


        document.body.style.overflow = "";

    }


    if (menuBtn) {

        menuBtn.onclick = openMenu;

    }


    if (closeBtn) {

        closeBtn.onclick = closeMenu;

    }


    if (overlay) {

        overlay.onclick = closeMenu;

    }


    /* ==========================================
       PRODUCT SLIDER
    ========================================== */

    const sliders =
        document.querySelectorAll(".products-wrapper");


    sliders.forEach(slider => {

        const container =
            slider.closest(".products-slider");


        if (!container) return;


        const nextBtn =
            container.querySelector(".slider-next");


        const prevBtn =
            container.querySelector(".slider-prev");


        const scrollAmount = 320;


        if (nextBtn) {

            nextBtn.addEventListener("click", () => {

                slider.scrollBy({

                    left: scrollAmount,

                    behavior: "smooth"

                });

            });

        }


        if (prevBtn) {

            prevBtn.addEventListener("click", () => {

                slider.scrollBy({

                    left: -scrollAmount,

                    behavior: "smooth"

                });

            });

        }


        /* ==========================================
           DRAG SLIDER
        ========================================== */

        let isDown = false;

        let startX;

        let scrollLeft;


        slider.addEventListener("mousedown", (e) => {

            isDown = true;

            startX =
                e.pageX - slider.offsetLeft;

            scrollLeft =
                slider.scrollLeft;

        });


        slider.addEventListener("mouseup", () => {

            isDown = false;

        });


        slider.addEventListener("mouseleave", () => {

            isDown = false;

        });


        slider.addEventListener("mousemove", (e) => {

            if (!isDown) return;

            e.preventDefault();


            const x =
                e.pageX - slider.offsetLeft;


            slider.scrollLeft =
                scrollLeft - (x - startX) * 1.5;

        });


        /* ==========================================
           TOUCH SLIDER
        ========================================== */

        let touchStart = 0;


        slider.addEventListener("touchstart", (e) => {

            touchStart =
                e.changedTouches[0].screenX;

        });


        slider.addEventListener("touchend", (e) => {

            const touchEnd =
                e.changedTouches[0].screenX;


            const distance =
                touchStart - touchEnd;


            if (Math.abs(distance) > 50) {

                slider.scrollBy({

                    left: distance,

                    behavior: "smooth"

                });

            }

        });

    });


    /* ==========================================
       TOGGLE PRODUCTS VIEW
    ========================================== */

    document
        .querySelectorAll(".toggle-products")
        .forEach(button => {

            button.addEventListener("click", function (e) {

                e.preventDefault();


                const target =
                    document.getElementById(
                        this.dataset.target
                    );


                if (!target) {

                    console.log(
                        "Not found:",
                        this.dataset.target
                    );

                    return;

                }


                target.classList.toggle(
                    "expanded-grid"
                );


                if (
                    target.classList.contains(
                        "expanded-grid"
                    )
                ) {

                    this.textContent =
                        "عرض أقل";

                } else {

                    this.textContent =
                        "عرض الكل";

                }

            });

        });


    /* ==========================================
       CSRF
    ========================================== */

    function getCookie(name) {

        let value = null;


        if (document.cookie) {

            document.cookie
                .split(";")
                .forEach(cookie => {

                    const item =
                        cookie.trim();


                    if (
                        item.startsWith(
                            name + "="
                        )
                    ) {

                        value =
                            decodeURIComponent(
                                item.substring(
                                    name.length + 1
                                )
                            );

                    }

                });

        }


        return value;

    }


    const csrftoken =
        getCookie("csrftoken");


    console.log(
        "CSRF:",
        csrftoken
            ? "FOUND"
            : "NOT FOUND"
    );


    /* ==========================================
       STORE TOAST NOTIFICATIONS
    ========================================== */

    function showToast(
        message,
        type = "success"
    ) {

        const toast =
            document.createElement("div");


        toast.className =
            "store-toast " + type;


        toast.innerHTML = `
            <span>
                ${message}
            </span>
        `;


        document.body.appendChild(toast);


        setTimeout(() => {

            toast.classList.add("show");

        }, 100);


        setTimeout(() => {

            toast.classList.remove("show");


            setTimeout(() => {

                toast.remove();

            }, 300);

        }, 3000);

    }


    /* ==========================================
       STORE GLOBAL HELPERS
    ========================================== */

    console.log("BEFORE STORE");


    window.Store = {

        /* ======================================
           GET STORE SLUG
        ====================================== */

        getStoreSlug: function () {

            const body =
                document.body;


            if (
                body &&
                body.dataset &&
                body.dataset.storeSlug
            ) {

                return body.dataset.storeSlug;

            }


            const parts =
                window.location.pathname
                    .split("/")
                    .filter(Boolean);


            const storeIndex =
                parts.indexOf("store");


            if (
                storeIndex !== -1 &&
                parts[storeIndex + 1]
            ) {

                return parts[storeIndex + 1];

            }


            return "";

        },


        /* ======================================
           تحديث عداد السلة
        ====================================== */

        refreshCart: function () {

            const storeSlug =
                this.getStoreSlug();


            if (!storeSlug) {

                console.warn(
                    "STORE SLUG NOT FOUND"
                );

                return;

            }


            fetch(
                `/store/${storeSlug}/cart/count/`,
                {

                    method: "GET",

                    credentials:
                        "same-origin",

                    headers: {

                        "X-Requested-With":
                            "XMLHttpRequest"

                    }

                }
            )

            .then(response => {

                if (!response.ok) {

                    throw new Error(
                        "Cart count HTTP " +
                        response.status
                    );

                }


                return response.json();

            })

            .then(data => {

                console.log(
                    "CART COUNT:",
                    data
                );


                const count =
                    document.getElementById(
                        "cartCount"
                    );


                if (count) {

                    count.textContent =
                        Number(data.count ?? 0);

                }

            })

            .catch(error => {

                console.error(
                    "Cart count error:",
                    error
                );

            });

        },


/* ======================================
   تحديث عداد المفضلة
====================================== */

refreshWishlist: function () {

    const storeSlug =
        this.getStoreSlug();


    if (!storeSlug) {

        console.warn(
            "STORE SLUG NOT FOUND"
        );

        return;

    }


    fetch(
        `/store/${storeSlug}/wishlist/count/`,
        {

            method: "GET",

            credentials:
                "same-origin",

            headers: {

                "X-Requested-With":
                    "XMLHttpRequest"

            }

        }
    )

    .then(response => {

        if (!response.ok) {

            throw new Error(
                "Wishlist count HTTP " +
                response.status
            );

        }

        return response.json();

    })

    .then(data => {

        console.log(
            "WISHLIST COUNT:",
            data
        );


        /*
         * العدد الحقيقي القادم من السيرفر
         */
        const wishlistCount =
            Number(data.count ?? 0);


        /*
         * =====================================
         * العداد العام في الهيدر
         * =====================================
         */

        const headerCount =
            document.getElementById(
                "headerWishlistCount"
            );


        if (headerCount) {

            headerCount.textContent =
                wishlistCount;

        }


        /*
         * =====================================
         * دعم أي عداد داخلي للمفضلة
         * =====================================
         *
         * إذا كان عندك عداد داخل صفحة
         * المفضلة وله هذا الـ ID:
         *
         * wishlistPageCount
         */

        const pageCount =
            document.getElementById(
                "wishlistPageCount"
            );


        if (pageCount) {

            pageCount.textContent =
                wishlistCount;

        }

    })

    .catch(error => {

        console.error(
            "Wishlist count error:",
            error
        );

    });

},



        /* ======================================
           تحديث عدادات المتجر
        ====================================== */

        refreshCounts: function () {

            this.refreshCart();

            this.refreshWishlist();

        },


        /* ======================================
           تنسيق السعر
        ====================================== */

        formatPrice: function (price) {

            return Number(price)
                .toLocaleString("ar-SA");

        }

    };


    /* ==========================================
       ADD TO CART
    ========================================== */

    document
        .querySelectorAll(".add-to-cart")
        .forEach(button => {

            button.addEventListener(
                "click",
                function (e) {

                    e.preventDefault();


                    console.log(
                        "ADD CART CLICKED"
                    );


                    const productId =
                        this.dataset.product;


                    const storeSlug =
                        window.Store.getStoreSlug();


                    if (!productId) {

                        console.error(
                            "PRODUCT ID NOT FOUND"
                        );

                        return;

                    }


                    if (!storeSlug) {

                        console.error(
                            "STORE SLUG NOT FOUND"
                        );

                        return;

                    }


                    fetch(
                        `/store/${storeSlug}/cart/add/${productId}/`,
                        {

                            method: "POST",

                            credentials:
                                "same-origin",

                            headers: {

                                "X-CSRFToken":
                                    csrftoken,

                                "X-Requested-With":
                                    "XMLHttpRequest",

                                "Content-Type":
                                    "application/json"

                            },

                            body:
                                JSON.stringify({

                                    quantity: 1

                                })

                        }
                    )

                    .then(response => {

                        console.log(
                            "CART STATUS:",
                            response.status
                        );


                        if (!response.ok) {

                            throw new Error(
                                "HTTP " +
                                response.status
                            );

                        }


                        return response.json();

                    })

                    .then(data => {

                        console.log(
                            "CART RESPONSE:",
                            data
                        );


                        if (
                            data.status ===
                            "success"
                        ) {

                            /*
                             * تحديث مباشر
                             */
                            const cartCount =
                                document.getElementById(
                                    "cartCount"
                                );


                            if (cartCount) {

                                cartCount.textContent =
                                    Number(
                                        data.items ?? 0
                                    );

                            }


                            /*
                             * مزامنة مع السيرفر
                             */
                            window.Store.refreshCart();


                            showToast(
                                "تمت إضافة المنتج إلى السلة"
                            );

                        } else {

                            showToast(
                                data.message ||
                                "تعذر إضافة المنتج إلى السلة",
                                "info"
                            );

                        }

                    })

                    .catch(error => {

                        console.error(
                            "ADD CART ERROR:",
                            error
                        );


                        showToast(
                            "حدث خطأ أثناء إضافة المنتج إلى السلة",
                            "info"
                        );

                    });

                }
            );

        });


    /* ==========================================
       WISHLIST
    ========================================== */

    document
        .querySelectorAll(".wishlist-btn")
        .forEach(button => {

            button.addEventListener(
                "click",
                function (e) {

                    e.preventDefault();


                    const wishlistButton =
                        this;


                    const productId =
                        wishlistButton.dataset.product;


                    const storeSlug =
                        window.Store.getStoreSlug();


                    if (!productId) {

                        console.error(
                            "WISHLIST PRODUCT ID NOT FOUND"
                        );

                        return;

                    }


                    if (!storeSlug) {

                        console.error(
                            "STORE SLUG NOT FOUND"
                        );

                        return;

                    }


                    /*
                     * منع الضغط المتكرر
                     */
                    if (
                        wishlistButton.dataset.loading ===
                        "true"
                    ) {

                        return;

                    }


                    wishlistButton.dataset.loading =
                        "true";


                    fetch(
                        `/store/${storeSlug}/wishlist/${productId}/`,
                        {

                            method: "POST",

                            credentials:
                                "same-origin",

                            headers: {

                                "X-CSRFToken":
                                    csrftoken,

                                "X-Requested-With":
                                    "XMLHttpRequest",

                                "Content-Type":
                                    "application/json"

                            },

                            body:
                                JSON.stringify({

                                    product_id:
                                        productId

                                })

                        }
                    )

                    .then(response => {

                        if (!response.ok) {

                            throw new Error(
                                "HTTP " +
                                response.status
                            );

                        }


                        return response.json();

                    })

                    .then(data => {

                        console.log(
                            "WISHLIST RESPONSE:",
                            data
                        );


                        const icon =
                            wishlistButton
                                .querySelector("i");


                        /* =================================
                           تمت الإضافة
                        ================================= */

                        if (
                            data.status ===
                            "added"
                        ) {

                            wishlistButton
                                .classList
                                .add("active");


                            if (icon) {

                                icon.classList
                                    .remove(
                                        "bi-heart"
                                    );


                                icon.classList
                                    .add(
                                        "bi-heart-fill"
                                    );


                                icon.style.color =
                                    "red";

                            }


                            showToast(
                                "تمت إضافة المنتج إلى المفضلة"
                            );

                        }


                        /* =================================
                           تمت الإزالة
                        ================================= */

                        else if (
                            data.status ===
                            "removed"
                        ) {

                            wishlistButton
                                .classList
                                .remove(
                                    "active"
                                );


                            if (icon) {

                                icon.classList
                                    .remove(
                                        "bi-heart-fill"
                                    );


                                icon.classList
                                    .add(
                                        "bi-heart"
                                    );


                                icon.style.color =
                                    "";

                            }


                            showToast(
                                "تمت إزالة المنتج من المفضلة",
                                "info"
                            );

                        }


                        /*
                         * مهم جدًا:
                         *
                         * بعد الإضافة أو الحذف
                         * نطلب العدد الحقيقي من السيرفر.
                         *
                         * مثال:
                         * 4 -> حذف -> السيرفر يرجع 3
                         * فيظهر 3 مباشرة.
                         */
                        /* 
=================================
   تحديث عداد المفضلة مباشرة
================================= */

const headerWishlistCount =
    document.getElementById(
        "headerWishlistCount"
    );

if (headerWishlistCount) {

    headerWishlistCount.textContent =
        Number(data.count ?? 0);

}

                    })

                    .catch(error => {

                        console.error(
                            "WISHLIST ERROR:",
                            error
                        );


                        showToast(
                            "حدث خطأ أثناء تحديث المفضلة",
                            "info"
                        );

                    })

                    .finally(() => {

                        wishlistButton
                            .dataset
                            .loading =
                            "false";

                    });

                }
            );

        });


    /* ==========================================
       LIVE PRODUCT FILTER
    ========================================== */

    const searchInput =
        document.getElementById(
            "storeSearch"
        );


    if (searchInput) {

        searchInput.addEventListener(
            "input",
            function () {

                const value =
                    this.value
                        .trim()
                        .toLowerCase();


                document
                    .querySelectorAll(
                        ".product-card"
                    )
                    .forEach(card => {

                        const name =
                            card.querySelector(
                                ".product-name"
                            );


                        if (!name) return;


                        if (
                            name.textContent
                                .toLowerCase()
                                .includes(value)
                        ) {

                            card.style.display =
                                "";

                        } else {

                            card.style.display =
                                "none";

                        }

                    });

            }
        );

    }


    /* ==========================================
       STICKY HEADER
    ========================================== */

    const header =
        document.querySelector(
            ".store-header"
        );


    if (header) {

        window.addEventListener(
            "scroll",
            () => {

                if (
                    window.scrollY > 120
                ) {

                    header.classList.add(
                        "sticky"
                    );

                } else {

                    header.classList.remove(
                        "sticky"
                    );

                }

            }
        );

    }


    /* ==========================================
       PRODUCT SCROLL ANIMATION
    ========================================== */

    const animatedItems =
        document.querySelectorAll(
            ".product-card, .category-card, .store-section"
        );


    if (animatedItems.length) {

        const observer =
            new IntersectionObserver(
                (entries) => {

                    entries.forEach(entry => {

                        if (
                            entry.isIntersecting
                        ) {

                            entry.target.classList.add(
                                "visible"
                            );

                        }

                    });

                },
                {
                    threshold: 0.15
                }
            );


        animatedItems.forEach(item => {

            item.classList.add(
                "hidden"
            );


            observer.observe(
                item
            );

        });

    }


    /* ==========================================
       DARK / LIGHT MODE
    ========================================== */

    const themeBtn =
        document.getElementById(
            "themeToggle"
        );


    const savedTheme =
        localStorage.getItem(
            "storeTheme"
        );


    if (savedTheme) {

        document.body.classList.add(
            savedTheme
        );

    }


    if (themeBtn) {

        themeBtn.addEventListener(
            "click",
            () => {

                document.body.classList.toggle(
                    "dark-mode"
                );


                const mode =
                    document.body.classList.contains(
                        "dark-mode"
                    )
                        ? "dark-mode"
                        : "";


                localStorage.setItem(
                    "storeTheme",
                    mode
                );

            }
        );

    }


    /* ==========================================
       LANGUAGE DIRECTION RTL / LTR
    ========================================== */

    const langBtn =
        document.getElementById(
            "languageToggle"
        );


    const savedDirection =
        localStorage.getItem(
            "storeDirection"
        );


    if (savedDirection) {

        document.documentElement.dir =
            savedDirection;


        document.documentElement.lang =
            savedDirection === "rtl"
                ? "ar"
                : "en";

    }


    if (langBtn) {

        langBtn.addEventListener(
            "click",
            () => {

                const current =
                    document.documentElement.dir;


                if (current === "rtl") {

                    document.documentElement.dir =
                        "ltr";


                    document.documentElement.lang =
                        "en";


                    localStorage.setItem(
                        "storeDirection",
                        "ltr"
                    );

                } else {

                    document.documentElement.dir =
                        "rtl";


                    document.documentElement.lang =
                        "ar";


                    localStorage.setItem(
                        "storeDirection",
                        "rtl"
                    );

                }

            }
        );

    }


    /* ==========================================
       PRODUCT REVIEWS & STARS
    ========================================== */

    const stars =
        document.querySelectorAll(
            ".rating-star"
        );


    stars.forEach(star => {

        star.addEventListener(
            "click",
            function () {

                const rating =
                    this.dataset.rating;


                const container =
                    this.closest(
                        ".rating-box"
                    );


                if (container) {

                    container
                        .querySelectorAll(
                            ".rating-star"
                        )
                        .forEach(item => {

                            if (
                                Number(
                                    item.dataset.rating
                                ) <=
                                Number(rating)
                            ) {

                                item.classList.add(
                                    "active"
                                );

                            } else {

                                item.classList.remove(
                                    "active"
                                );

                            }

                        });


                    container.dataset.value =
                        rating;

                }

            }
        );

    });


    /* ==========================================
       SEND REVIEW
    ========================================== */

    const reviewForm =
        document.getElementById(
            "reviewForm"
        );


    if (reviewForm) {

        reviewForm.addEventListener(
            "submit",
            function (e) {

                e.preventDefault();


                const ratingBox =
                    this.querySelector(
                        ".rating-box"
                    );


                const rating =
                    ratingBox
                        ? ratingBox.dataset.value
                        : "";


                const formData =
                    new FormData(this);


                formData.append(
                    "rating",
                    rating
                );


                fetch(
                    this.action,
                    {

                        method: "POST",

                        body: formData,

                        headers: {

                            "X-CSRFToken":
                                csrftoken

                        }

                    }
                )

                .then(response =>
                    response.json()
                )

                .then(data => {

                    if (data.success) {

                        showToast(
                            "تم إرسال تقييمك بنجاح"
                        );


                        this.reset();

                    }

                })

                .catch(error => {

                    console.error(
                        "REVIEW ERROR:",
                        error
                    );

                });

            }
        );

    }


    /* ==========================================
       OFFERS COUNTDOWN
    ========================================== */

    const countdowns =
        document.querySelectorAll(
            ".offer-countdown"
        );


    countdowns.forEach(timer => {

        const endDate =
            new Date(
                timer.dataset.date
            ).getTime();


        const interval =
            setInterval(() => {

                const now =
                    new Date().getTime();


                const distance =
                    endDate - now;


                if (distance <= 0) {

                    clearInterval(
                        interval
                    );


                    timer.innerHTML =
                        "انتهى العرض";


                    return;

                }


                const days =
                    Math.floor(
                        distance /
                        (1000 * 60 * 60 * 24)
                    );


                const hours =
                    Math.floor(
                        (
                            distance %
                            (1000 * 60 * 60 * 24)
                        ) /
                        (1000 * 60 * 60)
                    );


                const minutes =
                    Math.floor(
                        (
                            distance %
                            (1000 * 60 * 60)
                        ) /
                        (1000 * 60)
                    );


                const seconds =
                    Math.floor(
                        (
                            distance %
                            (1000 * 60)
                        ) /
                        1000
                    );


                timer.innerHTML = `
                    ${days} يوم
                    ${hours} ساعة
                    ${minutes} دقيقة
                    ${seconds} ثانية
                `;

            }, 1000);

    });


    /* ==========================================
       COPY COUPON CODE
    ========================================== */

    document
        .querySelectorAll(".copy-coupon")
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    const code =
                        button.dataset.code;


                    if (
                        navigator.clipboard
                    ) {

                        navigator.clipboard.writeText(
                            code
                        );

                    }


                    showToast(
                        "تم نسخ كوبون الخصم"
                    );

                }
            );

        });


    /* ==========================================
       ORDER STATUS NOTIFICATIONS
    ========================================== */

    function orderNotification(message) {

        const box =
            document.createElement("div");


        box.className =
            "order-notification";


        box.innerHTML = `

            <div class="notification-icon">
                🔔
            </div>

            <div>
                ${message}
            </div>

        `;


        document.body.appendChild(
            box
        );


        setTimeout(() => {

            box.classList.add(
                "show"
            );

        }, 100);


        setTimeout(() => {

            box.classList.remove(
                "show"
            );


            setTimeout(() => {

                box.remove();

            }, 500);

        }, 5000);

    }


    /* ==========================================
       CHECK ORDER STATUS
    ========================================== */

    const orderTracker =
        document.getElementById(
            "orderTracker"
        );


    if (orderTracker) {

        const orderId =
            orderTracker.dataset.order;


        setInterval(() => {

            fetch(
                `/orders/status/${orderId}/`
            )

            .then(response =>
                response.json()
            )

            .then(data => {

                if (data.changed) {

                    orderNotification(
                        data.message
                    );


                    orderTracker.innerHTML =
                        data.status;

                }

            })

            .catch(error => {

                console.error(
                    "ORDER STATUS ERROR:",
                    error
                );

            });

        }, 10000);

    }


    /* ==========================================
       IMAGE LAZY LOADING
    ========================================== */

    const lazyImages =
        document.querySelectorAll(
            "img[data-src]"
        );


    if (lazyImages.length) {

        const imageObserver =
            new IntersectionObserver(
                (entries, observer) => {

                    entries.forEach(entry => {

                        if (
                            entry.isIntersecting
                        ) {

                            const image =
                                entry.target;


                            image.src =
                                image.dataset.src;


                            image.removeAttribute(
                                "data-src"
                            );


                            observer.unobserve(
                                image
                            );

                        }

                    });

                },
                {
                    rootMargin: "100px"
                }
            );


        lazyImages.forEach(image => {

            imageObserver.observe(
                image
            );

        });

    }


    /* ==========================================
       MOBILE PERFORMANCE
    ========================================== */

    document
        .querySelectorAll("img")
        .forEach(image => {

            if (
                !image.hasAttribute(
                    "loading"
                )
            ) {

                image.setAttribute(
                    "loading",
                    "lazy"
                );

            }

        });


    /* ==========================================
       INITIAL STORE START
    ========================================== */

    if (window.Store) {

        /*
         * جلب الأعداد الحقيقية من السيرفر
         * عند فتح أي صفحة في المتجر.
         */

        window.Store.refreshCounts();

    }


    console.log("END STORE JS");

});