// The PDF and browser preview use the same compact layout for longer profiles.
window.fitCertificates = async function () {
    await document.fonts.ready;
    await Promise.all(Array.from(document.images, image => image.decode().catch(() => {})));
    document.querySelectorAll(".certificate-document").forEach(document => {
        document.classList.remove("certificate-document--compact");
        if (document.closest(".certificate-pdf")) {
            // Reserve room for Chromium's print rounding at the bottom of A4.
            const printHeight = 295 * 96 / 25.4;
            document.style.removeProperty("zoom");
            document.style.removeProperty("min-height");
            if (document.getBoundingClientRect().height > printHeight) {
                document.classList.add("certificate-document--compact");
                const compactHeight = document.getBoundingClientRect().height;
                if (compactHeight > printHeight) {
                    document.style.zoom = printHeight / compactHeight;
                    return;
                }
            }
            document.style.minHeight = printHeight + "px";
            return;
        }

        const footer = document.querySelector(".certificate-footer");
        const availableHeight = 297 * 96 / 25.4;
        const padding = parseFloat(getComputedStyle(document).paddingBottom);
        if (footer.getBoundingClientRect().bottom + padding > document.getBoundingClientRect().top + availableHeight) {
            document.classList.add("certificate-document--compact");
        }
    });
};
window.fitCertificates();
