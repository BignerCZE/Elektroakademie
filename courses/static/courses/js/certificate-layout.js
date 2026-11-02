// The PDF and browser preview use the same compact layout for longer profiles.
window.fitCertificates = async function () {
    await document.fonts.ready;
    await Promise.all(Array.from(document.images, image => image.decode().catch(() => {})));
    document.querySelectorAll(".certificate-document").forEach(document => {
        document.classList.remove("certificate-document--compact");
        const footer = document.querySelector(".certificate-footer");
        const availableHeight = 297 * 96 / 25.4;
        const padding = parseFloat(getComputedStyle(document).paddingBottom);
        if (footer.getBoundingClientRect().bottom + padding > document.getBoundingClientRect().top + availableHeight) {
            document.classList.add("certificate-document--compact");
        }
    });
};
window.fitCertificates();
