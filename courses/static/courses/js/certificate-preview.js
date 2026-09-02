document.addEventListener("DOMContentLoaded", function () {
    const modalOverlay = document.getElementById(
        "certificate-preview-modal"
    );

    const openButton = document.getElementById(
        "open-certificate-preview"
    );

    const closeButton = document.getElementById(
        "close-certificate-preview"
    );

    function openModal() {
        modalOverlay.classList.add("is-open");
        modalOverlay.setAttribute("aria-hidden", "false");

        document.body.classList.add("certificate-modal-open");

        closeButton.focus();
    }

    function closeModal() {
        modalOverlay.classList.remove("is-open");
        modalOverlay.setAttribute("aria-hidden", "true");

        document.body.classList.remove("certificate-modal-open");

        openButton.focus();
    }

    openButton.addEventListener("click", openModal);

    closeButton.addEventListener("click", closeModal);

    modalOverlay.addEventListener("click", function (event) {
        if (event.target === modalOverlay) {
            closeModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (
            event.key === "Escape"
            && modalOverlay.classList.contains("is-open")
        ) {
            closeModal();
        }
    });
});
