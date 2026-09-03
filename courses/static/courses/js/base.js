document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("mobile-menu-toggle");
    const navigation = document.getElementById("top-navigation");

    if (toggle && navigation) {
        toggle.addEventListener("click", function () {
            const isOpen = navigation.classList.toggle("is-open");
            toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });

        navigation.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", function () {
                navigation.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
            });
        });
    }

    const draftOrder = window.ElektroakademieOrderDraft.exists();
    const startOrderLink = document.getElementById("start-order-link");
    const draftOrderLink = document.getElementById("draft-order-link");

    if (startOrderLink && draftOrderLink) {
        if (draftOrder) {
            startOrderLink.hidden = true;
            draftOrderLink.hidden = false;
        } else {
            startOrderLink.hidden = false;
            draftOrderLink.hidden = true;
        }
    }
});
