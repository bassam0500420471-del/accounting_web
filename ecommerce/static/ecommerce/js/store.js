/* ==========================================================
   ALRAED ERP STORE
========================================================== */

document.addEventListener("DOMContentLoaded", () => {

    /* ==========================================
       PAGE LOADER
    ========================================== */

    window.addEventListener("load", () => {

        document.body.classList.add("loaded");

    });




    /* ==========================================
       BACK TO TOP
    ========================================== */

    const backTop = document.getElementById("backToTop");

    window.addEventListener("scroll", () => {

        if(window.scrollY > 400){

            backTop.classList.add("show");

        }

        else{

            backTop.classList.remove("show");

        }

    });

    if(backTop){

        backTop.addEventListener("click",()=>{

            window.scrollTo({

                top:0,

                behavior:"smooth"

            });

        });

    }




    /* ==========================================
       MOBILE MENU
    ========================================== */

    const menuBtn = document.getElementById("mobileMenuBtn");

    const closeBtn = document.getElementById("closeMobileMenu");

    const mobileMenu = document.getElementById("mobileMenu");

    const overlay = document.getElementById("menuOverlay");


    function openMenu(){

        mobileMenu.classList.add("active");

        overlay.classList.add("active");

        document.body.style.overflow="hidden";

    }


    function closeMenu(){

        mobileMenu.classList.remove("active");

        overlay.classList.remove("active");

        document.body.style.overflow="";

    }


    if(menuBtn){

        menuBtn.onclick=openMenu;

    }


    if(closeBtn){

        closeBtn.onclick=closeMenu;

    }


    if(overlay){

        overlay.onclick=closeMenu;

    }

});
    /* ==========================================
       PRODUCT HORIZONTAL SLIDER
    ========================================== */


    const sliders = document.querySelectorAll(".product-slider");


    sliders.forEach(slider => {


        const nextBtn = slider.parentElement.querySelector(".slider-next");

        const prevBtn = slider.parentElement.querySelector(".slider-prev");


        const scrollAmount = 300;



        if(nextBtn){

            nextBtn.addEventListener("click",()=>{

                slider.scrollBy({

                    left: scrollAmount,

                    behavior:"smooth"

                });

            });

        }



        if(prevBtn){

            prevBtn.addEventListener("click",()=>{

                slider.scrollBy({

                    left: -scrollAmount,

                    behavior:"smooth"

                });

            });

        }




        /* ==================================
           MOUSE DRAG
        ================================== */


        let isDown = false;

        let startX;

        let scrollLeft;



        slider.addEventListener("mousedown",(e)=>{


            isDown = true;

            slider.classList.add("dragging");

            startX = e.pageX - slider.offsetLeft;

            scrollLeft = slider.scrollLeft;


        });



        slider.addEventListener("mouseleave",()=>{

            isDown=false;

            slider.classList.remove("dragging");

        });



        slider.addEventListener("mouseup",()=>{

            isDown=false;

            slider.classList.remove("dragging");

        });



        slider.addEventListener("mousemove",(e)=>{


            if(!isDown) return;


            e.preventDefault();


            const x = e.pageX - slider.offsetLeft;


            const walk = (x - startX) * 1.5;


            slider.scrollLeft = scrollLeft - walk;


        });




        /* ==================================
           TOUCH MOBILE SWIPE
        ================================== */


        let touchStart = 0;

        let touchEnd = 0;



        slider.addEventListener("touchstart",(e)=>{

            touchStart = e.changedTouches[0].screenX;

        });



        slider.addEventListener("touchend",(e)=>{


            touchEnd = e.changedTouches[0].screenX;


            let distance = touchStart - touchEnd;



            if(Math.abs(distance) > 50){


                slider.scrollBy({

                    left: distance,

                    behavior:"smooth"

                });


            }


        });



    });
    /* ==========================================
       CART & WISHLIST
    ========================================== */


    const csrfToken = document.querySelector(
        "[name=csrfmiddlewaretoken]"
    );


    /* ==================================
       ADD TO CART
    ================================== */


    document.querySelectorAll(".add-to-cart")
    .forEach(button => {


        button.addEventListener("click", function(e){


            e.preventDefault();


            let productId = this.dataset.product;


            fetch("/cart/add/",{


                method:"POST",


                headers:{


                    "X-CSRFToken":
                    csrfToken ? csrfToken.value : "",


                    "Content-Type":
                    "application/json"


                },


                body:JSON.stringify({

                    product_id:productId,

                    quantity:1

                })


            })


            .then(response=>response.json())


            .then(data=>{


                if(data.success){


                    const cartCount =
                    document.getElementById("cartCount");


                    if(cartCount){

                        cartCount.innerText =
                        data.cart_count;

                    }



                    this.classList.add("added");


                }


            });



        });


    });





    /* ==================================
       WISHLIST
    ================================== */


    document.querySelectorAll(".wishlist-btn")
    .forEach(button=>{


        button.addEventListener("click",function(e){


            e.preventDefault();


            let productId =
            this.dataset.product;



            fetch("/wishlist/toggle/",{


                method:"POST",


                headers:{


                    "X-CSRFToken":
                    csrfToken ? csrfToken.value : "",


                    "Content-Type":
                    "application/json"

                },


                body:JSON.stringify({

                    product_id:productId

                })


            })


            .then(response=>response.json())


            .then(data=>{


                if(data.status==="added"){


                    this.classList.add("active");


                }


                else{


                    this.classList.remove("active");


                }


            });



        });



    });
    /* ==========================================
       LIVE PRODUCT SEARCH
    ========================================== */


    const searchInput =
    document.getElementById("storeSearch");


    const searchResults =
    document.getElementById("searchResults");



    if(searchInput && searchResults){



        searchInput.addEventListener("input", function(){


            let query = this.value.trim();



            if(query.length < 2){


                searchResults.innerHTML = "";

                searchResults.classList.remove("show");

                return;


            }



            fetch(`/store/search/?q=${query}`)



            .then(response=>response.json())



            .then(data=>{


                searchResults.innerHTML = "";



                if(data.products.length){



                    data.products.forEach(product=>{


                        let item =
                        document.createElement("a");



                        item.href =
                        product.url;



                        item.className =
                        "search-item";



                        item.innerHTML = `


                            <img src="${product.image}">


                            <span>

                                ${product.name}

                            </span>


                            <strong>

                                ${product.price}

                            </strong>


                        `;



                        searchResults.appendChild(item);



                    });



                    searchResults.classList.add("show");



                }

                else{


                    searchResults.innerHTML = `

                        <div class="no-result">

                            لا توجد منتجات

                        </div>

                    `;


                    searchResults.classList.add("show");


                }



            });



        });






        document.addEventListener("click",(e)=>{


            if(
                !searchInput.contains(e.target)
                &&
                !searchResults.contains(e.target)
            ){


                searchResults.classList.remove("show");


            }



        });



    }
    /* ==========================================
       STORE TOAST NOTIFICATIONS
    ========================================== */


    function showToast(message, type="success"){


        let toast =
        document.createElement("div");


        toast.className =
        "store-toast " + type;



        toast.innerHTML = `

            <span>${message}</span>

        `;



        document.body.appendChild(toast);



        setTimeout(()=>{


            toast.classList.add("show");


        },100);




        setTimeout(()=>{


            toast.classList.remove("show");



            setTimeout(()=>{


                toast.remove();


            },300);



        },3000);



    }





    /* ==================================
       CART SUCCESS MESSAGE
    ================================== */


    document.querySelectorAll(".add-to-cart")
    .forEach(button=>{


        button.addEventListener("click",()=>{


            showToast(

                "تمت إضافة المنتج إلى السلة"

            );


        });


    });





    /* ==================================
       WISHLIST MESSAGE
    ================================== */


    document.querySelectorAll(".wishlist-btn")
    .forEach(button=>{


        button.addEventListener("click",()=>{


            if(
                button.classList.contains("active")
            ){


                showToast(

                    "تمت الإضافة إلى المفضلة"

                );


            }

            else{


                showToast(

                    "تمت إزالة المنتج من المفضلة",

                    "info"

                );


            }


        });


    });
    /* ==========================================
       STICKY HEADER
    ========================================== */


    const header =
    document.querySelector(".store-header");



    if(header){


        window.addEventListener("scroll",()=>{


            if(window.scrollY > 120){


                header.classList.add("sticky");


            }

            else{


                header.classList.remove("sticky");


            }



        });



    }





    /* ==========================================
       PRODUCT SCROLL ANIMATION
    ========================================== */


    const animatedItems =
    document.querySelectorAll(
        ".product-card, .category-card, .store-section"
    );



    if(animatedItems.length){



        const observer =
        new IntersectionObserver((entries)=>{


            entries.forEach(entry=>{


                if(entry.isIntersecting){


                    entry.target.classList.add(
                        "visible"
                    );


                }



            });



        },{
            threshold:0.15
        });




        animatedItems.forEach(item=>{


            item.classList.add(
                "hidden"
            );


            observer.observe(item);



        });



    }
    /* ==========================================
       DARK / LIGHT MODE
    ========================================== */


    const themeBtn =
    document.getElementById("themeToggle");



    const savedTheme =
    localStorage.getItem("storeTheme");



    if(savedTheme){


        document.body.classList.add(savedTheme);


    }




    if(themeBtn){


        themeBtn.addEventListener("click",()=>{


            document.body.classList.toggle(
                "dark-mode"
            );



            let mode =
            document.body.classList.contains(
                "dark-mode"
            )
            ? "dark-mode"
            : "";



            localStorage.setItem(
                "storeTheme",
                mode
            );



        });



    }
    /* ==========================================
       LANGUAGE DIRECTION RTL / LTR
    ========================================== */


    const langBtn =
    document.getElementById("languageToggle");



    const savedDirection =
    localStorage.getItem("storeDirection");



    if(savedDirection){


        document.documentElement.dir =
        savedDirection;



        document.documentElement.lang =
        savedDirection === "rtl"
        ? "ar"
        : "en";


    }




    if(langBtn){



        langBtn.addEventListener("click",()=>{



            let current =
            document.documentElement.dir;



            if(current === "rtl"){



                document.documentElement.dir =
                "ltr";



                document.documentElement.lang =
                "en";



                localStorage.setItem(
                    "storeDirection",
                    "ltr"
                );



            }

            else{



                document.documentElement.dir =
                "rtl";



                document.documentElement.lang =
                "ar";



                localStorage.setItem(
                    "storeDirection",
                    "rtl"
                );



            }



        });



    }
    /* ==========================================
       PRODUCT REVIEWS & STARS
    ========================================== */


    const stars =
    document.querySelectorAll(".rating-star");



    stars.forEach(star=>{


        star.addEventListener("click",function(){



            let rating =
            this.dataset.rating;



            let container =
            this.closest(".rating-box");



            if(container){


                container
                .querySelectorAll(".rating-star")
                .forEach(item=>{


                    if(
                        item.dataset.rating <= rating
                    ){


                        item.classList.add(
                            "active"
                        );


                    }

                    else{


                        item.classList.remove(
                            "active"
                        );


                    }


                });



                container.dataset.value =
                rating;



            }



        });



    });





    /* ==================================
       SEND REVIEW
    ================================== */


    const reviewForm =
    document.getElementById("reviewForm");



    if(reviewForm){



        reviewForm.addEventListener(
            "submit",
            function(e){



                e.preventDefault();



                let rating =
                this.querySelector(
                    ".rating-box"
                ).dataset.value;



                let formData =
                new FormData(this);



                formData.append(
                    "rating",
                    rating
                );



                fetch(
                    this.action,
                    {

                    method:"POST",

                    body:formData,

                    headers:{

                        "X-CSRFToken":
                        csrfToken ?
                        csrfToken.value :
                        ""

                    }

                })



                .then(response=>response.json())



                .then(data=>{


                    if(data.success){


                        showToast(
                            "تم إرسال تقييمك بنجاح"
                        );


                        this.reset();



                    }



                });



            }

        );



    }
    /* ==========================================
       OFFERS COUNTDOWN
    ========================================== */


    const countdowns =
    document.querySelectorAll(".offer-countdown");



    countdowns.forEach(timer=>{


        let endDate =
        new Date(
            timer.dataset.date
        ).getTime();



        let interval =
        setInterval(()=>{



            let now =
            new Date().getTime();



            let distance =
            endDate - now;



            if(distance <= 0){


                clearInterval(interval);


                timer.innerHTML =
                "انتهى العرض";


                return;


            }



            let days =
            Math.floor(
                distance /
                (1000*60*60*24)
            );



            let hours =
            Math.floor(
                (distance %
                (1000*60*60*24))
                /
                (1000*60*60)
            );



            let minutes =
            Math.floor(
                (distance %
                (1000*60*60))
                /
                (1000*60)
            );



            let seconds =
            Math.floor(
                (distance %
                (1000*60))
                /
                1000
            );



            timer.innerHTML = `

                ${days} يوم

                ${hours} ساعة

                ${minutes} دقيقة

                ${seconds ثانية}

            `;



        },1000);



    });







    /* ==========================================
       COPY COUPON CODE
    ========================================== */


    document.querySelectorAll(".copy-coupon")
    .forEach(button=>{


        button.addEventListener("click",()=>{



            let code =
            button.dataset.code;



            navigator.clipboard.writeText(
                code
            );



            showToast(
                "تم نسخ كوبون الخصم"
            );



        });



    });
    /* ==========================================
       ORDER STATUS NOTIFICATIONS
    ========================================== */


    function orderNotification(message){


        let box =
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



        document.body.appendChild(box);



        setTimeout(()=>{


            box.classList.add(
                "show"
            );


        },100);




        setTimeout(()=>{


            box.classList.remove(
                "show"
            );


            setTimeout(()=>{


                box.remove();


            },500);



        },5000);



    }







    /* ==================================
       CHECK ORDER STATUS
    ================================== */


    const orderTracker =
    document.getElementById(
        "orderTracker"
    );



    if(orderTracker){



        let orderId =
        orderTracker.dataset.order;



        setInterval(()=>{



            fetch(
                `/orders/status/${orderId}/`
            )



            .then(response=>
                response.json()
            )



            .then(data=>{



                if(data.changed){



                    orderNotification(
                        data.message
                    );



                    orderTracker.innerHTML =
                    data.status;



                }



            });



        },10000);



    }
    /* ==========================================
       IMAGE LAZY LOADING
    ========================================== */


    const lazyImages =
    document.querySelectorAll(
        "img[data-src]"
    );



    if(lazyImages.length){



        const imageObserver =
        new IntersectionObserver(
            (entries, observer)=>{


                entries.forEach(entry=>{


                    if(entry.isIntersecting){



                        let image =
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
                rootMargin:"100px"
            }
        );




        lazyImages.forEach(image=>{


            imageObserver.observe(
                image
            );


        });



    }







    /* ==========================================
       MOBILE PERFORMANCE
    ========================================== */


    document.querySelectorAll(
        "img"
    )
    .forEach(image=>{


        if(
            !image.hasAttribute(
                "loading"
            )
        ){


            image.setAttribute(
                "loading",
                "lazy"
            );


        }



    });
    /* ==========================================
       STORE GLOBAL HELPERS
    ========================================== */


    window.Store = {



        toast:function(message,type="success"){


            if(typeof showToast === "function"){


                showToast(
                    message,
                    type
                );


            }


        },





        refreshCart:function(){



            fetch(
                "/cart/count/"
            )

            .then(response=>
                response.json()
            )


            .then(data=>{


                const count =
                document.getElementById(
                    "cartCount"
                );



                if(count){


                    count.innerText =
                    data.count;


                }



            })

            .catch(()=>{});


        },





        formatPrice:function(price){



            return Number(price)
            .toLocaleString(
                "ar-SA"
            );



        }



    };





    /* ==========================================
       INITIAL STORE START
    ========================================== */


    if(window.Store){


        window.Store.refreshCart();


    }
