/*==================================================
        ALRAED ERP - PAYMENT METHODS JS
==================================================*/


document.addEventListener(
    "DOMContentLoaded",
    function(){



/*==================================================
            ENABLE / DISABLE PAYMENT
==================================================*/


const switches = document.querySelectorAll(
    ".payment-footer .form-check-input"
);


switches.forEach(function(sw){


    sw.addEventListener(
        "change",
        function(){


            const card =
            this.closest(".payment-card");


            const status =
            card.querySelector(".payment-status");


            if(this.checked){


                status.classList.remove(
                    "disabled"
                );


                status.classList.add(
                    "enabled"
                );


                status.innerHTML =
                `
                <i class="bi bi-check-circle-fill"></i>
                مفعل
                `;


            }
            else{


                status.classList.remove(
                    "enabled"
                );


                status.classList.add(
                    "disabled"
                );


                status.innerHTML =
                `
                <i class="bi bi-x-circle-fill"></i>
                غير مفعل
                `;


            }



        }
    );

});



/*==================================================
                MODAL ANIMATION
==================================================*/


const modals =
document.querySelectorAll(".modal");


modals.forEach(function(modal){


    modal.addEventListener(
        "show.bs.modal",
        function(){


            const dialog =
            this.querySelector(
                ".modal-dialog"
            );


            dialog.style.transform =
            "translateY(-20px)";


            dialog.style.opacity =
            "0";


            setTimeout(function(){


                dialog.style.transition =
                ".3s";


                dialog.style.transform =
                "translateY(0)";


                dialog.style.opacity =
                "1";


            },50);



        }
    );


});



});
/*==================================================
                SAVE BUTTONS
==================================================*/


const saveButtons =
document.querySelectorAll(
    ".modal-footer .btn-primary, .modal-footer .btn-warning"
);



saveButtons.forEach(function(button){


    button.addEventListener(
        "click",
        function(){


            const originalText =
            this.innerHTML;


            this.innerHTML =
            `
            <span class="spinner-border spinner-border-sm"></span>
            جاري الحفظ...
            `;


            this.disabled = true;



            setTimeout(()=>{


                this.innerHTML =
                `
                <i class="bi bi-check-circle-fill"></i>
                تم الحفظ
                `;


                this.classList.add(
                    "btn-success"
                );



                setTimeout(()=>{


                    const modal =
                    this.closest(".modal");


                    const instance =
                    bootstrap.Modal.getInstance(
                        modal
                    );


                    if(instance){

                        instance.hide();

                    }



                    this.innerHTML =
                    originalText;


                    this.disabled=false;


                    this.classList.remove(
                        "btn-success"
                    );



                },1200);



            },800);



        }
    );


});



/*==================================================
                FORM VALIDATION
==================================================*/


const modalInputs =
document.querySelectorAll(
    ".modal input"
);



modalInputs.forEach(function(input){


    input.addEventListener(
        "input",
        function(){


            if(this.value.trim() !== ""){


                this.classList.remove(
                    "is-invalid"
                );


            }


        }
    );


});



function validateModal(modal){


    let valid=true;


    const required =
    modal.querySelectorAll(
        "input"
    );


    required.forEach(function(input){


        if(
            input.value.trim()===""
            &&
            input.hasAttribute("required")
        ){


            input.classList.add(
                "is-invalid"
            );


            valid=false;


        }


    });


    return valid;


}



/*==================================================
                TOAST MESSAGE
==================================================*/


function showPaymentToast(message,type="success"){


    const toast =
    document.createElement(
        "div"
    );


    toast.className =
    `
    payment-toast ${type}
    `;


    toast.innerHTML =
    `
    <i class="bi bi-check-circle-fill"></i>
    ${message}
    `;



    document.body.appendChild(toast);



    setTimeout(()=>{


        toast.classList.add(
            "show"
        );


    },100);



    setTimeout(()=>{


        toast.classList.remove(
            "show"
        );


        setTimeout(()=>{

            toast.remove();

        },300);



    },2500);



}
/*==================================================
                CSRF TOKEN
==================================================*/


function getCookie(name) {

    let cookieValue = null;


    if(document.cookie && document.cookie !== "") {


        const cookies =
        document.cookie.split(";");


        cookies.forEach(cookie => {


            cookie =
            cookie.trim();


            if(cookie.startsWith(name + "=")) {


                cookieValue =
                decodeURIComponent(
                    cookie.substring(
                        name.length + 1
                    )
                );


            }


        });


    }


    return cookieValue;

}



const csrftoken =
getCookie("csrftoken");




/*==================================================
            AJAX SAVE PREPARATION
==================================================*/


document.querySelectorAll(
    ".modal-footer button"
).forEach(function(button){


    button.addEventListener(
        "click",
        function(){


            const modal =
            this.closest(".modal");


            if(!modal){

                return;

            }


            const data = {};


            modal.querySelectorAll(
                "input,select,textarea"
            )
            .forEach(function(field){


                if(field.name){


                    data[field.name] =
                    field.value;


                }


            });



            /*
                لاحقاً سنربطه مع:

                /dashboard/payment-methods/save/

            */


            console.log(
                "Payment Data:",
                data
            );



        }
    );


});



/*==================================================
                TOAST CSS CLASS CONTROL
==================================================*/


const toastStyle = document.createElement(
    "style"
);


toastStyle.innerHTML = `


.payment-toast{


    position:fixed;

    bottom:30px;

    right:30px;

    background:#16a34a;

    color:#fff;

    padding:16px 25px;

    border-radius:16px;

    display:flex;

    align-items:center;

    gap:10px;

    font-weight:700;

    box-shadow:
    0 15px 35px rgba(0,0,0,.15);

    transform:
    translateY(80px);

    opacity:0;

    transition:.3s;

    z-index:9999;

}



.payment-toast.show{


    transform:
    translateY(0);


    opacity:1;


}



.payment-toast.error{


    background:#dc2626;


}


`;


document.head.appendChild(
    toastStyle
);
