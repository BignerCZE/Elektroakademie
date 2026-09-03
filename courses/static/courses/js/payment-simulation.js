document.addEventListener("DOMContentLoaded", function () {
    window.ElektroakademieOrderDraft.clear();

    const paymentPage = document.querySelector("main[data-success-url]");

    let seconds = 5;
    const countdown = document.getElementById("payment-countdown");

    const timer = setInterval(function () {
        seconds -= 1;
        countdown.textContent = seconds;

        if (seconds <= 0) {
            clearInterval(timer);
            window.location.href = paymentPage.dataset.successUrl;
        }
    }, 1000);
});
