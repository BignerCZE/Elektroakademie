document.addEventListener("DOMContentLoaded", function () {
    localStorage.removeItem("elektroakademie_order_draft");

    let seconds = 30;
    const paymentPage = document.querySelector("main[data-index-url]");
    const countdownElement = document.getElementById(
        "redirect-countdown"
    );

    const timer = window.setInterval(function () {
        seconds -= 1;

        if (countdownElement) {
            countdownElement.textContent = String(seconds);
        }

        if (seconds <= 0) {
            window.clearInterval(timer);
            window.location.href = paymentPage.dataset.indexUrl;
        }
    }, 1000);

    document.querySelectorAll("[data-copy-link]").forEach(
        function (button) {
            button.addEventListener("click", async function () {
                const input = document.getElementById(
                    button.dataset.copyLink
                );

                if (!input) {
                    return;
                }

                const originalText = button.textContent.trim();

                try {
                    await navigator.clipboard.writeText(
                        input.value
                    );

                    button.textContent = "Zkopírováno";
                } catch (error) {
                    input.select();
                    input.setSelectionRange(
                        0,
                        input.value.length
                    );

                    const copied = document.execCommand("copy");

                    button.textContent = copied
                        ? "Zkopírováno"
                        : "Kopírování selhalo";
                }

                window.setTimeout(function () {
                    button.textContent = originalText;
                }, 2000);
            });
        }
    );
});
